import logging
from neo4j import GraphDatabase, basic_auth
from core.settings import settings

class Neo4jService:
    def __init__(self):
        try:
            # Create driver and verify connectivity immediately so startup fails fast
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=basic_auth(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            self.driver.verify_connectivity()
            logging.info("Connected to Neo4j at %s", settings.NEO4J_URI)
        except Exception as e:
            logging.exception("Failed to initialize Neo4j driver: %s", e)
            # Re-raise so callers (e.g. app startup) can handle/fail appropriately
            raise

    def close(self):
        self.driver.close()

    def execute_query(self, query: str, parameters: dict = None) -> list:
        try:
            logging.info(f"Executing Neo4j query: {query} with parameters: {parameters}")
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            logging.error(f"Error executing Neo4j query: {str(e)}")
            raise ConnectionError("Error executing Neo4j query.")