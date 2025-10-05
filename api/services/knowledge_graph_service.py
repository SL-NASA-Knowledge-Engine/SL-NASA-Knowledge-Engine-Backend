# api/services/knowledge_graph_service.py
import json
import logging
import os
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
        query_words = [word.strip().title() for word in query_text.split() if len(word) > 4]

        cypher_query = """
        UNWIND $keywords AS keyword
        MATCH (n:Entity)
        WHERE n.name CONTAINS keyword
        MATCH (n)-[r]-(m)
        RETURN n.name AS entity1, type(r) AS relation, m.name AS entity2, r.source_doc AS pmc_id
        LIMIT 15
        """
        try:
            results = self.neo4j.execute_query(cypher_query, parameters={'keywords': query_words})
            
            context = []
            for record in results:
                context.append({
                    "content": f"El concepto '{record['entity1']}' tiene una relación de tipo '{record['relation']}' con '{record['entity2']}'.",
                    "pmc_id": record['pmc_id']
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

        context_str = ""
        hyperlinks_str = ""
        unique_pmc_ids = sorted(list({item['pmc_id'] for item in context}))

        for item in context:
            context_str += f"[ID: {item['pmc_id']}] {item['content']}\n"
        
        for pmc_id in unique_pmc_ids:
            url = self.reference_map.get(pmc_id, "URL no encontrada")
            hyperlinks_str += f"{pmc_id}: {url}\n"

        system_prompt = """
        Eres un asistente experto en biociencia espacial de la NASA. Tu tarea es responder la pregunta del usuario basándote únicamente en el contexto proporcionado.
        **Instrucciones Cruciales:**
        1. Sintetiza la información del contexto para dar una respuesta clara y concisa.
        2. Al final de CADA afirmación, DEBES añadir una cita en formato `[ID]`. Usa el `pmc_id` del contexto.
        3. NO inventes información. Si el contexto no es suficiente para responder, indícalo.
        4. Al final de toda tu respuesta, crea una sección llamada '## Referencias'. En esta sección, lista cada `pmc_id` que citaste con su hipervínculo correspondiente.
        """
        
        user_prompt = f"""
        **Contexto Proporcionado:**
        ---
        {context_str}
        ---

        **Hipervínculos para las Referencias:**
        ---
        {hyperlinks_str}
        ---

        **Pregunta del usuario:**
        {query}

        **Respuesta:**
        """
        
        return self.openai.generate_message(system_prompt, user_prompt)