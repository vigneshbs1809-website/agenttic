import uuid
import re
from typing import List, Dict, Any, Optional

class SectionAwareChunker:
    def __init__(self, target_chunk_tokens: int = 350, chunk_overlap_tokens: int = 50):
        self.target_chunk_tokens = target_chunk_tokens
        self.chunk_overlap_tokens = chunk_overlap_tokens
        # Token estimation factor (~1.3 words per token for scientific text)
        self.target_words = int(target_chunk_tokens / 1.3)
        self.overlap_words = int(chunk_overlap_tokens / 1.3)

    def chunk_paper_sections(
        self,
        paper_id: str,
        paper_title: str,
        sections: List[Dict[str, Any]],
        project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Splits extracted academic sections into section-aware and page-aware chunks.
        Chunks NEVER bleed across distinct section boundaries (e.g. Abstract vs Methodology).
        """
        all_chunks = []
        global_chunk_idx = 0

        for sec in sections:
            sec_title = sec.get("section_title", "General")
            sec_type = sec.get("section_type", "content")
            page_num = sec.get("page_number", 1)
            content = sec.get("content", "").strip()

            if not content:
                continue

            # Split section text into paragraphs/sentences
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            if not paragraphs:
                paragraphs = [content]

            words_in_section = content.split()
            total_sec_words = len(words_in_section)

            # If section fits within a single chunk, keep it intact
            if total_sec_words <= self.target_words:
                all_chunks.append({
                    "chunk_id": str(uuid.uuid4()),
                    "paper_id": paper_id,
                    "project_id": project_id or "default",
                    "paper_title": paper_title,
                    "chunk_index": global_chunk_idx,
                    "section_title": sec_title,
                    "section_type": sec_type,
                    "page_number": page_num,
                    "content": content,
                    "token_count": int(total_sec_words * 1.3)
                })
                global_chunk_idx += 1
                continue

            # If section exceeds target size, perform sliding-window chunking strictly within this section
            words = words_in_section
            start_idx = 0

            while start_idx < len(words):
                end_idx = min(start_idx + self.target_words, len(words))
                chunk_slice = words[start_idx:end_idx]
                chunk_text = " ".join(chunk_slice)

                all_chunks.append({
                    "chunk_id": str(uuid.uuid4()),
                    "paper_id": paper_id,
                    "project_id": project_id or "default",
                    "paper_title": paper_title,
                    "chunk_index": global_chunk_idx,
                    "section_title": sec_title,
                    "section_type": sec_type,
                    "page_number": page_num,
                    "content": chunk_text,
                    "token_count": int(len(chunk_slice) * 1.3)
                })
                global_chunk_idx += 1

                if end_idx >= len(words):
                    break

                # Advance with overlap
                start_idx += (self.target_words - self.overlap_words)

        return all_chunks

chunker = SectionAwareChunker(target_chunk_tokens=350, chunk_overlap_tokens=50)

