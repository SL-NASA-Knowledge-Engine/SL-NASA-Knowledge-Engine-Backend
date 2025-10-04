# scripts/4_populate_neo4j.py
import json
import logging
import sys
import os
from tqdm import tqdm

# Añadir la raíz del proyecto al path para que los imports funcionen
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from infrastructure.neo4j_service import Neo4jService

# --- CONFIGURACIÓN ---
RESOURCES_DIR = "resources"
INPUT_TRIPLETS_FILE = os.path.join(RESOURCES_DIR, 'raw_triplets.json')
RELATION_MAP_FILE = os.path.join(RESOURCES_DIR, 'relation_map.json')

class Neo4jUploader:
    def __init__(self, neo4j_service: Neo4jService):
        self.neo4j = neo4j_service

    def upload_triplet(self, triplet: dict, relation_mapping: dict):
        """Sube una única tripleta al grafo, refinando la relación."""
        source = str(triplet.get('source', '')).strip().title()
        target = str(triplet.get('target', '')).strip().title()
        raw_relation = str(triplet.get('relation', '')).strip().lower()
        source_doc = triplet.get('source_doc', 'Unknown')

        if not source or not target or not raw_relation:
            return

        # Busca la relación canónica, si no existe, usa 'RELATED_TO' como default
        canonical_relation = relation_mapping.get(raw_relation, 'RELATED_TO')
        
        # Consulta Cypher que usa MERGE para evitar duplicados de nodos y relaciones
        # Se crea una relación por cada documento fuente para preservar la trazabilidad
        query = (
            "MERGE (s:Entity {name: $source_name}) "
            "MERGE (t:Entity {name: $target_name}) "
            "MERGE (s)-[r:`" + canonical_relation + "` {source_doc: $doc}]->(t)"
        )
        
        self.neo4j.execute_query(query, parameters={
            "source_name": source, 
            "target_name": target, 
            "doc": source_doc
        })

def load_relation_mapping(mapping_file: str) -> dict:
    """Carga el mapeo de relaciones y lo invierte para una búsqueda rápida."""
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            canonical_map = json.load(f)
        
        reversed_map = {}
        for canonical, raw_list in canonical_map.items():
            for raw_relation in raw_list:
                reversed_map[raw_relation.lower()] = canonical
        logging.info(f"Mapa de relaciones cargado y procesado desde '{mapping_file}'.")
        return reversed_map
    except Exception as e:
        logging.error(f"Error al cargar o procesar el archivo de mapeo '{mapping_file}': {e}")
        return None

def main():
    """Función principal para cargar los datos en Neo4j."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    relation_mapping = load_relation_mapping(RELATION_MAP_FILE)
    if relation_mapping is None:
        return

    try:
        with open(INPUT_TRIPLETS_FILE, 'r', encoding='utf-8') as f:
            all_triplets = json.load(f)
    except Exception as e:
        logging.error(f"Error al cargar el archivo de tripletas '{INPUT_TRIPLETS_FILE}': {e}")
        return
        
    neo_service = None
    try:
        neo_service = Neo4jService()
        uploader = Neo4jUploader(neo_service)
        
        logging.info(f"Subiendo {len(all_triplets)} tripletas a Neo4j...")
        for triplet in tqdm(all_triplets, desc="Cargando en Neo4j"):
            uploader.upload_triplet(triplet, relation_mapping)
            
    except Exception as e:
        logging.error(f"Error durante el proceso de carga a Neo4j: {e}")
    finally:
        if neo_service:
            neo_service.close()
        
    logging.info("\n¡Proceso de carga a Neo4j completado! 🚀")
    logging.info("Tu grafo de conocimiento está listo en la base de datos.")

if __name__ == "__main__":
    main()