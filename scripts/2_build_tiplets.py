# scripts/2_build_triplets.py
import json
import time
import re
import logging
import sys
import os
from tqdm import tqdm
from collections import Counter

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from infrastructure.openai_service import OpenAIMessageService

INPUT_JSON_FILE = 'resources/space_biology_scraped.json'
OUTPUT_TRIPLETS_FILE = 'resources/raw_triplets.json'
TOP_RELATIONS_FILE = 'resources/top_relations.txt'

# Allowed relation canonical forms and common variants to map
RELATION_MAP = {
    'wrote': 'WROTE',
    'written by': 'WROTE',
    'author_of': 'WROTE',
    'covers': 'COVERS',
    'cover': 'COVERS',
    'describes': 'DESCRIBES',
    'described': 'DESCRIBES',
    'resulted_in': 'RESULTED_IN',
    'resulted in': 'RESULTED_IN',
    'resulted-in': 'RESULTED_IN',
    'resulted': 'RESULTED_IN',
    'resulted in:': 'RESULTED_IN',
    'cites': 'CITES',
    'cited': 'CITES',
    'references': 'CITES',
    # Additional scientific relations
    'published in': 'PUBLISHED_IN',
    'published': 'PUBLISHED_IN',
    'journal': 'PUBLISHED_IN',
    'investigates': 'INVESTIGATES',
    'investigated': 'INVESTIGATES',
    'investigation of': 'INVESTIGATES',
    'reports': 'REPORTS',
    'reported': 'REPORTS',
    'measures': 'MEASURES',
    'measured': 'MEASURES',
    'observes': 'OBSERVED_IN',
    'observed in': 'OBSERVED_IN',
    'observed': 'OBSERVED_IN',
    'uses': 'USES',
    'used': 'USES',
    'employs': 'USES',
    'employed': 'USES',
    'associated with': 'ASSOCIATED_WITH',
    'associated': 'ASSOCIATED_WITH',
    'correlated with': 'CORRELATED_WITH',
    'correlates with': 'CORRELATED_WITH',
    'correlated': 'CORRELATED_WITH',
    'supports': 'SUPPORTS',
    'supported': 'SUPPORTS',
    'confirms': 'SUPPORTS',
    'contradicts': 'CONTRADICTS',
    'challenges': 'CONTRADICTS',
    'refutes': 'CONTRADICTS',
    'inhibits': 'INHIBITS',
    'inhibit': 'INHIBITS',
    'activates': 'ACTIVATES',
    'activate': 'ACTIVATES',
    # More scientific relation variants observed in papers
    'induce': 'INDUCES',
    'induces': 'INDUCES',
    'induced': 'INDUCES',
    'cause': 'CAUSES',
    'causes': 'CAUSES',
    'caused': 'CAUSES',
    'lead to': 'LEADS_TO',
    'leads to': 'LEADS_TO',
    'leads': 'LEADS_TO',
    'increase': 'INCREASES',
    'increased': 'INCREASES',
    'increases': 'INCREASES',
    'decrease': 'DECREASES',
    'decreased': 'DECREASES',
    'decreases': 'DECREASES',
    'up-regulated': 'UPREGULATED',
    'upregulated': 'UPREGULATED',
    'up regulated': 'UPREGULATED',
    'down-regulated': 'DOWNREGULATED',
    'downregulated': 'DOWNREGULATED',
    'down regulated': 'DOWNREGULATED',
    'promote': 'PROMOTES',
    'promotes': 'PROMOTES',
    'promoted': 'PROMOTES',
    'found': 'REPORTS',
    'observed that': 'OBSERVED_IN',
    'we observed': 'OBSERVED_IN',
    'we found': 'REPORTS',
    'show': 'DEMONSTRATES',
    'shows': 'DEMONSTRATES',
    'shown': 'DEMONSTRATES',
    'demonstrates': 'DEMONSTRATES',
    'demonstrated': 'DEMONSTRATES',
    'suggest': 'SUGGESTS',
    'suggests': 'SUGGESTS',
    'suggested': 'SUGGESTS',
    'hypothesize': 'HYPOTHESIZES',
    'hypothesizes': 'HYPOTHESIZES',
    'hypothesized': 'HYPOTHESIZES',
    'regulate': 'REGULATES',
    'regulates': 'REGULATES',
    'regulation': 'REGULATES',
    'modulate': 'MODULATES',
    'modulates': 'MODULATES',
    'modulated': 'MODULATES',
    'attenuate': 'ATTENUATES',
    'attenuates': 'ATTENUATES',
    'attenuated': 'ATTENUATES',
    'enhance': 'ENHANCES',
    'enhances': 'ENHANCES',
    'enhanced': 'ENHANCES',
    'involve': 'INVOLVES',
    'involves': 'INVOLVES',
    'involved in': 'INVOLVES',
    'affect': 'AFFECTS',
    'affects': 'AFFECTS',
    'affected': 'AFFECTS',
    'linked to': 'ASSOCIATED_WITH',
    'links to': 'ASSOCIATED_WITH',
}

