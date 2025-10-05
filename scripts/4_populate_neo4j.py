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
        # Preserve original casing; trimming only
        source = str(triplet.get('source', '')).strip()
        target = str(triplet.get('target', '')).strip()
        raw_relation = str(triplet.get('relation', '')).strip().lower()
        source_doc = triplet.get('source_doc', 'Unknown')

        if not source or not target or not raw_relation:
            return

        # Busca la relación canónica, si no existe, usa 'RELATED_TO' como default
        canonical_relation = relation_mapping.get(raw_relation, 'RELATED_TO')
        
        # Consulta Cypher que usa MERGE para evitar duplicados de nodos y relaciones
        # Se crea una relación por cada documento fuente para preservar la trazabilidad
        # Add a pipeline-specific label (SL_PIPELINE) so we can safely wipe only nodes created by this pipeline
        query = (
            "MERGE (s:Entity:SL_PIPELINE {name: $source_name}) "
            "MERGE (t:Entity:SL_PIPELINE {name: $target_name}) "
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

def wipe_database(neo_service: Neo4jService, mode: str = 'pipeline'):
    """Wipe data from the database.

    mode: 'pipeline' deletes only nodes with :SL_PIPELINE label.
          'all' drops all nodes (requires caution).
    """
    if mode == 'pipeline':
        logging.info("Eliminando nodos creados por el pipeline (:SL_PIPELINE) ...")
        try:
            neo_service.execute_query("MATCH (n:SL_PIPELINE) DETACH DELETE n")
            logging.info("Borrado de nodos con :SL_PIPELINE completado.")
        except Exception as e:
            logging.error(f"Error al borrar nodos de pipeline: {e}")
            raise
    elif mode == 'all':
        logging.info("ELIMINANDO TODA LA BASE DE DATOS (MATCH (n) DETACH DELETE n) ...")
        try:
            neo_service.execute_query("MATCH (n) DETACH DELETE n")
            logging.info("Borrado completo de la base de datos finalizado.")
        except Exception as e:
            logging.error(f"Error al borrar toda la base de datos: {e}")
            raise
    else:
        logging.error(f"Modo de borrado desconocido: {mode}")
        raise ValueError("Modo de borrado desconocido")

def main():
    """Función principal para cargar los datos en Neo4j."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Initialize Neo4j early (we'll wipe the entire DB unconditionally before uploading)
    neo_service = None
    try:
        neo_service = Neo4jService()
    except Exception as e:
        logging.error(f"No se pudo inicializar Neo4jService: {e}")
        return

    try:
        # Wipe the entire database (user requested automatic full wipe on every run)
        logging.info("Wiping entire Neo4j database before upload (MATCH (n) DETACH DELETE n)")
        wipe_database(neo_service, mode='all')

        relation_mapping = load_relation_mapping(RELATION_MAP_FILE)
        if relation_mapping is None:
            return

        try:
            with open(INPUT_TRIPLETS_FILE, 'r', encoding='utf-8') as f:
                all_triplets = json.load(f)
        except Exception as e:
            logging.error(f"Error al cargar el archivo de tripletas '{INPUT_TRIPLETS_FILE}': {e}")
            return

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