# ...existing code...
from neo4j import GraphDatabase, basic_auth
import logging
from core.settings import settings

class Neo4jService:
    def __init__(self):
        # Do not create driver here to avoid blocking app startup.
        self._driver = None
        self._uri = settings.NEO4J_URI
        self._user = settings.NEO4J_USER
        self._password = settings.NEO4J_PASSWORD

    def _ensure_driver(self):
        if self._driver is None:
            try:
                self._driver = GraphDatabase.driver(
                    self._uri,
                    auth=basic_auth(self._user, self._password)
                )
                logging.info("Neo4j driver created for %s", self._uri)
            except Exception as e:
                logging.exception("Failed to create Neo4j driver: %s", e)
                raise

    def verify(self):
        """Opcional: llamada explícita para verificar conectividad (no automática en init)."""
        self._ensure_driver()
        try:
            self._driver.verify_connectivity()
            logging.info("Verified connectivity to Neo4j at %s", self._uri)
        except Exception:
            logging.exception("Neo4j verify_connectivity failed")
            raise

    def close(self):
        if self._driver is not None:
            try:
                self._driver.close()
                logging.info("Neo4j driver closed")
            except Exception:
                logging.exception("Error closing Neo4j driver")
            finally:
                self._driver = None

    def execute_query(self, query: str, parameters: dict = None) -> list:
        self._ensure_driver()
        try:
            logging.debug("Executing Neo4j query: %s params=%s", query, parameters)
            with self._driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            logging.exception("Error executing Neo4j query")
            raise