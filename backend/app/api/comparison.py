import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.entities import PaperComparison, ResearchProject, ResearchPaper
from backend.app.models.comparison_schemas import (
    CreateComparisonRequest,
    CreateComparisonResponse,
    CrossPaperComparisonReport,
    ComparisonListItem,
    MatrixRow,
    SimilarityItem,
    MethodologicalDifferenceItem,
    DatasetComparisonItem,
    EvaluationComparisonItem,
    ComparabilityAssessment,
    ContradictoryFindingItem,
    UnderexploredApproachItem
)
from backend.app.services.comparison_agent import comparison_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/comparison", tags=["Cross-Paper Comparison Agent"])

@router.post("/compare", response_model=CreateComparisonResponse)
async def generate_cross_paper_comparison(
    req: CreateComparisonRequest,
    db: Session = Depends(get_db)
):
    """
    Cross-Paper Comparison Agent:
    Compares 2 to 5 academic research papers simultaneously.

    Generates:
    1. Comparative analysis matrix (13 criteria across papers with page citations)
    2. Similarity analysis across research aims & evaluation protocols
    3. Methodological differences & theoretical paradigms
    4. Dataset comparison & benchmark cross-mapping
    5. Evaluation comparison & rigor-backed Comparability Assessment (preventing false superiority claims)
    6. Contradictory findings with attached evidence passages
    7. Underexplored approaches and architectural synergies
    8. Publication-ready written comparative summary in Markdown
    """
    report = await comparison_agent.compare_papers(
        db=db,
        paper_ids=req.paper_ids,
        project_id=req.project_id,
        title=req.title,
        force_regenerate=req.force_regenerate
    )

    msg = "Retrieved cached cross-paper comparison." if report.is_cached else "Cross-paper comparative study generated and persistently saved."

    return CreateComparisonResponse(
        comparison_id=report.comparison_id,
        comparison_title=report.comparison_title,
        total_papers_compared=len(report.compared_papers),
        report=report,
        message=msg
    )

@router.get("/{comparison_id}", response_model=CrossPaperComparisonReport)
async def get_comparison_by_id(
    comparison_id: str,
    db: Session = Depends(get_db)
):
    """Retrieves an existing saved cross-paper comparison report by ID."""
    comp = db.query(PaperComparison).filter(PaperComparison.id == comparison_id).first()
    if not comp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comparison with ID '{comparison_id}' not found."
        )

    paper_ids = json.loads(comp.paper_ids)
    papers = db.query(ResearchPaper).filter(ResearchPaper.id.in_(paper_ids)).all()
    compared_meta = [
        {"id": p.id, "title": p.title, "year": p.publication_year, "doi": p.doi}
        for p in papers
    ]

    diff_payload = json.loads(comp.differences_json)
    method_diffs = diff_payload.get("methodological", [])
    dataset_diffs = diff_payload.get("datasets", [])
    eval_diffs = diff_payload.get("evaluations", [])

    return CrossPaperComparisonReport(
        comparison_id=comp.id,
        comparison_title=comp.comparison_title,
        project_id=comp.project_id,
        compared_papers=compared_meta,
        matrix=[MatrixRow(**r) for r in json.loads(comp.matrix_json)],
        similarities=[SimilarityItem(**s) for s in json.loads(comp.similarity_json)],
        methodological_differences=[MethodologicalDifferenceItem(**d) for d in method_diffs],
        dataset_comparison=[DatasetComparisonItem(**ds) for ds in dataset_diffs],
        evaluation_comparison=[EvaluationComparisonItem(**ev) for ev in eval_diffs],
        comparability_assessment=ComparabilityAssessment(**json.loads(comp.comparability_json)),
        contradictory_findings=[ContradictoryFindingItem(**c) for c in json.loads(comp.contradictions_json)],
        underexplored_approaches=[UnderexploredApproachItem(**u) for u in json.loads(comp.underexplored_json)],
        comparative_summary_markdown=comp.comparative_summary,
        model_used=comp.model_used,
        created_at=comp.created_at.isoformat(),
        is_cached=True
    )

@router.get("/project/{project_id}", response_model=List[ComparisonListItem])
async def list_project_comparisons(
    project_id: str,
    db: Session = Depends(get_db)
):
    """Lists all saved cross-paper comparisons for a research project."""
    comps = db.query(PaperComparison).filter(PaperComparison.project_id == project_id).order_by(PaperComparison.created_at.desc()).all()
    results = []
    for c in comps:
        try:
            pids = json.loads(c.paper_ids)
            results.append(ComparisonListItem(
                comparison_id=c.id,
                comparison_title=c.comparison_title,
                project_id=c.project_id,
                paper_count=len(pids),
                created_at=c.created_at.isoformat()
            ))
        except Exception:
            pass
    return results

@router.get("/{comparison_id}/markdown")
async def get_comparison_markdown_export(
    comparison_id: str,
    db: Session = Depends(get_db)
):
    """Returns the formatted comparative synthesis in Markdown for reading or export."""
    comp = db.query(PaperComparison).filter(PaperComparison.id == comparison_id).first()
    if not comp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comparison with ID '{comparison_id}' not found."
        )
    return Response(content=comp.comparative_summary, media_type="text/markdown")

