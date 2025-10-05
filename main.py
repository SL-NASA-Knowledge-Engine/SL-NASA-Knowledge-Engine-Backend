# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

from core.logging_config import LogLevels, configure_logging
from api.router import router as api_router
from infrastructure.neo4j_service import Neo4jService

# Configura el logging al inicio
configure_logging(LogLevels.info)

# Variable global para mantener la conexión a la base de datos
neo4j_service_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja el ciclo de vida de la aplicación: crea el driver de Neo4j al iniciar
    y lo cierra al apagar.
    """
    global neo4j_service_instance
    logging.info("Iniciando aplicación y conexión a Neo4j...")
    
    try:
        # Inicializa la conexión a Neo4j al arrancar
        neo4j_service_instance = Neo4jService()
        app.state.neo4j = neo4j_service_instance
        logging.info("Servicio de Neo4j inicializado y conectado.")
        
        yield # La aplicación está activa y lista para recibir peticiones
        
    finally:
        # Cierra la conexión al apagar la aplicación
        if neo4j_service_instance:
            neo4j_service_instance.close()
        logging.info("Aplicación apagada y conexión a Neo4j cerrada.")

app = FastAPI(
    title="NASA Knowledge Engine API",
    description="Una API para explorar el conocimiento de las publicaciones de biociencia de la NASA a través de un GraphRAG.",
    version="1.0.0",
    lifespan=lifespan,
)

# Incluir el router de la API
app.include_router(api_router, prefix="/api/v1")

@app.get("/", summary="Endpoint raíz de bienvenida", tags=["Status"])
def read_root():
    return {"message": "Bienvenido a la API del NASA Knowledge Engine"}