ALLOWED_RELATIONS = set(RELATION_MAP.values())

def normalize_relation(raw: str) -> str | None:
    if not raw:
        return None
    key = raw.strip().lower()
    # direct mapping
    if key in RELATION_MAP:
        return RELATION_MAP[key]
    # uppercase tokens like RESULTED_IN are allowed
    up = raw.strip().upper().replace(' ', '_')
    if up in ALLOWED_RELATIONS:
        return up
    return None

def normalize_triplets(triplets, article_title: str = None, article_pmc: str = None):
    """Validate and normalize a list of triplet dicts.

    - Maps relation to canonical tokens (WROTE, COVERS, DESCRIBES, RESULTED_IN, CITES).
    - Replaces literal 'Article' values with the article title or pmc_id when available.
    - Removes duplicates and invalid entries.
    """
    if not isinstance(triplets, list):
        return []
    seen = set()
    out = []
    for t in triplets:
        if not isinstance(t, dict):
            continue
        src = t.get('source') or t.get('subject')
        rel = t.get('relation') or t.get('predicate')
        tgt = t.get('target') or t.get('object')
        if not src or not rel or not tgt:
            continue
        src = str(src).strip()
        rel = str(rel).strip()
        tgt = str(tgt).strip()

        # replace literal node type labels with real metadata
        if src.lower() == 'article' and article_title:
            src = article_title.strip()
        elif src.lower() == 'article' and article_pmc:
            src = article_pmc.strip()

        if tgt.lower() == 'article' and article_title:
            tgt = article_title.strip()
        elif tgt.lower() == 'article' and article_pmc:
            tgt = article_pmc.strip()

        canonical_rel = normalize_relation(rel)
        if not canonical_rel:
            # try to be permissive by removing punctuation
            canonical_rel = normalize_relation(re.sub(r"[^\w ]", ' ', rel))
        if not canonical_rel:
            # skip unknown relation
            logging.debug(f"Omitting tripleta por relación desconocida: {rel}")
            continue

        # truncate very long nodes
        if len(src) > 300:
            src = src[:297] + '...'
        if len(tgt) > 300:
            tgt = tgt[:297] + '...'

        key = (src, canonical_rel, tgt)
        if key in seen:
            continue
        seen.add(key)
        cleaned = {'source': src, 'relation': canonical_rel, 'target': tgt}
        out.append(cleaned)
    return out

