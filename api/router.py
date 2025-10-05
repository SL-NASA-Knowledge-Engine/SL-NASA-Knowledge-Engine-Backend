# api/router.py
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel

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