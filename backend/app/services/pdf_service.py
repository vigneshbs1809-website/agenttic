import pymupdf  # PyMuPDF
import re
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)

# The 10 canonical academic sections required
CANONICAL_SECTIONS = [
    "Abstract",
    "Introduction",
    "Related Work",
    "Methodology",
    "Experiments",
    "Results",
    "Discussion",
    "Limitations",
    "Conclusion",
    "References"
]

# Section header regex mappings
SECTION_PATTERNS = {
    "Abstract": re.compile(r"^(?:[0-9IVX]+\.?\s*)?(?:abstract|summary)\b", re.IGNORECASE),
    "Introduction": re.compile(r"^(?:[0-9IVX]+\.?\s*)?(?:1\.?\s*)?(?:introduction|motivation|background\s+and\s+introduction)\b", re.IGNORECASE),
    "Related Work": re.compile(r"^(?:[0-9IVX]+\.?\s*)?(?:related\s+work|literature\s+review|prior\s+art|background\s+and\s+related\s+work)\b", re.IGNORECASE),
    "Methodology": re.compile(r"^(?:[0-9IVX]+\.?\s*)?(?:methodology|method|methods|proposed\s+approach|system\s+model|architecture|model\s+design|materials\s+and\s+methods)\b", re.IGNORECASE),
    "Experiments": re.compile(r"^(?:[0-9IVX]+\.?\s*)?(?:experiments|experimental\s+setup|evaluation|experimental\s+design|empirical\s+study|benchmarks)\b", re.IGNORECASE),
    "Results": re.compile(r"^(?:[0-9IVX]+\.?\s*)?(?:results|experimental\s+results|findings|empirical\s+results|performance\s+analysis)\b", re.IGNORECASE),
    "Discussion": re.compile(r"^(?:[0-9IVX]+\.?\s*)?(?:discussion|results\s+and\s+discussion|comparative\s+analysis|implications)\b", re.IGNORECASE),
    "Limitations": re.compile(r"^(?:[0-9IVX]+\.?\s*)?(?:limitations|threats\s+to\s+validity|failure\s+modes|risks\s+and\s+limitations)\b", re.IGNORECASE),
    "Conclusion": re.compile(r"^(?:[0-9IVX]+\.?\s*)?(?:conclusion|conclusions|concluding\s+remarks|summary\s+and\s+conclusion|conclusions\s+and\s+future\s+work)\b", re.IGNORECASE),
    "References": re.compile(r"^(?:[0-9IVX]+\.?\s*)?(?:references|bibliography|works\s+cited)\b", re.IGNORECASE),
}

