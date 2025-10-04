# withdrawal_advisor/router.py
import logging
from fastapi import APIRouter, Request, HTTPException, Depends

from infrastructure.neo4j_service import Neo4jService

router = APIRouter()


def get_neo4j(request: Request) -> Neo4jService:
    """Dependency that returns the initialized Neo4jService from app.state.

    Raises HTTPException(500) if the service is not initialized.
    """
    neo = getattr(request.app.state, "neo4j", None)
    if neo is None:
        logging.error("Neo4j service not initialized in app.state")
        raise HTTPException(status_code=500, detail="Neo4j service not initialized")
    return neo


@router.get("/hello")
def api_router(neo: Neo4jService = Depends(get_neo4j)):
    """Endpoint de prueba que ejecuta una consulta simple en Neo4j.

    Usa la dependencia `get_neo4j` para obtener el servicio ya inicializado en el
    lifespan de la aplicación.
    """
    try:
        results = neo.execute_query("MATCH (n) RETURN count(n) AS count")
        count = results[0].get('count') if results else 0
        return {"message": "Hello World", "neo4j_node_count": count}
    except Exception as e:
        logging.exception("Neo4j query failed on /hello: %s", e)
        raise HTTPException(status_code=500, detail="Neo4j query failed")