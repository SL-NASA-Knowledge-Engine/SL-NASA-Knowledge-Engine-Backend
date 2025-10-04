# build_graph.py
import json
import networkx as nx
import time
import re
import logging
from tqdm import tqdm
from collections import Counter

from infrastructure.openai_service import OpenAIMessageService

# Importamos tu clase de servicio


# --- CONFIGURACIÓN ---
INPUT_JSON_FILE = 'resources/space_biology_scraped.json'
OUTPUT_TRIPLETS_FILE = 'raw_triplets_azure.json'
OUTPUT_GRAPH_FILE = 'nasa_bioscience_graph_azure.gml'
TOP_RELATIONS_FILE = 'top_relations_azure.txt'

# --- 2. FUNCIÓN PARA LLAMAR AL SERVICIO DE OPENAI ---

def get_open_triplets_from_text(openai_service: OpenAIMessageService, text_chunk: str):
    """
    Usa el OpenAIMessageService para extraer tripletas de conocimiento (OIE).
    """
    if not openai_service or not text_chunk.strip():
        return []

    # Dividimos nuestro prompt en "system" y "user" como lo espera tu clase
    system_prompt = """
    Eres un experto en biociencia y tu tarea es extraer conocimiento estructurado de textos científicos.
    Tu objetivo es identificar las afirmaciones factuales más importantes en forma de tripletas (entidad1, relación, entidad2).
    """
    
    user_prompt = f"""
    **Instrucciones:**
    1. Analiza el siguiente texto científico.
    2. 'entidad1' y 'entidad2' deben ser conceptos científicos clave (genes, proteínas, organismos, condiciones, resultados, etc.).
    3. La 'relación' debe ser la frase verbal corta y precisa que conecta las dos entidades en el texto.
    4. Devuelve el resultado como una lista de diccionarios JSON, donde cada diccionario tiene las claves "source", "relation" y "target".
    5. Sé conciso y extrae solo las relaciones más significativas.
    6. Si no encuentras ninguna relación clara, devuelve una lista vacía [].

    **Texto a analizar:**
    ---
    {text_chunk}
    ---

    **Resultado en formato JSON:**
    """
    
    try:
        response_text = openai_service.generate_message(system_prompt, user_prompt)
        
        # Regex para encontrar el bloque JSON, que es más robusto
        match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if match:
            json_str = match.group(0)
            triplets = json.loads(json_str)
            return triplets
        print("Advertencia: No se encontró un formato JSON válido en la respuesta.")
        return []
    except json.JSONDecodeError:
        print(f"Advertencia: No se pudo decodificar la respuesta JSON del modelo.")
        return []
    except Exception as e:
        print(f"Ocurrió un error al procesar la respuesta del servicio: {e}")
        return []

# --- 3. PROCESAMIENTO Y CONSTRUCCIÓN DEL GRAFO ---

def build_knowledge_graph(documents, openai_service):
    """
    Construye un grafo de conocimiento a partir de una lista de documentos.
    """
    G = nx.DiGraph()
    all_triplets = []

    print("Iniciando la extracción de conocimiento con el servicio de Azure OpenAI...")
    
    for doc in tqdm(documents, desc="Procesando Documentos"):
        pmc_id = doc.get('pmc_id', 'Unknown')
        
        text_to_process = {
            'abstract': doc.get('abstract', ''),
            'results': doc.get('sections', {}).get('results and discussion', ''),
            'conclusions': doc.get('sections', {}).get('conclusions', '')
        }
        
        for section, text in text_to_process.items():
            if text:
                triplets = get_open_triplets_from_text(openai_service, text)
                
                for triplet in triplets:
                    source = str(triplet.get('source', '')).strip().title()
                    target = str(triplet.get('target', '')).strip().title()
                    relation = str(triplet.get('relation', '')).strip().lower()

                    if source and target and relation:
                        G.add_edge(source, target, label=relation, source_doc=pmc_id)
                        all_triplets.append(triplet)
                
                time.sleep(1) # Pausa para respetar los límites de la API si es necesario

    return G, all_triplets

# --- FUNCIÓN PRINCIPAL ---

def main():
    """
    Función principal que orquesta todo el proceso.
    """
    # Configura el logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Instanciamos tu servicio de OpenAI
    try:
        openai_service = OpenAIMessageService()
        logging.info("Servicio de Azure OpenAI inicializado correctamente.")
    except Exception as e:
        logging.error(f"No se pudo inicializar OpenAIMessageService. Revisa tus settings: {e}")
        return
        
    # Cargamos los documentos
    try:
        with open(INPUT_JSON_FILE, 'r', encoding='utf-8') as f:
            documents = json.load(f)
    except Exception as e:
        logging.error(f"Error al cargar el archivo de documentos '{INPUT_JSON_FILE}': {e}")
        return

    # Construimos el grafo (ejecutamos en una muestra pequeña para probar)
    # Para el hackaton completo, elimina el [:5]
    sample_documents = documents[:5] 
    knowledge_graph, all_triplets = build_knowledge_graph(sample_documents, openai_service)
    
    # ... (El resto del código para analizar y guardar el grafo es igual al anterior) ...
    print("\n--- ¡Construcción del Grafo Finalizada! ---")
    print(f"Total de tripletas extraídas: {len(all_triplets)}")
    print(f"Nodos (Entidades): {knowledge_graph.number_of_nodes()}")
    print(f"Aristas (Relaciones): {knowledge_graph.number_of_edges()}")

    with open(OUTPUT_TRIPLETS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_triplets, f, indent=2, ensure_ascii=False)
    print(f"Tripletas crudas guardadas en '{OUTPUT_TRIPLETS_FILE}'")
    
    nx.write_gml(knowledge_graph, OUTPUT_GRAPH_FILE)
    print(f"Grafo crudo guardado en '{OUTPUT_GRAPH_FILE}'")

    relation_counts = Counter(edge_data['label'] for _, _, edge_data in knowledge_graph.edges(data=True))
    with open(TOP_RELATIONS_FILE, 'w', encoding='utf-8') as f:
        f.write("Top 100 relaciones más frecuentes y su conteo:\n" + "="*50 + "\n")
        for relation, count in relation_counts.most_common(100):
            f.write(f"{relation}: {count}\n")
    print(f"Análisis de frecuencia de relaciones guardado en '{TOP_RELATIONS_FILE}'.")

if __name__ == "__main__":
    main()