import io
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.database import get_db
from backend.app.models.entities import GeneratedReport, ResearchProject
from backend.app.services.report_generator_service import ReportGeneratorService

router = APIRouter(prefix="/api/reports", tags=["Research Reports"])

# -----------------------------------------------------------------------------
# Request & Response Schemas
# -----------------------------------------------------------------------------
class GenerateReportRequest(BaseModel):
    project_id: str = Field(..., description="Target Research Project UUID")
    report_type: str = Field(
        "literature_review",
        description="One of: literature_review, individual_paper, comparative_analysis, gap_analysis, contradiction_analysis, proposed_methodology"
    )
    citation_style: str = Field("IEEE", description="Citation formatting style: IEEE or APA")
    paper_ids: Optional[List[str]] = Field(None, description="Optional subset of paper UUIDs to constrain synthesis scope")
    custom_title: Optional[str] = Field(None, description="Optional custom title for the dossier")

class ReportSummaryItem(BaseModel):
    id: str
    project_id: str
    project_title: str
    report_title: str
    report_type: str
    generation_model: str
    citation_style: str
    word_count: int
    created_at: str
    updated_at: str

class ReportDetailResponse(BaseModel):
    id: str
    project_id: str
    project_title: str
    report_title: str
    report_type: str
    content_markdown: str
    generation_model: str
    citation_style: str
    word_count: int
    created_at: str
    updated_at: str

def _extract_citation_style(generation_model: str) -> str:
    if "APA" in (generation_model or ""):
        return "APA"
    return "IEEE"

def _clean_filename(title: str, ext: str) -> str:
    clean = re.sub(r'[^a-zA-Z0-9_\- ]+', '', title).strip().replace(' ', '_')
    return f"{clean or 'report'}.{ext}"

# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.post("/generate", response_model=ReportDetailResponse, status_code=201)
def generate_report(
    payload: GenerateReportRequest,
    db: Session = Depends(get_db)
):
    """
    Generates a grounded academic research report from verified SQLite data.
    Supports 6 report types, IEEE & APA citation standards, and auto-persists to history.
    """
    svc = ReportGeneratorService(db)
    try:
        report = svc.generate_report(
            project_id=payload.project_id,
            report_type=payload.report_type,
            citation_style=payload.citation_style,
            paper_ids=payload.paper_ids,
            custom_title=payload.custom_title,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")

    proj = db.query(ResearchProject).filter(ResearchProject.id == report.project_id).first()
    proj_title = proj.title if proj else "Unknown Project"
    words = len(report.content_markdown.split())

    return ReportDetailResponse(
        id=report.id,
        project_id=report.project_id,
        project_title=proj_title,
        report_title=report.report_title,
        report_type=report.report_type,
        content_markdown=report.content_markdown,
        generation_model=report.generation_model,
        citation_style=_extract_citation_style(report.generation_model),
        word_count=words,
        created_at=report.created_at.isoformat() if report.created_at else "",
        updated_at=report.updated_at.isoformat() if report.updated_at else "",
    )

@router.get("/history", response_model=List[ReportSummaryItem])
def list_report_history(
    project_id: Optional[str] = Query(None, description="Filter history by project ID"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Lists previously generated reports with metadata, citation style, and word count.
    """
    q = db.query(GeneratedReport)
    if project_id:
        q = q.filter(GeneratedReport.project_id == project_id)
    
    reports = q.order_by(desc(GeneratedReport.created_at)).limit(limit).all()

    # Pre-fetch projects
    proj_ids = list({r.project_id for r in reports})
    projs = db.query(ResearchProject).filter(ResearchProject.id.in_(proj_ids)).all() if proj_ids else []
    proj_map = {p.id: p.title for p in projs}

    results = []
    for r in reports:
        words = len((r.content_markdown or "").split())
        results.append(ReportSummaryItem(
            id=r.id,
            project_id=r.project_id,
            project_title=proj_map.get(r.project_id, "Unknown Project"),
            report_title=r.report_title,
            report_type=r.report_type,
            generation_model=r.generation_model or "Platform Engine",
            citation_style=_extract_citation_style(r.generation_model),
            word_count=words,
            created_at=r.created_at.isoformat() if r.created_at else "",
            updated_at=r.updated_at.isoformat() if r.updated_at else "",
        ))

    return results

@router.get("/{report_id}", response_model=ReportDetailResponse)
def get_report_by_id(
    report_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves full report content and metadata by ID.
    """
    report = db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    proj = db.query(ResearchProject).filter(ResearchProject.id == report.project_id).first()
    proj_title = proj.title if proj else "Unknown Project"
    words = len(report.content_markdown.split())

    return ReportDetailResponse(
        id=report.id,
        project_id=report.project_id,
        project_title=proj_title,
        report_title=report.report_title,
        report_type=report.report_type,
        content_markdown=report.content_markdown,
        generation_model=report.generation_model,
        citation_style=_extract_citation_style(report.generation_model),
        word_count=words,
        created_at=report.created_at.isoformat() if report.created_at else "",
        updated_at=report.updated_at.isoformat() if report.updated_at else "",
    )

@router.get("/{report_id}/export/{export_format}")
def export_report_file(
    report_id: str,
    export_format: str,
    db: Session = Depends(get_db)
):
    """
    Exports report in requested format:
    - `pdf`: Publication-grade PDF with academic typography, running headers/footers, and page numbers.
    - `docx`: Microsoft Word OpenXML document.
    - `markdown` or `md`: Clean academic Markdown file.
    """
    report = db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    svc = ReportGeneratorService(db)
    fmt = export_format.lower().strip()

    if fmt in ["markdown", "md"]:
        content = svc.export_markdown(report)
        filename = _clean_filename(report.report_title, "md")
        return Response(
            content=content,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    elif fmt == "pdf":
        try:
            pdf_bytes = svc.export_pdf(report)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
        filename = _clean_filename(report.report_title, "pdf")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    elif fmt == "docx":
        try:
            docx_bytes = svc.export_docx(report)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DOCX generation failed: {str(e)}")
        filename = _clean_filename(report.report_title, "docx")
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported export format '{export_format}'. Supported formats: pdf, docx, markdown."
        )

@router.delete("/{report_id}")
def delete_report(
    report_id: str,
    db: Session = Depends(get_db)
):
    """
    Deletes report record from SQLite database.
    """
    report = db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    db.delete(report)
    db.commit()
    return {"status": "success", "message": f"Report '{report.report_title}' deleted successfully", "id": report_id}