def get_open_triplets_from_text(openai_service: OpenAIMessageService, text_chunk: str, article_title: str = None, article_pmc: str = None):
    if not openai_service or not text_chunk.strip():
        return []

    system_prompt = (
        "Eres un extractor de conocimiento especializado en artículos científicos de biociencias y astrobiología. "
        "Tu tarea es, de forma conservadora y sin inventar información, extraer relaciones verificables del texto y expresarlas como tripletas. "
        "Devuelve SOLO JSON válido: una lista (posiblemente vacía) de objetos con claves 'source', 'relation' y 'target'. "
        "Sólo usa las relaciones explícitamente permitidas en las instrucciones del usuario. "
        "Si la relación no está clara o es altamente especulativa, devuelve la lista vacía []."
    )

    # Provide article metadata to the model so it can use the real title instead of the literal word "Article"
    article_info = ''
    if article_title:
        article_info += f"Article title: {article_title}\n"
    if article_pmc:
        article_info += f"Article pmc_id: {article_pmc}\n"

    user_prompt = f"""
    Instrucciones precisas (lee antes de procesar el texto):
    1) Objetivo: extraer tripletas que encajen en este esquema de nodos y relaciones permitidas (no inventes hechos):
         Nodos permitidos (valores para 'source' o 'target' deben ser textos concisos que representen la entidad):
             - Article: título o identificador (ej: "Mice in Bion-M 1 Space Mission")
             - Author: nombre completo (ej: "Vladimir Sychev")
             - Topic: tema/concepto (ej: "microgravity", "stem cells")
             - Experiment: descripción breve de procedimiento o sujeto experimental (ej: "mice in microgravity for 30 days")
             - Finding: resumen corto de un resultado o conclusión (ej: "microgravity induces bone loss")

         Relaciones permitidas (usar exactamente estos tokens en mayúsculas):
             - WROTE  (Author -> Article)
             - COVERS (Article -> Topic)
             - DESCRIBES (Article -> Experiment)
             - RESULTED_IN (Experiment -> Finding)
             - CITES (Article -> Article)

    2) Reglas de extracción:
         - Extrae SOLO relaciones que estén explícitas en el texto o que sean inferibles de forma directa y conservadora.
         - No crees nodos/relaciones basados en conjeturas. Si falta evidencia textual, omite.
         - Para cada tripleta devuelve: {{"source": "...", "relation": "<REL>", "target": "..."}}.
         - Usa frases cortas y normalizadas para 'source' y 'target' (no párrafos).
         - Si el texto refiere a un artículo distinto (citación), intenta extraer el título o el identificador si está presente; si no, omítelo.
         - Si no hay ninguna tripleta válida en el fragmento, devuelve exactamente [] (una lista vacía).

    3) Formato de salida (ejemplos válidos):
         [
             {{"source": "Vladimir Sychev", "relation": "WROTE", "target": "Mice in Bion-M 1 Space Mission"}},
             {{"source": "Mice in Bion-M 1 Space Mission", "relation": "COVERS", "target": "microgravity"}},
             {{"source": "Mice in Bion-M 1 Space Mission", "relation": "DESCRIBES", "target": "mice in microgravity for 30 days"}},
             {{"source": "mice in microgravity for 30 days", "relation": "RESULTED_IN", "target": "bone loss"}}
         ]

    4) Idioma: responde en el mismo idioma que el texto; en este caso el texto puede estar en inglés o español. Mantén los textos de 'source' y 'target' tal como aparecen (o una versión corta y fiel).

        5) Texto a analizar:
    ---
    {text_chunk}
    ---
    
        Información del artículo (si está disponible):
        {article_info}

        Reglas adicionales IMPORTANTES:
            - NUNCA uses exactamente la cadena literal "Article", "Author", "Topic", "Experiment" o "Finding" como valor para 'source' o 'target'.
                En su lugar, cuando te refieras al artículo actual usa el título proporcionado en 'Article title' arriba.
            - Normaliza títulos quitando saltos de línea excesivos y preservando el texto esencial.

        Devuelve SOLO el JSON descrito, sin explicaciones adicionales.
        """

    try:
        response_text = openai_service.generate_message(system_prompt, user_prompt)
        # extract the first JSON array-like substring
        match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if not match:
            logging.warning("No se encontró JSON (lista) en la respuesta del LLM.")
            return []
        json_str = match.group(0)
        try:
            parsed = json.loads(json_str)
        except Exception:
            # fallback: try to clean common LLM formatting (trailling commas etc.)
            cleaned = re.sub(r',\s*\]', ']', json_str)
            try:
                parsed = json.loads(cleaned)
            except Exception as e:
                logging.error(f"No se pudo parsear el JSON extraído: {e}")
                return []

        # normalize and validate triplets
        normalized = normalize_triplets(parsed, article_title=article_title, article_pmc=article_pmc)
        return normalized
    except Exception as e:
        logging.error(f"Error al procesar la respuesta del servicio: {e}")
        return []

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    try:
        openai_service = OpenAIMessageService()
        logging.info("Servicio de Azure OpenAI inicializado.")
    except Exception as e:
        logging.error(f"No se pudo inicializar OpenAIMessageService: {e}")
        return
        
    try:
        with open(INPUT_JSON_FILE, 'r', encoding='utf-8') as f:
            documents = json.load(f)
    except Exception as e:
        logging.error(f"Error al cargar '{INPUT_JSON_FILE}': {e}")
        return

    all_triplets = []
    logging.info(f"Iniciando extracción de tripletas de {len(documents)} documentos...")
    for doc in tqdm(documents, desc="Procesando Documentos"):
        text_to_process = {
            'abstract': doc.get('abstract', ''),
            'results': doc.get('sections', {}).get('results and discussion', ''),
            'conclusions': doc.get('sections', {}).get('conclusions', '')
        }
        for text in text_to_process.values():
            if text:
                triplets = get_open_triplets_from_text(
                    openai_service,
                    text,
                    article_title=doc.get('title'),
                    article_pmc=doc.get('pmc_id')
                )
                for t in triplets:
                    t['source_doc'] = doc.get('pmc_id', 'Unknown')
                all_triplets.extend(triplets)
                time.sleep(1) 

        # Añadir relaciones 'WROTE' a partir de metadatos para asegurar Authors->Article
        title = doc.get('title') or doc.get('pmc_id') or 'Unknown Article'
        pmc = doc.get('pmc_id')
        authors = doc.get('authors') or []
        for a in authors:
            a_name = a.strip() if isinstance(a, str) else None
            if not a_name:
                continue
            wrote_triplet = {'source': a_name, 'relation': 'WROTE', 'target': title, 'source_doc': pmc}
            # avoid duplicates
            if wrote_triplet not in all_triplets:
                all_triplets.append(wrote_triplet)

    logging.info(f"Extracción Completa. Total de tripletas: {len(all_triplets)}")
    with open(OUTPUT_TRIPLETS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_triplets, f, indent=2, ensure_ascii=False)
    logging.info(f"Resultados guardados en '{OUTPUT_TRIPLETS_FILE}'")
    
    relation_counts = Counter(str(t.get('relation', '')).strip().lower() for t in all_triplets if t.get('relation'))
    with open(TOP_RELATIONS_FILE, 'w', encoding='utf-8') as f:
        f.write("Relaciones más frecuentes y su conteo:\n" + "="*50 + "\n")
        for relation, count in relation_counts.most_common(200):
            f.write(f"{relation}: {count}\n")
    logging.info(f"Análisis de frecuencia guardado en '{TOP_RELATIONS_FILE}'.")

if __name__ == "__main__":
    main()