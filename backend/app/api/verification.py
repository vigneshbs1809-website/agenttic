import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.entities import ResearchPaper, VerificationResult
from backend.app.models.verification_schemas import (
    VerifyClaimRequest,
    VerificationResultResponse,
    BatchVerifyClaimsRequest,
    BatchVerifyClaimsResponse
)
from backend.app.services.verification_agent import verification_agent

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/verification",
    tags=["Evidence Verification"]
)

@router.post("/verify-claim", response_model=VerificationResultResponse)
async def verify_single_claim(
    request: VerifyClaimRequest,
    db: Session = Depends(get_db)
):
    """
    Independently validates a research claim against the original PDF evidence.
    Returns: claim_text, source_paper, original_evidence, page_number, verification_status, explanation.
    Unsupported claims are marked with is_verified_finding=False.
    """
    try:
        return await verification_agent.verify_claim(request=request, db=db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error during claim verification: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}"
        )

@router.post("/batch", response_model=BatchVerifyClaimsResponse)
async def batch_verify_claims(
    request: BatchVerifyClaimsRequest,
    db: Session = Depends(get_db)
):
    """
    Batch validates multiple claims against source evidence.
    """
    try:
        return await verification_agent.batch_verify(claims=request.claims, db=db)
    except Exception as e:
        logger.error(f"Error during batch verification: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch verification failed: {str(e)}"
        )

@router.post("/verify-gap/{gap_id}", response_model=List[VerificationResultResponse])
async def verify_research_gap_evidences(
    gap_id: str,
    db: Session = Depends(get_db)
):
    """
    Validates all evidence passages associated with an identified research gap.
    """
    try:
        return await verification_agent.verify_gap(gap_id=gap_id, db=db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error verifying research gap {gap_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gap verification failed: {str(e)}"
        )

@router.get("/history", response_model=List[VerificationResultResponse])
async def get_verification_history(
    paper_id: Optional[str] = Query(default=None, description="Filter history by paper ID"),
    limit: int = Query(default=50, ge=1, le=200, description="Max records to retrieve"),
    db: Session = Depends(get_db)
):
    """
    Retrieves stored verification results from SQLite.
    """
    query = db.query(VerificationResult)
    if paper_id:
        query = query.filter(VerificationResult.paper_id == paper_id)

    records = query.order_by(VerificationResult.created_at.desc()).limit(limit).all()
    results = []
    for r in records:
        paper = db.query(ResearchPaper).filter(ResearchPaper.id == r.paper_id).first()
        is_verified = r.verification_status in ["Supported", "Partially Supported"]
        results.append(
            VerificationResultResponse(
                id=r.id,
                claim_text=r.claim_text or "Claim",
                source_paper={"paper_id": r.paper_id or "unknown", "title": paper.title if paper else "Unknown Paper"},
                original_evidence=r.supporting_evidence or r.counter_evidence,
                page_number=r.page_number,
                section_title=r.notes,
                verification_status=r.verification_status,
                explanation=r.explanation or "",
                similarity_score=r.verification_score or 1.0,
                is_verified_finding=is_verified,
                created_at=str(r.created_at)
            )
        )
    return results

