# api/services/knowledge_graph_service.py
import json
import logging
import os
import re
from infrastructure.openai_service import OpenAIMessageService
from infrastructure.neo4j_service import Neo4jService

class KnowledgeGraphService:
    def __init__(self, neo4j_service: Neo4jService, openai_service: OpenAIMessageService):
        self.neo4j = neo4j_service
        self.openai = openai_service
        self.reference_map = self._load_references()

    def _load_references(self):
        """Carga el mapa de referencias {pmc_id: url} desde el archivo JSON original."""
        try:
            # Asumimos que el archivo scrapeado está en la carpeta 'resources'
            with open(os.path.join('resources', 'space_biology_scraped.json'), 'r', encoding='utf-8') as f:
                documents = json.load(f)
            return {doc['pmc_id']: doc.get('source_url', '') for doc in documents}
        except Exception as e:
            logging.error(f"Error al cargar el mapa de referencias: {e}")
            return {}

    def search_context(self, query_text: str) -> list:
        """Busca en el grafo para encontrar contexto relevante para la pregunta."""
        # Extract meaningful keywords (words of length >=4), lowercased and unique
        keywords = list(dict.fromkeys([w.lower() for w in re.findall(r"\w{4,}", query_text)]))

        cypher_query = """
        UNWIND $keywords AS keyword
        MATCH (n:Entity)
        WHERE toLower(n.name) CONTAINS keyword
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN n.name AS entity1, type(r) AS relation, m.name AS entity2, collect(DISTINCT r.source_doc) AS pmc_ids
        LIMIT 50
        """
        try:
            results = self.neo4j.execute_query(cypher_query, parameters={'keywords': keywords})

            context = []
            for record in results:
                entity1 = record.get('entity1')
                relation = record.get('relation') or 'RELATED_TO'
                entity2 = record.get('entity2')
                pmc_ids = record.get('pmc_ids') or []
                # normalize pmc_ids to a list of non-empty strings
                if isinstance(pmc_ids, str):
                    pmc_ids = [pmc_ids]
                pmc_ids = [p for p in pmc_ids if p]

                # make relation readable: RESULTED_IN -> resulted in
                readable_rel = relation.replace('_', ' ').lower()

                summary = f"{entity1} {readable_rel} {entity2}" if entity2 else f"{entity1} ({readable_rel})"
                context.append({
                    "content": summary,
                    "pmc_ids": pmc_ids
                })
            return context
        except Exception as e:
            logging.error(f"Error al buscar en Neo4j: {e}")
            return []

    def generate_answer_with_citations(self, query: str) -> str:
        """Orquesta el proceso completo de RAG."""
        context = self.search_context(query)

        if not context:
            return "No encontré información relevante en la base de conocimiento para responder a tu pregunta."

        # Build a readable context block and collect unique pmc ids
        context_lines = []
        unique_pmc_ids = set()
        for item in context:
            pmcs = item.get('pmc_ids') or []
            pmc_tags = ",".join(pmcs) if pmcs else "Unknown"
            context_lines.append(f"[IDs: {pmc_tags}] {item['content']}")
            for p in pmcs:
                unique_pmc_ids.add(p)

        context_str = "\n".join(context_lines)

        hyperlinks_str = ""
        for pmc_id in sorted(unique_pmc_ids):
            url = self.reference_map.get(pmc_id, "URL no encontrada")
            hyperlinks_str += f"{pmc_id}: {url}\n"

        system_prompt = """
        Eres un asistente experto en biociencia espacial de la NASA. Responde la pregunta del usuario usando SOLO el contexto proporcionado.
        Reglas:
        - No inventes información.
        - Cada afirmación concreta debe llevar al final una referencia entre corchetes con el PMC id, por ejemplo: "La microgravedad induce pérdida ósea [PMC3630201]".
        - Si una afirmación está respaldada por múltiples artículos, incluye todos los PMC ids en la cita: [PMC1, PMC2].
        - Al final de la respuesta incluye una sección "## Referencias" con cada PMC utilizado y su URL correspondiente.
        """

        user_prompt = f"""
        Contexto extraído del grafo (usa solamente esto para responder):
        ---
        {context_str}
        ---

        Referencias (PMC -> URL):
        ---
        {hyperlinks_str}
        ---

        Pregunta del usuario:
        {query}

        Responde de forma concisa, con citas en formato [PMC...] al final de cada afirmación.
        """
        
        return self.openai.generate_message(system_prompt, user_prompt)

    def get_top_categories(self, limit: int = 10) -> list:
        """
        Obtiene las N entidades más frecuentes (con más relaciones) del grafo.
        """
        cypher_query = """
        MATCH (n:Entity)
        WITH n, COUNT { (n)--() } as degree
        ORDER BY degree DESC
        LIMIT $limit
        RETURN n.name AS category, degree AS count
        """
        try:
            results = self.neo4j.execute_query(cypher_query, parameters={'limit': limit})
            return results
        except Exception as e:
            logging.error(f"Error al obtener las entidades de Neo4j: {e}")
            return []
