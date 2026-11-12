import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.entities import ResearchPaper, ExtractedEntity, ResearchClaim, PaperCitation
from backend.app.models.graph_schemas import (
    GraphResponse,
    GraphFilterQuery,
    ExtractedEntityResponse,
    ResearchClaimResponse,
    PaperCitationResponse,
    ExtractionResultResponse
)
from backend.app.services.graph_service import graph_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/graph",
    tags=["Research Knowledge Graph"]
)

@router.get("/overview", response_model=GraphResponse)
async def get_global_graph_overview(
    max_papers: int = Query(default=50, ge=1, le=200, description="Max papers to include in the graph"),
    algorithm: Optional[str] = Query(default=None, description="Filter by algorithm name"),
    year: Optional[int] = Query(default=None, description="Filter by publication year"),
    start_year: Optional[int] = Query(default=None, description="Filter by start year"),
    end_year: Optional[int] = Query(default=None, description="Filter by end year"),
    topic: Optional[str] = Query(default=None, description="Filter by research topic"),
    include_citations: bool = Query(default=True, description="Include verified citations"),
    include_methodology_sharing: bool = Query(default=True, description="Include shared methodology edges"),
    db: Session = Depends(get_db)
):
    """
    Returns the Research Knowledge Graph linking papers, authors, algorithms,
    datasets, problems, topics, metrics, and limitations.
    Supports filtering by algorithm, year, and topic.
    """
    try:
        filters = GraphFilterQuery(
            algorithm=algorithm,
            year=year,
            start_year=start_year,
            end_year=end_year,
            topic=topic,
            include_citations=include_citations,
            include_methodology_sharing=include_methodology_sharing,
            max_nodes=max_papers * 5
        )
        return await graph_service.get_filtered_knowledge_graph(db=db, filters=filters)
    except Exception as e:
        logger.error(f"Error generating overview graph: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate overview graph: {str(e)}"
        )

@router.post("/query", response_model=GraphResponse)
async def query_knowledge_graph(
    filters: GraphFilterQuery,
    project_id: Optional[str] = Query(default=None, description="Optional project ID constraint"),
    db: Session = Depends(get_db)
):
    """
    Queries the knowledge graph with full filter criteria (paper, algorithm, year, topic).
    """
    try:
        return await graph_service.get_filtered_knowledge_graph(
            db=db,
            filters=filters,
            project_id=project_id
        )
    except Exception as e:
        logger.error(f"Error filtering knowledge graph: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to filter knowledge graph: {str(e)}"
        )

@router.get("/paper/{paper_id}", response_model=GraphResponse)
async def get_paper_knowledge_graph(
    paper_id: str,
    include_citations: bool = Query(default=True, description="Whether to include citation relationships"),
    include_methodology_sharing: bool = Query(default=True, description="Whether to include shared methodology relationships"),
    db: Session = Depends(get_db)
):
    """
    Returns the ego-graph centered on a specific research paper,
    linking its algorithms, datasets, problems, topics, metrics, limitations, and citations.
    """
    paper = db.query(ResearchPaper).filter(ResearchPaper.id == paper_id).first()
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research paper '{paper_id}' not found."
        )

    try:
        filters = GraphFilterQuery(
            paper_id=paper_id,
            include_citations=include_citations,
            include_methodology_sharing=include_methodology_sharing
        )
        return await graph_service.get_filtered_knowledge_graph(db=db, filters=filters)
    except Exception as e:
        logger.error(f"Error generating paper graph for {paper_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate paper graph: {str(e)}"
        )

@router.get("/project/{project_id}", response_model=GraphResponse)
async def get_project_knowledge_graph(
    project_id: str,
    algorithm: Optional[str] = Query(default=None, description="Filter by algorithm"),
    year: Optional[int] = Query(default=None, description="Filter by year"),
    topic: Optional[str] = Query(default=None, description="Filter by topic"),
    db: Session = Depends(get_db)
):
    """
    Returns the knowledge graph for all papers inside a specific research project,
    with optional filtering by algorithm, year, and topic.
    """
    try:
        filters = GraphFilterQuery(
            algorithm=algorithm,
            year=year,
            topic=topic
        )
        return await graph_service.get_filtered_knowledge_graph(
            db=db,
            filters=filters,
            project_id=project_id
        )
    except Exception as e:
        logger.error(f"Error generating project graph for {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate project graph: {str(e)}"
        )

