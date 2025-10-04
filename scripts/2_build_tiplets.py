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

def get_open_triplets_from_text(openai_service: OpenAIMessageService, text_chunk: str):
    if not openai_service or not text_chunk.strip():
        return []

    system_prompt = "Eres un experto en biociencia y tu tarea es extraer conocimiento estructurado de textos científicos. Tu objetivo es identificar las afirmaciones factuales más importantes en forma de tripletas (entidad1, relación, entidad2)."
    user_prompt = f"""
    **Instrucciones:**
    1. Analiza el siguiente texto científico.
    2. 'entidad1' y 'entidad2' deben ser conceptos científicos clave (genes, proteínas, organismos, condiciones, resultados, etc.).
    3. La 'relación' debe ser la frase verbal corta y precisa que conecta las dos entidades en el texto.
    4. Devuelve el resultado como una lista de diccionarios JSON con las claves "source", "relation" y "target".
    5. Sé conciso y extrae solo las relaciones más significativas. Si no encuentras ninguna relación clara, devuelve una lista vacía [].

    **Texto a analizar:**
    ---
    {text_chunk}
    ---
    **Resultado en formato JSON:**
    """
    
    try:
        response_text = openai_service.generate_message(system_prompt, user_prompt)
        match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        logging.warning("No se encontró JSON válido en la respuesta.")
        return []
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
                triplets = get_open_triplets_from_text(openai_service, text)
                for t in triplets:
                    t['source_doc'] = doc.get('pmc_id', 'Unknown')
                all_triplets.extend(triplets)
                time.sleep(1) 

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