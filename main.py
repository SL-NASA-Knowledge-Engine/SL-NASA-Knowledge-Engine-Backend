from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging
import socket
import time
from urllib.parse import urlparse

from core.logging_config import LogLevels, configure_logging
from api.router import router
from infrastructure.neo4j_service import Neo4jService
from core.settings import settings


configure_logging(LogLevels.info)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager: create Neo4j driver at startup and close at shutdown.

    Performs a short TCP check with retries to fail fast if the host is unreachable,
    then initializes the driver (which also verifies connectivity).
    """

    def _tcp_check(uri: str, timeout: float = 3.0) -> bool:
        try:
            parsed = urlparse(uri)
            host = parsed.hostname
            port = parsed.port or 7687
            if not host:
                return False
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            return False

    # quick reachability check with a few retries
    retries = 3
    delay_seconds = 2
    reachable = False
    for attempt in range(1, retries + 1):
        if _tcp_check(settings.NEO4J_URI, timeout=3.0):
            reachable = True
            break
        logging.warning("Attempt %s/%s: Neo4j host not reachable yet, retrying in %ss...", attempt, retries, delay_seconds)
        time.sleep(delay_seconds)

    if not reachable:
        logging.error("Neo4j host %s not reachable after %s attempts", settings.NEO4J_URI, retries)
        raise RuntimeError(f"Neo4j host {settings.NEO4J_URI} not reachable")

    neo = None
    try:
        neo = Neo4jService()
        app.state.neo4j = neo
        logging.info("Neo4jService initialized")

        yield

    except Exception:
        logging.exception("Error during application startup or runtime")
        raise

    finally:
        if neo is not None:
            try:
                neo.close()
                logging.info("Neo4jService closed")
            except Exception:
                logging.exception("Error closing Neo4jService")


app = FastAPI(
    title="Withdrawal Advisor API",
    description="API para asesorar sobre retiros de inversión.",
    version="2.1.0",
    lifespan=lifespan,
)


app.include_router(router, prefix="/api/v1")