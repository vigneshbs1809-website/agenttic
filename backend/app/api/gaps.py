import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.entities import ResearchProject, ResearchGap, GapEvidence
from backend.app.models.gap_schemas import (
    ResearchGapResponse,
    DiscoverGapsRequest,
    DiscoverGapsResponse,
    UpdateGapRequest
)
from backend.app.services.gap_agent import gap_agent, GAP_CATEGORIES

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/gaps",
    tags=["Research Gap Discovery"]
)

@router.get("/categories", response_model=List[str])
async def get_gap_categories():
    """Returns the list of 10 academic research gap categories."""
    return GAP_CATEGORIES

@router.post("/discover/{project_id}", response_model=DiscoverGapsResponse)
async def discover_research_gaps(
    project_id: str,
    request: DiscoverGapsRequest = DiscoverGapsRequest(),
    db: Session = Depends(get_db)
):
    """
    Core contribution endpoint: Discovers both explicit author-stated limitations
    and implicit cross-paper comparative research gaps across 10 dimensions.
    """
    try:
        return await gap_agent.discover_project_gaps(
            project_id=project_id,
            db=db,
            include_explicit=request.include_explicit,
            include_implicit=request.include_implicit,
            force_rediscover=request.force_rediscover
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error discovering research gaps for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover research gaps: {str(e)}"
        )

@router.get("", response_model=DiscoverGapsResponse)
async def list_research_gaps(
    project_id: Optional[str] = Query(default=None, description="Filter by project ID"),
    gap_type: Optional[str] = Query(default=None, description="Filter by category (e.g. methodological, dataset)"),
    identification_method: Optional[str] = Query(default=None, description="Filter by method: explicit_author_stated vs implicit_system_inferred"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status: open, approved, rejected, addressed, verified"),
    db: Session = Depends(get_db)
):
    """
    Lists research gaps across all projects or filtered by project, category, method, or status.
    """
    query = db.query(ResearchGap)
    if project_id:
        query = query.filter(ResearchGap.project_id == project_id)
    if gap_type:
        query = query.filter(ResearchGap.gap_type == gap_type)
    if identification_method:
        query = query.filter(ResearchGap.identification_method == identification_method)
    if status_filter:
        query = query.filter(ResearchGap.status == status_filter)

    gaps = query.order_by(ResearchGap.confidence_score.desc()).all()
    return gap_agent._build_response(project_id or "all", gaps, db)

@router.get("/project/{project_id}", response_model=DiscoverGapsResponse)
async def get_project_gaps(
    project_id: str,
    gap_type: Optional[str] = Query(default=None, description="Filter by category (e.g. methodological, dataset, scalability)"),
    identification_method: Optional[str] = Query(default=None, description="Filter by method: explicit_author_stated vs implicit_system_inferred"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status: open, addressed, verified"),
    db: Session = Depends(get_db)
):
    """
    Retrieves persistently stored research gaps for a project with optional filters.
    """
    project = db.query(ResearchProject).filter(ResearchProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    query = db.query(ResearchGap).filter(ResearchGap.project_id == project_id)

    if gap_type:
        query = query.filter(ResearchGap.gap_type == gap_type)
    if identification_method:
        query = query.filter(ResearchGap.identification_method == identification_method)
    if status_filter:
        query = query.filter(ResearchGap.status == status_filter)

    gaps = query.order_by(ResearchGap.confidence_score.desc()).all()

    if not gaps and not gap_type and not identification_method and not status_filter:
        # Auto-discover if none present
        try:
            return await gap_agent.discover_project_gaps(
                project_id=project_id, db=db, force_rediscover=False
            )
        except Exception as e:
            logger.warning(f"Auto-discovery failed: {e}")

    return gap_agent._build_response(project_id, gaps, db)

@router.get("/{gap_id}", response_model=ResearchGapResponse)
async def get_research_gap_by_id(
    gap_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves full details, evidence citations, and counter-evidence for a specific gap.
    """
    gap = db.query(ResearchGap).filter(ResearchGap.id == gap_id).first()
    if not gap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Research gap '{gap_id}' not found.")

    resp = gap_agent._build_response(gap.project_id, [gap], db)
    if not resp.gaps:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gap details not available.")
    return resp.gaps[0]

@router.put("/{gap_id}", response_model=ResearchGapResponse)
async def update_research_gap(
    gap_id: str,
    request: UpdateGapRequest,
    db: Session = Depends(get_db)
):
    """
    Updates the status (open, addressed, verified), title, description,
    or suggested direction of a research gap.
    """
    gap = db.query(ResearchGap).filter(ResearchGap.id == gap_id).first()
    if not gap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Research gap '{gap_id}' not found.")

    if request.status is not None:
        valid_statuses = ["open", "addressed", "verified", "approved", "rejected"]
        if request.status.lower() not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Status must be one of: {', '.join(valid_statuses)}."
            )
        gap.status = request.status.lower()

    if request.title is not None:
        gap.title = request.title[:490]
    if request.description is not None:
        gap.description = request.description
    if request.suggested_direction is not None:
        gap.suggested_direction = request.suggested_direction

    db.commit()
    db.refresh(gap)

    resp = gap_agent._build_response(gap.project_id, [gap], db)
    return resp.gaps[0]

@router.delete("/{gap_id}")
async def delete_research_gap(
    gap_id: str,
    db: Session = Depends(get_db)
):
    """
    Deletes a research gap and its cascade evidences from SQLite.
    """
    gap = db.query(ResearchGap).filter(ResearchGap.id == gap_id).first()
    if not gap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Research gap '{gap_id}' not found.")

    db.delete(gap)
    db.commit()
    return {"message": f"Research gap '{gap_id}' deleted successfully.", "id": gap_id}