class PDFService:
    @staticmethod
    def validate_pdf(file_bytes: bytes) -> bool:
        """Validates that bytes conform to the PDF file specification."""
        if not file_bytes or len(file_bytes) < 10:
            return False
        # Check standard PDF magic header
        if not file_bytes.startswith(b"%PDF-"):
            return False
        try:
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
            is_valid = len(doc) > 0
            doc.close()
            return is_valid
        except Exception as e:
            logger.warning(f"PDF validation failed: {e}")
            return False

    @staticmethod
    def extract_pages(doc: pymupdf.Document) -> List[Dict[str, Any]]:
        """
        Extracts text page-by-page preserving original 1-indexed PDF page numbers.
        """
        pages = []
        for page_idx in range(len(doc)):
            page_num = page_idx + 1
            page = doc[page_idx]
            page_text = page.get_text("text").strip()
            
            words = page_text.split()
            token_est = int(len(words) * 1.3)

            pages.append({
                "page_number": page_num,
                "text": page_text,
                "character_count": len(page_text),
                "token_count": token_est
            })
        return pages

    @staticmethod
    def extract_rule_based_metadata(doc: pymupdf.Document, filename: str) -> Dict[str, Any]:
        """
        Rule-based extraction of title, authors, abstract, and publication year.
        Uses visual font sizes and block ordering on the first two pages.
        """
        meta = doc.metadata or {}
        first_page = doc[0] if len(doc) > 0 else None
        
        # 1. Title Extraction
        title = meta.get("title", "").strip()
        # Clean generic metadata titles like "Untitled" or file paths
        if not title or len(title) < 5 or title.lower().endswith(".pdf") or "untitled" in title.lower():
            title = None

        if not title and first_page:
            # Inspect first page text blocks to find largest font size block (standard paper title)
            try:
                blocks = first_page.get_text("dict")["blocks"]
                max_size = 0.0
                best_text = ""
                for b in blocks:
                    if "lines" in b:
                        for line in b["lines"]:
                            for span in line["spans"]:
                                text = span["text"].strip()
                                size = span["size"]
                                if size > max_size and len(text) > 5 and not text.isdigit():
                                    max_size = size
                                    best_text = text
                                elif abs(size - max_size) < 0.5 and len(text) > 0:
                                    best_text += " " + text
                if best_text and len(best_text) >= 5:
                    lines = [l.strip() for l in best_text.split("\n") if l.strip()]
                    title = lines[0] if lines else re.sub(r"\s+", " ", best_text).strip()
            except Exception:
                pass

        if not title:
            # Fallback to sanitized filename
            title = Path(filename).stem.replace("_", " ").replace("-", " ").title()

        # 2. Authors Extraction
        authors = []
        author_meta = meta.get("author", "").strip()
        if author_meta:
            split_authors = [a.strip() for a in re.split(r"[,;]", author_meta) if a.strip()]
            authors.extend(split_authors)

        if not authors and first_page:
            # Heuristic: search text lines between title and Abstract
            first_page_text = first_page.get_text("text")
            lines = [l.strip() for l in first_page_text.split("\n") if l.strip()]
            candidate_authors = []
            found_title = False
            for line in lines:
                if title and title[:20].lower() in line.lower():
                    found_title = True
                    continue
                if found_title:
                    if re.search(r"\b(abstract|summary|introduction)\b", line, re.IGNORECASE):
                        break
                    # Filter out university, department, or email lines
                    if not re.search(r"(@|university|department|institute|lab|college|school|ieee|acm)", line, re.IGNORECASE):
                        if len(line) < 100:
                            candidate_authors.extend([a.strip() for a in re.split(r"[,;]|and\s+", line) if len(a.strip()) > 2])
            if candidate_authors:
                authors = candidate_authors[:5]

        # 3. Abstract Extraction
        abstract = ""
        full_text_early = ""
        for i in range(min(2, len(doc))):
            full_text_early += doc[i].get_text("text") + "\n"

        abs_match = re.search(
            r"(?:abstract|summary)\s*[:\-\n]\s*(.*?)(?=\n\s*(?:[0-9IVX]+\.?\s*)?(?:1\.?\s*)?(?:introduction|keywords|index\s+terms))",
            full_text_early,
            re.IGNORECASE | re.DOTALL
        )
        if abs_match:
            abstract = re.sub(r"\s+", " ", abs_match.group(1)).strip()
        elif "abstract" in full_text_early.lower():
            # Slice around 'abstract' keyword
            idx = full_text_early.lower().find("abstract")
            abstract = re.sub(r"\s+", " ", full_text_early[idx+8:idx+1200]).strip()

        # 4. Publication Year Extraction
        year = None
        # Try metadata creation date
        creation_date = meta.get("creationDate", "")
        if creation_date and len(creation_date) >= 6:
            year_match = re.search(r"(?:19|20)\d{2}", creation_date)
            if year_match:
                year = int(year_match.group(0))

        if not year and first_page:
            # Scan header/footer on first page
            first_text = first_page.get_text("text")
            year_candidates = re.findall(r"\b(20[0-2]\d|199\d)\b", first_text)
            if year_candidates:
                year = int(year_candidates[0])

        return {
            "title": title,
            "authors": authors,
            "abstract": abstract[:2000] if abstract else None,
            "publication_year": year,
            "total_pages": len(doc)
        }

    @staticmethod
    def identify_academic_sections(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detects transitions across the 10 canonical academic sections:
        Abstract, Introduction, Related Work, Methodology, Experiments,
        Results, Discussion, Limitations, Conclusion, References.
        """
        sections = []
        current_canonical = "Introduction"
        current_heading = "Introduction"
        current_page = 1
        buffer_lines = []

        def match_section_header(line: str) -> Optional[Tuple[str, str]]:
            stripped = line.strip()
            if not stripped or len(stripped) > 80:
                return None
            for canonical, pattern in SECTION_PATTERNS.items():
                if pattern.match(stripped):
                    return canonical, stripped
            return None

        section_idx = 0

        for page_data in pages:
            page_num = page_data["page_number"]
            page_text = page_data["text"]
            lines = page_text.split("\n")

            for line in lines:
                header_match = match_section_header(line)
                if header_match:
                    new_canonical, new_heading = header_match

                    # Flush previous section if it has content
                    if buffer_lines:
                        content_text = "\n".join(buffer_lines).strip()
                        if content_text:
                            tokens = int(len(content_text.split()) * 1.3)
                            sections.append({
                                "id": str(uuid.uuid4()),
                                "section_index": section_idx,
                                "section_title": current_heading,
                                "section_type": current_canonical.lower().replace(" ", "_"),
                                "page_number": current_page,
                                "content": content_text,
                                "token_count": tokens
                            })
                            section_idx += 1
                        buffer_lines = []

                    current_canonical = new_canonical
                    current_heading = new_heading
                    current_page = page_num
                else:
                    if line.strip():
                        buffer_lines.append(line)

        # Flush final section
        if buffer_lines:
            content_text = "\n".join(buffer_lines).strip()
            if content_text:
                tokens = int(len(content_text.split()) * 1.3)
                sections.append({
                    "id": str(uuid.uuid4()),
                    "section_index": section_idx,
                    "section_title": current_heading,
                    "section_type": current_canonical.lower().replace(" ", "_"),
                    "page_number": current_page,
                    "content": content_text,
                    "token_count": tokens
                })

        # If no explicit sections were detected, fallback to page-based chunks
        if not sections:
            for idx, p in enumerate(pages):
                sections.append({
                    "id": str(uuid.uuid4()),
                    "section_index": idx,
                    "section_title": f"Page {p['page_number']}",
                    "section_type": "content",
                    "page_number": p["page_number"],
                    "content": p["text"],
                    "token_count": p["token_count"]
                })

        return sections

pdf_service = PDFService()
