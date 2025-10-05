# infrastructure/neo4j_service.py
from neo4j import GraphDatabase, basic_auth
import logging
from core.settings import settings

class Neo4jService:
    def __init__(self):
        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=basic_auth(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            self._driver.verify_connectivity()
            logging.info("Conexión con Neo4j establecida y verificada.")
        except Exception as e:
            logging.error(f"Error al crear o verificar el driver de Neo4j: {e}")
            raise

    def close(self):
        if self._driver is not None:
            self._driver.close()
            logging.info("Conexión con Neo4j cerrada.")

    def execute_query(self, query: str, parameters: dict = None) -> list:
        try:
            with self._driver.session() as session:
                result = session.run(query, parameters or {})
                # Devuelve una lista de diccionarios, que es más fácil de usar
                return [record.data() for record in result]
        except Exception as e:
            logging.error(f"Error al ejecutar la consulta en Neo4j: {e}")
            raise