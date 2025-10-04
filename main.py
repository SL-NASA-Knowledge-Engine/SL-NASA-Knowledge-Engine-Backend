# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging
import sys

from core.logging_config import LogLevels, configure_logging
from api.router import router
from infraestructure.neo4j_service import Neo4jService


configure_logging(LogLevels.info)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager: crea el servicio de Neo4j al arrancar y lo cierra al apagar."""
    neo = None
    try:
        # setup
        neo = Neo4jService()
        app.state.neo4j = neo
        logging.info("Neo4jService initialized")

        # gives the control to the server while the app is running
        yield

    except Exception as e:
        # If the startup fails (for example, if it cannot connect to Neo4j),
        # we re-raise the exception to prevent the app from starting.
        logging.exception(f"Error during application startup or runtime: {e}")
        raise

    finally:
        # teardown: we ensure the driver is closed if it was created
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