@router.get("/citations", response_model=List[PaperCitationResponse])
async def get_verified_citations(
    paper_id: Optional[str] = Query(default=None, description="Filter citations for a specific citing or cited paper"),
    db: Session = Depends(get_db)
):
    """
    Returns strictly verified paper citations extracted from paper references.
    """
    query = db.query(PaperCitation)
    if paper_id:
        query = query.filter(
            (PaperCitation.citing_paper_id == paper_id) |
            (PaperCitation.cited_paper_id == paper_id)
        )

    citations = query.all()
    results = []
    for c in citations:
        citing = db.query(ResearchPaper).filter(ResearchPaper.id == c.citing_paper_id).first()
        cited = db.query(ResearchPaper).filter(ResearchPaper.id == c.cited_paper_id).first()
        results.append(
            PaperCitationResponse(
                id=c.id,
                citing_paper_id=c.citing_paper_id,
                citing_paper_title=citing.title if citing else "Unknown Paper",
                cited_paper_id=c.cited_paper_id,
                cited_paper_title=cited.title if cited else "Unknown Paper",
                citation_text=c.citation_text,
                is_verified=c.is_verified,
                confidence=c.confidence
            )
        )
    return results

@router.post("/extract/{paper_id}", response_model=ExtractionResultResponse)
async def extract_paper_entities_and_claims(
    paper_id: str,
    force: bool = Query(default=False, description="Force re-extraction even if entities exist"),
    db: Session = Depends(get_db)
):
    """
    Triggers entity and citation extraction for a paper and persists results in SQLite.
    """
    try:
        result = await graph_service.extract_entities_and_claims(
            paper_id=paper_id,
            db=db,
            force=force
        )
        return ExtractionResultResponse(
            paper_id=paper_id,
            entities_extracted=result.get("entities_count", 0),
            claims_extracted=result.get("claims_count", 0),
            status=result.get("status", "success")
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error extracting entities for paper {paper_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract entities: {str(e)}"
        )

@router.post("/extract/project/{project_id}")
async def extract_project_entities_and_claims(
    project_id: str,
    force: bool = Query(default=False, description="Force re-extraction even if entities exist"),
    db: Session = Depends(get_db)
):
    """
    Triggers entity and citation extraction for all papers in a project.
    """
    papers = db.query(ResearchPaper).filter(ResearchPaper.project_id == project_id).all()
    if not papers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No papers found for project {project_id}"
        )

    results = []
    for paper in papers:
        try:
            res = await graph_service.extract_entities_and_claims(paper.id, db, force=force)
            results.append(res)
        except Exception as e:
            logger.warning(f"Extraction failed for paper {paper.id}: {e}")
            results.append({"paper_id": paper.id, "error": str(e), "status": "failed"})

    return {
        "project_id": project_id,
        "total_papers": len(papers),
        "results": results
    }

@router.get("/entities/{paper_id}", response_model=List[ExtractedEntityResponse])
async def get_paper_entities(
    paper_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns the list of persistent extracted entities for a paper.
    """
    paper = db.query(ResearchPaper).filter(ResearchPaper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Paper {paper_id} not found.")

    entities = db.query(ExtractedEntity).filter(ExtractedEntity.paper_id == paper_id).all()
    if not entities:
        await graph_service.extract_entities_and_claims(paper_id, db)
        entities = db.query(ExtractedEntity).filter(ExtractedEntity.paper_id == paper_id).all()

    return entities

@router.get("/claims/{paper_id}", response_model=List[ResearchClaimResponse])
async def get_paper_claims(
    paper_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns the list of persistent research claims for a paper.
    """
    paper = db.query(ResearchPaper).filter(ResearchPaper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Paper {paper_id} not found.")

    claims = db.query(ResearchClaim).filter(ResearchClaim.paper_id == paper_id).all()
    if not claims:
        await graph_service.extract_entities_and_claims(paper_id, db)
        claims = db.query(ResearchClaim).filter(ResearchClaim.paper_id == paper_id).all()

    return claims
