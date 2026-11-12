import re
import os
import io
import time
import uuid
import hashlib
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import httpx
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status

from backend.app.core.config import settings
from backend.app.models.entities import ResearchProject, ResearchPaper, Author
from backend.app.models.discovery_schemas import DiscoveredPaper, DiscoverySearchRequest
from backend.app.services.document_processing import document_processor

logger = logging.getLogger(__name__)

def normalize_title(title: str) -> str:
    """Normalizes title string for duplicate detection across APIs."""
    if not title:
        return ""
    # Lowercase, remove all non-alphanumeric characters and excessive whitespace
    return re.sub(r"[^a-z0-9]", "", title.lower())

def normalize_doi(doi: Optional[str]) -> Optional[str]:
    """Extracts raw DOI string (e.g. '10.1038/s41586-020-2649-2')."""
    if not doi:
        return None
    cleaned = doi.strip().lower()
    for prefix in ["https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:"]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
    return cleaned.strip()

def reconstruct_openalex_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> Optional[str]:
    """Reconstructs linear text from OpenAlex inverted abstract index."""
    if not inverted_index or not isinstance(inverted_index, dict):
        return None
    try:
        word_pos = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_pos.append((pos, word))
        word_pos.sort(key=lambda x: x[0])
        return " ".join(w for _, w in word_pos)
    except Exception as e:
        logger.debug(f"Could not reconstruct OpenAlex abstract: {e}")
        return None

