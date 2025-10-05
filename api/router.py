# api/router.py
import logging
from fastapi import APIRouter, Request, HTTPException, Depends, Path
from pydantic import BaseModel
from typing import List

from infrastructure.neo4j_service import Neo4jService
from infrastructure.openai_service import OpenAIMessageService
from api.services.knowledge_graph_service import KnowledgeGraphService

router = APIRouter()

# --- Dependencias ---
def get_neo4j(request: Request) -> Neo4jService:
    neo = getattr(request.app.state, "neo4j", None)
    if neo is None:
        raise HTTPException(status_code=503, detail="Servicio de base de datos no disponible.")
    return neo

def get_openai_service() -> OpenAIMessageService:
    return OpenAIMessageService()
    
def get_kg_service(
    neo4j: Neo4jService = Depends(get_neo4j),
    openai: OpenAIMessageService = Depends(get_openai_service)
) -> KnowledgeGraphService:
    return KnowledgeGraphService(neo4j_service=neo4j, openai_service=openai)

# --- Modelos de Petición/Respuesta ---
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str

class CategoryResponse(BaseModel):
    category: str
    count: int

# --- Endpoints ---
@router.get("/hello", tags=["Status"])
def hello_endpoint(neo: Neo4jService = Depends(get_neo4j)):
    try:
        results = neo.execute_query("MATCH (n) RETURN count(n) AS count")
        count = results[0].get('count') if results else 0
        return {"message": "Hello from NASA Knowledge Engine!", "neo4j_node_count": count}
    except Exception as e:
        logging.exception("Neo4j query failed on /hello: %s", e)
        raise HTTPException(status_code=500, detail=f"Neo4j query failed: {e}")

@router.post("/query", response_model=QueryResponse, tags=["Knowledge Graph"])
def handle_query(
    request: QueryRequest,
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    if not request.question:
        raise HTTPException(status_code=400, detail="El campo 'question' no puede estar vacío.")
    
    try:
        logging.info(f"Recibida pregunta: {request.question}")
        answer = kg_service.generate_answer_with_citations(request.question)
        return QueryResponse(answer=answer)
    except Exception as e:
        logging.exception(f"Error al procesar la consulta: {e}")
        raise HTTPException(status_code=500, detail="Error interno al procesar la pregunta.")

@router.get("/categories/top/{limit}", response_model=List[CategoryResponse], tags=["Knowledge Graph"])
def get_top_categories(
    limit: int = Path(..., gt=0, le=100, description="El número de categorías a devolver (entre 1 y 100)"),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    Devuelve el top N de las categorías (tipos de relaciones) más frecuentes en el grafo de conocimiento.
    """
    try:
        logging.info(f"Solicitud para obtener el top {limit} de categorías.")
        top_categories = kg_service.get_top_categories(limit)
        return top_categories
    except Exception as e:
        logging.exception(f"Error al obtener el top {limit} de categorías: {e}")
        raise HTTPException(status_code=500, detail="Error interno al obtener las categorías.")