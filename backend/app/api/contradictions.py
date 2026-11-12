import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.entities import ResearchContradiction
from backend.app.models.contradiction_schemas import (
    DetectContradictionsRequest,
    DetectContradictionsResponse,
    ContradictionItem,
    ContradictionCategory,
    ContradictionNature
)
from backend.app.agents.contradiction_detector import contradiction_detector

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/contradictions",
    tags=["Contradiction Detection Agent"]
)

@router.get("/categories")
def get_contradiction_categories():
    """Returns supported contradiction analysis dimensions and nature classifications."""
    return {
        "categories": [c.value for c in ContradictionCategory],
        "natures": [n.value for n in ContradictionNature]
    }

@router.post("/detect", response_model=DetectContradictionsResponse)
def detect_contradictions(
    request: DetectContradictionsRequest,
    db: Session = Depends(get_db)
):
    """
    Identifies conflicting findings, opposing conclusions, experimental discrepancies,
    dataset inconsistencies, and conflicting algorithmic claims between research papers.
    Distinguishes genuine contradictions from differences caused by experimental conditions.
    """
    try:
        return contradiction_detector.detect_contradictions(request, db)
    except Exception as e:
        logger.error(f"Error in contradiction detection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect contradictions: {str(e)}"
        )

@router.get("/project/{project_id}", response_model=DetectContradictionsResponse)
def get_project_contradictions(
    project_id: str,
    category: Optional[str] = Query(None, description="Optional category filter"),
    nature: Optional[str] = Query(None, description="Optional nature filter"),
    db: Session = Depends(get_db)
):
    """
    Retrieves all detected contradictions for papers in a research project.
    """
    query = db.query(ResearchContradiction).filter(ResearchContradiction.project_id == project_id)
    if category:
        query = query.filter(ResearchContradiction.category == category)
    if nature:
        query = query.filter(ResearchContradiction.nature == nature)

    items = query.order_by(ResearchContradiction.created_at.desc()).all()
    if not items:
        # If none exist yet, automatically trigger detection
        req = DetectContradictionsRequest(project_id=project_id)
        return contradiction_detector.detect_contradictions(req, db)

    return contradiction_detector._build_response(items, None, db)

@router.get("/{contradiction_id}", response_model=ContradictionItem)
def get_contradiction_by_id(
    contradiction_id: str,
    db: Session = Depends(get_db)
):
    """Retrieves a single detected contradiction by unique ID."""
    c = db.query(ResearchContradiction).filter(ResearchContradiction.id == contradiction_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contradiction not found")

    p_a_title = c.paper_a.title if c.paper_a else "Source Paper A"
    p_b_title = c.paper_b.title if c.paper_b else "Source Paper B"

    return ContradictionItem(
        id=c.id,
        project_id=c.project_id,
        paper_a_id=c.paper_a_id,
        paper_b_id=c.paper_b_id,
        paper_a_title=p_a_title,
        paper_b_title=p_b_title,
        category=ContradictionCategory(c.category),
        nature=ContradictionNature(c.nature),
        title=c.title,
        description=c.description,
        passage_a=c.passage_a,
        passage_b=c.passage_b,
        page_a=c.page_a,
        page_b=c.page_b,
        section_a=c.section_a,
        section_b=c.section_b,
        root_cause_analysis=c.root_cause_analysis,
        severity=c.severity,
        confidence_score=c.confidence_score,
        status=c.status,
        created_at=c.created_at.isoformat() if hasattr(c.created_at, "isoformat") else str(c.created_at)
    )

@router.delete("/{contradiction_id}")
def delete_contradiction(
    contradiction_id: str,
    db: Session = Depends(get_db)
):
    """Deletes a detected contradiction record."""
    c = db.query(ResearchContradiction).filter(ResearchContradiction.id == contradiction_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contradiction not found")
    db.delete(c)
    db.commit()
    return {"status": "success", "message": f"Contradiction {contradiction_id} deleted"}