class ResearchDiscoveryAgent:
    def __init__(self):
        self.timeout = settings.ACADEMIC_SEARCH_TIMEOUT_SECONDS
        self.pdf_dir = Path(settings.PDF_STORAGE_DIR)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.default_headers = {
            "User-Agent": f"LiteratureIntelligencePlatform/1.0 (mailto:{settings.OPENALEX_EMAIL})"
        }

    async def search_openalex(
        self,
        query: str,
        limit: int = 10,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        author: Optional[str] = None,
        open_access_only: bool = False
    ) -> List[DiscoveredPaper]:
        """Queries OpenAlex API for academic works."""
        papers: List[DiscoveredPaper] = []
        url = "https://api.openalex.org/works"
        
        params: Dict[str, Any] = {
            "search": query,
            "per-page": min(limit, 50),
            "sort": "relevance_score:desc"
        }

        filters = []
        if year_start and year_end:
            filters.append(f"publication_year:{year_start}-{year_end}")
        elif year_start:
            filters.append(f"publication_year:{year_start}-")
        elif year_end:
            filters.append(f"publication_year:-{year_end}")
        if open_access_only:
            filters.append("is_oa:true")
        if filters:
            params["filter"] = ",".join(filters)

        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.default_headers) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    for item in data.get("results", []):
                        title = (item.get("title") or "").strip()
                        if not title:
                            continue

                        doi = normalize_doi(item.get("doi"))
                        abstract = reconstruct_openalex_abstract(item.get("abstract_inverted_index"))
                        year = item.get("publication_year")

                        # Extract authors
                        authors = []
                        for auth_info in item.get("authorships", []):
                            name = auth_info.get("author", {}).get("display_name")
                            if name:
                                authors.append(name.strip())

                        # Open access & links
                        oa_info = item.get("open_access", {}) or {}
                        is_oa = oa_info.get("is_oa", False)
                        primary_loc = item.get("primary_location", {}) or {}
                        pdf_url = primary_loc.get("pdf_url") or oa_info.get("oa_url")
                        landing_url = primary_loc.get("landing_page_url") or item.get("doi") or item.get("id")
                        venue = primary_loc.get("source", {}).get("display_name") if primary_loc.get("source") else None

                        paper_id = doi or hashlib.md5(title.lower().encode("utf-8")).hexdigest()[:16]

                        papers.append(DiscoveredPaper(
                            id=paper_id,
                            title=title,
                            abstract=abstract,
                            authors=authors,
                            doi=doi,
                            year=year,
                            url=landing_url,
                            pdf_url=pdf_url,
                            is_open_access=bool(is_oa or pdf_url),
                            sources=["openalex"],
                            venue=venue,
                            citation_count=item.get("cited_by_count", 0)
                        ))
                else:
                    logger.warning(f"OpenAlex returned HTTP {res.status_code}: {res.text[:100]}")
        except Exception as e:
            logger.warning(f"OpenAlex API search failed: {e}")

        return papers

    async def search_arxiv(
        self,
        query: str,
        limit: int = 10,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        author: Optional[str] = None
    ) -> List[DiscoveredPaper]:
        """Queries arXiv API using Atom XML feed."""
        papers: List[DiscoveredPaper] = []
        url = "https://export.arxiv.org/api/query"

        # Format search query: all:query
        clean_q = re.sub(r'["\']', '', query).strip()
        search_terms = f"all:{clean_q}"
        if author:
            search_terms += f" AND au:{author.strip()}"

        params = {
            "search_query": search_terms,
            "start": 0,
            "max_results": min(limit, 50),
            "sortBy": "relevance",
            "sortOrder": "descending"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    xml_content = res.text
                    root = ET.fromstring(xml_content)
                    ns = {
                        "atom": "http://www.w3.org/2005/Atom",
                        "arxiv": "http://arxiv.org/schemas/atom"
                    }

                    for entry in root.findall("atom:entry", ns):
                        raw_title = entry.findtext("atom:title", default="", namespaces=ns)
                        title = " ".join(raw_title.split())
                        if not title:
                            continue

                        raw_summary = entry.findtext("atom:summary", default="", namespaces=ns)
                        abstract = " ".join(raw_summary.split())

                        published = entry.findtext("atom:published", default="", namespaces=ns)
                        year = int(published[:4]) if len(published) >= 4 and published[:4].isdigit() else None

                        # Filter by year if specified
                        if year_start and year and year < year_start:
                            continue
                        if year_end and year and year > year_end:
                            continue

                        authors = [
                            a.findtext("atom:name", default="", namespaces=ns).strip()
                            for a in entry.findall("atom:author", ns)
                            if a.findtext("atom:name", default="", namespaces=ns).strip()
                        ]

                        doi = normalize_doi(entry.findtext("arxiv:doi", default=None, namespaces=ns))
                        landing_url = entry.findtext("atom:id", default="", namespaces=ns).strip()

                        # Construct PDF URL from arXiv ID
                        # e.g., http://arxiv.org/abs/2301.00001v1 -> https://arxiv.org/pdf/2301.00001.pdf
                        pdf_url = None
                        for link in entry.findall("atom:link", ns):
                            if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                                pdf_url = link.attrib.get("href")
                                break

                        if not pdf_url and "arxiv.org/abs/" in landing_url:
                            arxiv_id = landing_url.split("arxiv.org/abs/")[-1].split("v")[0]
                            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

                        paper_id = doi or (landing_url.split("arxiv.org/abs/")[-1] if "arxiv.org/abs/" in landing_url else hashlib.md5(title.lower().encode("utf-8")).hexdigest()[:16])

                        papers.append(DiscoveredPaper(
                            id=paper_id,
                            title=title,
                            abstract=abstract,
                            authors=authors,
                            doi=doi,
                            year=year,
                            url=landing_url,
                            pdf_url=pdf_url,
                            is_open_access=True,  # arXiv is always open-access
                            sources=["arxiv"],
                            venue="arXiv",
                            citation_count=None
                        ))
                else:
                    logger.warning(f"arXiv API returned HTTP {res.status_code}")
        except Exception as e:
            logger.warning(f"arXiv API search failed: {e}")

        return papers

    async def search_semanticscholar(
        self,
        query: str,
        limit: int = 10,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        author: Optional[str] = None
    ) -> List[DiscoveredPaper]:
        """Queries Semantic Scholar API."""
        papers: List[DiscoveredPaper] = []
        url = "https://api.semanticscholar.org/graph/v1/paper/search"

        headers = dict(self.default_headers)
        if settings.SEMANTIC_SCHOLAR_API_KEY:
            headers["x-api-key"] = settings.SEMANTIC_SCHOLAR_API_KEY

        params: Dict[str, Any] = {
            "query": query,
            "limit": min(limit, 50),
            "fields": "paperId,title,abstract,authors,year,externalIds,url,openAccessPdf,isOpenAccess,citationCount,venue"
        }

        # Year filter for S2
        if year_start and year_end:
            params["year"] = f"{year_start}-{year_end}"
        elif year_start:
            params["year"] = f"{year_start}-"
        elif year_end:
            params["year"] = f"-{year_end}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    for item in data.get("data", []):
                        title = (item.get("title") or "").strip()
                        if not title:
                            continue

                        ext_ids = item.get("externalIds", {}) or {}
                        doi = normalize_doi(ext_ids.get("DOI"))
                        abstract = item.get("abstract")
                        year = item.get("year")

                        authors = [
                            a.get("name").strip()
                            for a in item.get("authors", [])
                            if a.get("name")
                        ]

                        oa_pdf = item.get("openAccessPdf", {}) or {}
                        pdf_url = oa_pdf.get("url") if isinstance(oa_pdf, dict) else None
                        is_oa = item.get("isOpenAccess", False) or bool(pdf_url)
                        landing_url = item.get("url")
                        venue = item.get("venue")

                        paper_id = doi or item.get("paperId") or hashlib.md5(title.lower().encode("utf-8")).hexdigest()[:16]

                        papers.append(DiscoveredPaper(
                            id=paper_id,
                            title=title,
                            abstract=abstract,
                            authors=authors,
                            doi=doi,
                            year=year,
                            url=landing_url,
                            pdf_url=pdf_url,
                            is_open_access=bool(is_oa),
                            sources=["semanticscholar"],
                            venue=venue,
                            citation_count=item.get("citationCount")
                        ))
                elif res.status_code == 429:
                    logger.info("Semantic Scholar API rate-limited (HTTP 429). Gracefully continuing with other sources.")
                else:
                    logger.warning(f"Semantic Scholar API HTTP {res.status_code}: {res.text[:100]}")
        except Exception as e:
            logger.warning(f"Semantic Scholar API search failed: {e}")

        return papers

    def deduplicate_papers(self, papers: List[DiscoveredPaper]) -> List[DiscoveredPaper]:
        """
        Deduplicates papers across OpenAlex, arXiv, and Semantic Scholar
        by matching normalized DOI, arXiv URL, or normalized title slug.
        Merges metadata to preserve the highest quality abstract, PDF link, and sources.
        """
        doi_map: Dict[str, DiscoveredPaper] = {}
        title_map: Dict[str, DiscoveredPaper] = {}
        unique_papers: List[DiscoveredPaper] = []

        for p in papers:
            norm_t = normalize_title(p.title)
            norm_d = normalize_doi(p.doi)

            existing = None
            if norm_d and norm_d in doi_map:
                existing = doi_map[norm_d]
            elif norm_t and norm_t in title_map:
                existing = title_map[norm_t]

            if existing:
                # Merge sources
                for s in p.sources:
                    if s not in existing.sources:
                        existing.sources.append(s)

                # Prefer non-empty or longer abstract
                if not existing.abstract and p.abstract:
                    existing.abstract = p.abstract
                elif existing.abstract and p.abstract and len(p.abstract) > len(existing.abstract):
                    existing.abstract = p.abstract

                # Prefer existing or incoming DOI
                if not existing.doi and p.doi:
                    existing.doi = p.doi

                # Prefer incoming PDF URL if existing lacks one
                if not existing.pdf_url and p.pdf_url:
                    existing.pdf_url = p.pdf_url
                if p.is_open_access:
                    existing.is_open_access = True

                # Prefer non-empty year
                if not existing.year and p.year:
                    existing.year = p.year

                # Prefer non-empty venue
                if not existing.venue and p.venue:
                    existing.venue = p.venue

                # Keep higher citation count
                if p.citation_count is not None:
                    if existing.citation_count is None or p.citation_count > existing.citation_count:
                        existing.citation_count = p.citation_count
            else:
                unique_papers.append(p)
                if norm_d:
                    doi_map[norm_d] = p
                if norm_t:
                    title_map[norm_t] = p

        return unique_papers

    def rank_papers(self, papers: List[DiscoveredPaper], query: str, sort_by: str = "relevance") -> List[DiscoveredPaper]:
        """
        Ranks papers by computing a multi-factor relevance score:
        - Query term matches in title (high weight)
        - Query term matches in abstract
        - Multi-source appearance boost
        - Recency boost
        - Citation count boost
        """
        query_words = [w.lower() for w in re.findall(r"\b[A-Za-z0-9_]{3,}\b", query)]
        clean_q_lower = query.lower().strip()
        current_year = 2026

        for p in papers:
            score = 0.2  # Base score
            title_lower = p.title.lower()
            abstract_lower = (p.abstract or "").lower()

            # Exact title phrase bonus
            if clean_q_lower in title_lower:
                score += 0.35

            # Word overlaps in title
            title_hits = sum(1 for w in query_words if w in title_lower)
            if query_words:
                score += 0.25 * (title_hits / len(query_words))

            # Word overlaps in abstract
            if abstract_lower and query_words:
                abs_hits = sum(1 for w in query_words if w in abstract_lower)
                score += 0.15 * (abs_hits / len(query_words))

            # Multi-source boost (verified across multiple databases)
            if len(p.sources) > 1:
                score += 0.15

            # Open-access availability boost
            if p.is_open_access or p.pdf_url:
                score += 0.05

            # Recency bonus (last 4 years)
            if p.year and p.year >= (current_year - 4):
                score += 0.05

            p.relevance_score = round(min(1.0, score), 4)

        if sort_by == "year_desc":
            papers.sort(key=lambda x: (x.year or 0, x.relevance_score), reverse=True)
        elif sort_by == "year_asc":
            papers.sort(key=lambda x: (x.year or 9999, -x.relevance_score))
        elif sort_by == "citations_desc":
            papers.sort(key=lambda x: (x.citation_count or 0, x.relevance_score), reverse=True)
        else:  # relevance
            papers.sort(key=lambda x: x.relevance_score, reverse=True)

        return papers

    def filter_papers(
        self,
        papers: List[DiscoveredPaper],
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        author: Optional[str] = None,
        open_access_only: bool = False
    ) -> List[DiscoveredPaper]:
        """Applies local post-filtering criteria."""
        filtered = []
        author_lower = author.lower().strip() if author else None

        for p in papers:
            if year_start and p.year and p.year < year_start:
                continue
            if year_end and p.year and p.year > year_end:
                continue
            if open_access_only and not p.is_open_access and not p.pdf_url:
                continue
            if author_lower:
                author_match = any(author_lower in a.lower() for a in p.authors)
                if not author_match:
                    continue
            filtered.append(p)

        return filtered

    async def execute_discovery_search(self, req: DiscoverySearchRequest) -> Tuple[List[DiscoveredPaper], Dict[str, str]]:
        """
        Coordinates cross-source academic search across OpenAlex, arXiv, and Semantic Scholar.
        Fails gracefully on individual source failures or network issues.
        """
        full_query = req.topic.strip()
        if req.keywords:
            full_query += " " + " ".join(k.strip() for k in req.keywords if k.strip())

        sources_to_query = [s.lower() for s in req.sources] if req.sources is not None else ["openalex", "arxiv", "semanticscholar"]
        source_statuses: Dict[str, str] = {}
        all_papers: List[DiscoveredPaper] = []

        # 1. OpenAlex
        if "openalex" in sources_to_query:
            try:
                oa_papers = await self.search_openalex(
                    query=full_query,
                    limit=req.limit_per_source,
                    year_start=req.year_start,
                    year_end=req.year_end,
                    author=req.author,
                    open_access_only=req.open_access_only
                )
                all_papers.extend(oa_papers)
                source_statuses["openalex"] = f"ok ({len(oa_papers)} found)"
            except Exception as e:
                source_statuses["openalex"] = f"error: {str(e)}"

        # 2. arXiv
        if "arxiv" in sources_to_query:
            try:
                arxiv_papers = await self.search_arxiv(
                    query=full_query,
                    limit=req.limit_per_source,
                    year_start=req.year_start,
                    year_end=req.year_end,
                    author=req.author
                )
                all_papers.extend(arxiv_papers)
                source_statuses["arxiv"] = f"ok ({len(arxiv_papers)} found)"
            except Exception as e:
                source_statuses["arxiv"] = f"error: {str(e)}"

        # 3. Semantic Scholar
        if "semanticscholar" in sources_to_query:
            try:
                s2_papers = await self.search_semanticscholar(
                    query=full_query,
                    limit=req.limit_per_source,
                    year_start=req.year_start,
                    year_end=req.year_end,
                    author=req.author
                )
                all_papers.extend(s2_papers)
                source_statuses["semanticscholar"] = f"ok ({len(s2_papers)} found)" if s2_papers else "rate_limited or empty"
            except Exception as e:
                source_statuses["semanticscholar"] = f"error: {str(e)}"

        # Deduplicate, Filter & Rank
        deduped = self.deduplicate_papers(all_papers)
        filtered = self.filter_papers(
            papers=deduped,
            year_start=req.year_start,
            year_end=req.year_end,
            author=req.author,
            open_access_only=req.open_access_only
        )
        ranked = self.rank_papers(filtered, query=full_query, sort_by=req.sort_by)

        return ranked, source_statuses

    async def download_paper_pdf(self, pdf_url: str, filename_hint: Optional[str] = None) -> Tuple[Optional[Path], int]:
        """
        Downloads open-access PDF directly from publisher or repository.
        Validates HTTP 200 and %PDF- magic bytes.
        """
        doc_id = str(uuid.uuid4())
        dest_filename = f"{doc_id}.pdf"
        target_path = self.pdf_dir / dest_filename

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=self.default_headers) as client:
                res = await client.get(pdf_url)
                if res.status_code == 200:
                    content = res.content
                    # Validate PDF magic bytes
                    if content.startswith(b"%PDF-") or b"%PDF-" in content[:1024]:
                        with open(target_path, "wb") as f:
                            f.write(content)
                        logger.info(f"Successfully downloaded PDF ({len(content)} bytes) to {target_path}")
                        return target_path, len(content)
                    else:
                        logger.warning(f"Downloaded content from {pdf_url} is not a valid PDF.")
                        return None, 0
                else:
                    logger.warning(f"Failed to download PDF from {pdf_url}: HTTP {res.status_code}")
                    return None, 0
        except Exception as e:
            logger.warning(f"Error downloading PDF from {pdf_url}: {e}")
            return None, 0

    async def add_paper_to_project(
        self,
        db: Session,
        project_id: str,
        paper: DiscoveredPaper,
        download_pdf: bool = True,
        process_document: bool = True
    ) -> Tuple[ResearchPaper, bool, str]:
        """
        Adds a discovered paper to an existing research project.
        - If download_pdf is True and pdf_url is available: downloads PDF and processes sections/chunks.
        - If download fails or no PDF is available: catalogs the paper metadata with processed_status='metadata_only',
          allowing the user to manually attach a PDF later.
        """
        # 1. Verify project exists
        project = db.query(ResearchProject).filter(ResearchProject.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Research project '{project_id}' not found."
            )

        # 2. Check for duplicate DOI in the database
        if paper.doi:
            existing = db.query(ResearchPaper).filter(ResearchPaper.doi == paper.doi).first()
            if existing:
                if existing.project_id != project_id:
                    # Link existing paper to this project or notify
                    return existing, bool(existing.file_path), f"Paper '{existing.title}' already exists in library (ID: {existing.id})."
                return existing, bool(existing.file_path), f"Paper already in this project (ID: {existing.id})."

        doc_id = str(uuid.uuid4())
        pdf_path = None
        file_size = 0
        pdf_downloaded = False

        # 3. Attempt PDF download if open access / link available
        if download_pdf and paper.pdf_url:
            pdf_path, file_size = await self.download_paper_pdf(paper.pdf_url, filename_hint=paper.title)
            pdf_downloaded = (pdf_path is not None)

        # 4. If PDF was downloaded and processing is enabled, run full document extraction pipeline
        if pdf_downloaded and pdf_path and process_document:
            try:
                processed_paper = await document_processor.process_pdf_document(
                    db=db,
                    doc_id=doc_id,
                    file_path=pdf_path,
                    original_filename=f"{paper.title[:50]}.pdf",
                    file_size=file_size,
                    project_id=project_id,
                    force_llm_assist=False
                )
                # Ensure DOI and venue are preserved
                if paper.doi and not processed_paper.doi:
                    processed_paper.doi = paper.doi
                if paper.venue and not processed_paper.journal_or_conference:
                    processed_paper.journal_or_conference = paper.venue
                db.commit()
                db.refresh(processed_paper)
                return processed_paper, True, f"Paper '{paper.title}' downloaded and fully indexed in project."
            except Exception as e:
                logger.error(f"Failed to process downloaded PDF {pdf_path}: {e}")
                # Fall back to metadata-only record
                pass

        # 5. Create paper metadata record in SQLite (with or without downloaded PDF)
        paper_record = ResearchPaper(
            id=doc_id,
            project_id=project_id,
            title=paper.title,
            doi=paper.doi,
            publication_year=paper.year,
            journal_or_conference=paper.venue,
            abstract=paper.abstract,
            filename=pdf_path.name if pdf_path else None,
            file_path=str(pdf_path) if pdf_path else None,
            file_size_bytes=file_size if file_size else None,
            processed_status="pending" if pdf_downloaded else "metadata_only",
            error_message=None
        )
        db.add(paper_record)
        db.flush()

        # Link authors
        for author_name in paper.authors:
            clean_name = author_name.strip()
            if clean_name:
                author_obj = db.query(Author).filter(Author.name == clean_name).first()
                if not author_obj:
                    author_obj = Author(name=clean_name)
                    db.add(author_obj)
                    db.flush()
                if author_obj not in paper_record.authors:
                    paper_record.authors.append(author_obj)

        db.commit()
        db.refresh(paper_record)

        msg = f"Paper metadata added to project '{project.title}'."
        if pdf_downloaded:
            msg += " PDF downloaded (pending processing)."
        else:
            msg += " No open-access PDF was available; you can upload a PDF manually."

        return paper_record, pdf_downloaded, msg

    async def attach_manual_pdf(
        self,
        db: Session,
        paper_id: str,
        file: UploadFile
    ) -> ResearchPaper:
        """
        Allows manual upload of a PDF for a paper that was previously saved as metadata-only.
        Extracts sections, runs section-aware chunking, and indexes into ChromaDB.
        """
        paper = db.query(ResearchPaper).filter(ResearchPaper.id == paper_id).first()
        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Paper with ID '{paper_id}' not found."
            )

        # Validate and save uploaded PDF
        _, safe_path, file_size = await document_processor.save_uploaded_file(file)

        # Process document
        processed_paper = await document_processor.process_pdf_document(
            db=db,
            doc_id=paper.id,
            file_path=safe_path,
            original_filename=file.filename,
            file_size=file_size,
            project_id=paper.project_id
        )
        return processed_paper

discovery_agent = ResearchDiscoveryAgent()

