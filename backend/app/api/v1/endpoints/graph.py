from fastapi import APIRouter
from backend.app.services.graph_service import graph_service
from backend.app.models.schemas import GraphResponse

router = APIRouter()

@router.get("/graph/overview", response_model=GraphResponse)
async def get_graph_overview():
    graph_data = graph_service.rebuild_graph_from_db()
    return graph_data

