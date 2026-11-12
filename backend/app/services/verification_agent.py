import re
import json
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from sqlalchemy.orm import Session

from backend.app.models.entities import (
    ResearchPaper,
    PaperSection,
    ResearchClaim,
    ResearchGap,
    GapEvidence,
    VerificationResult
)
from backend.app.models.verification_schemas import (
    VerificationStatus,
    VerifyClaimRequest,
    VerificationResultResponse,
    BatchVerifyClaimsResponse
)
from backend.app.services.retrieval_agent import RetrievalAgent

logger = logging.getLogger(__name__)

class EvidenceVerificationAgent:
    """
    Independent Evidence Verification Agent.
    Validates claims and gaps directly against original PDF source passages.
    Guarantees:
    - Independent retrieval and inspection of original PDF evidence.
    - Does NOT simply ask the generating LLM whether its own claim is correct.
    - Unsupported claims (Contradicted, Insufficient Evidence) NEVER appear as verified findings.
    """

    def __init__(self):
        self.retriever = RetrievalAgent(default_top_k=4)

    # ----------------------------------------------------------------------
    # 1. Independent Passage Retrieval
    # ----------------------------------------------------------------------
    async def retrieve_source_evidence(
        self,
        claim_text: str,
        paper: ResearchPaper,
        db: Session,
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Retrieves original source passages from hybrid RAG vector index and
        SQLite paper sections for the specific target paper.
        """
        candidate_passages: List[Dict[str, Any]] = []
        seen_texts = set()

        # 1. Hybrid RAG retrieval filtered by paper_id
        try:
            rag_results = await self.retriever.search_hybrid(
                query=claim_text,
                paper_id=paper.id,
                top_k=top_k
            )
            for res in rag_results:
                text_clean = res.get("original_text", "").strip()
                if text_clean and text_clean not in seen_texts:
                    seen_texts.add(text_clean)
                    candidate_passages.append({
                        "text": text_clean,
                        "page_number": res.get("page_number") or 1,
                        "section_title": res.get("section_name") or "General",
                        "score": res.get("retrieval_score", 0.8),
                        "source": "hybrid_rag"
                    })
        except Exception as e:
            logger.warning(f"RAG retrieval failed for paper {paper.id}: {e}")

        # 2. Direct lexical scanning of SQLite PaperSections
        sections = db.query(PaperSection).filter(PaperSection.paper_id == paper.id).all()
        claim_words = [w.lower() for w in re.findall(r"\b[a-zA-Z0-9_\-\.%]+\b", claim_text) if len(w) > 2 and w.lower() not in ["the", "and", "for", "with", "that", "this", "from", "on", "in"]]

        for sec in sections:
            content = sec.content or ""
            content_lower = content.lower()

            hits = sum(1 for w in claim_words if w in content_lower)
            if hits >= 2:
                sentences = re.split(r"(?<!\d)\.(?!\d)\s*", content)
                for sent in sentences:
                    sent_strip = sent.strip()
                    if len(sent_strip) > 20:
                        sent_hits = sum(1 for w in claim_words if w in sent_strip.lower())
                        if sent_hits >= 2 and sent_strip not in seen_texts:
                            seen_texts.add(sent_strip)
                            candidate_passages.append({
                                "text": sent_strip,
                                "page_number": sec.page_number or 1,
                                "section_title": sec.section_title or sec.section_type or "Section",
                                "score": 0.85,
                                "source": "section_lexical"
                            })

        return candidate_passages

    # ----------------------------------------------------------------------
    # 2. Metric Extraction Helper
    # ----------------------------------------------------------------------
    def extract_metrics(self, text: str) -> List[Tuple[str, Optional[str]]]:
        """Extracts quantitative metric values (e.g. ('89.2', '%'), ('28.4', '%'), ('3.4', 'x'))."""
        matches = re.findall(r"\b(\d+(?:\.\d+)?)\s*(%|x|ms|s|seconds|fps|times)?(?:\b|\s|$)", text, re.IGNORECASE)
        results = []
        for m in matches:
            val = m[0]
            unit = m[1].lower() if m[1] else None
            # Ignore standalone years (e.g. 2024, 2025)
            if not unit and len(val) == 4 and val.startswith("20"):
                continue
            results.append((val, unit))
        return results

    # ----------------------------------------------------------------------
    # 3. Independent Claim Validation Engine
    # ----------------------------------------------------------------------
    def evaluate_claim_against_evidence(
        self,
        claim_text: str,
        passages: List[Dict[str, Any]],
        paper: ResearchPaper
    ) -> Tuple[str, Optional[str], Optional[int], Optional[str], str, float]:
        """
        Compares claim directly against source passages.
        Determines: Supported, Partially Supported, Contradicted, or Insufficient Evidence.
        """
        if not passages:
            return (
                VerificationStatus.INSUFFICIENT_EVIDENCE.value,
                None,
                None,
                None,
                f"No source passages in '{paper.title}' contain evidence relating to this claim.",
                0.0
            )

        claim_clean = claim_text.strip()
        claim_lower = claim_clean.lower()
        claim_metrics = self.extract_metrics(claim_clean)

        best_passage = passages[0]
        best_evidence_text = best_passage["text"]
        best_page = best_passage["page_number"]
        best_section = best_passage["section_title"]
        best_score = best_passage.get("score", 0.5)

        # ------------------------------------------------------------------
        # 1. Check for EXACT METRIC DIRECT SUPPORT first
        # ------------------------------------------------------------------
        if claim_metrics:
            claim_vals = [m[0] for m in claim_metrics]
            for pas in passages:
                pas_text = pas["text"]
                pas_metrics = self.extract_metrics(pas_text)
                pas_vals = [m[0] for m in pas_metrics]
                if all(v in pas_vals for v in claim_vals):
                    return (
                        VerificationStatus.SUPPORTED.value,
                        pas_text,
                        pas["page_number"],
                        pas["section_title"],
                        (
                            f"Direct support verified: The source text at Page {pas['page_number']} explicitly corroborates "
                            f"the asserted metrics ({', '.join(claim_vals)}): \"{pas_text}\"."
                        ),
                        0.95
                    )

        # ------------------------------------------------------------------
        # 2. Check for EXPLICIT CONTRADICTIONS across passages
        # ------------------------------------------------------------------
        for pas in passages:
            pas_text = pas["text"]
            pas_lower = pas_text.lower()
            pas_metrics = self.extract_metrics(pas_text)

            # A. Metric Discrepancy Contradiction:
            # Same unit and same metric context, but different number
            if claim_metrics and pas_metrics:
                for c_val, c_unit in claim_metrics:
                    # Find passage metrics with matching unit (e.g. '%')
                    matching_unit_pas_metrics = [p_val for p_val, p_unit in pas_metrics if p_unit == c_unit and c_unit is not None]
                    if matching_unit_pas_metrics and c_val not in matching_unit_pas_metrics:
                        # Check shared topic (success rate, accuracy, latency, etc. with academic synonyms)
                        perf_synonyms = {"success rate", "accuracy", "performance", "f1", "f1-score", "precision", "recall", "score", "map", "auc", "roc-auc"}
                        latency_synonyms = {"latency", "delay", "runtime", "execution time", "speedup", "reduction"}
                        throughput_synonyms = {"throughput", "fps", "bandwidth", "qps"}

                        claim_has_perf = any(t in claim_lower for t in perf_synonyms)
                        pas_has_perf = any(t in pas_lower for t in perf_synonyms)

                        claim_has_lat = any(t in claim_lower for t in latency_synonyms)
                        pas_has_lat = any(t in pas_lower for t in latency_synonyms)

                        claim_has_thr = any(t in claim_lower for t in throughput_synonyms)
                        pas_has_thr = any(t in pas_lower for t in throughput_synonyms)

                        shares_metric_topic = (
                            (claim_has_perf and pas_has_perf) or
                            (claim_has_lat and pas_has_lat) or
                            (claim_has_thr and pas_has_thr) or
                            any(k in claim_lower and k in pas_lower for k in ["collision", "loss", "error rate", "perplexity"])
                        )
                        if shares_metric_topic:
                            return (
                                VerificationStatus.CONTRADICTED.value,
                                pas_text,
                                pas["page_number"],
                                pas["section_title"],
                                (
                                    f"Contradiction identified: The claim asserts value ({c_val}{c_unit or ''}), "
                                    f"whereas the original source text at Page {pas['page_number']} explicitly documents "
                                    f"({', '.join(matching_unit_pas_metrics)}{c_unit or ''}). The asserted metric directly conflicts with the published literature: \"{pas_text}\"."
                                ),
                                0.95
                            )

            # B. Direction Inversion Contradiction
            # e.g. Claim asserts "increases latency" when paper documents "latency reduction"
            claim_has_inc_latency = bool(re.search(r"\b(?:(?:increases?|higher|elevated|growth in)\s+(?:the\s+)?latency|latency\s+(?:increase|growth|elevation))\b", claim_lower))
            claim_has_dec_latency = bool(re.search(r"\b(?:(?:reduces?|reduction|lower|decreases?)\s+(?:in\s+)?latency|latency\s+(?:reduction|decrease|drop))\b", claim_lower))
            pas_has_inc_latency = bool(re.search(r"\b(?:(?:increases?|higher|elevated|growth in)\s+(?:the\s+)?latency|latency\s+(?:increase|growth|elevation))\b", pas_lower))
            pas_has_dec_latency = bool(re.search(r"\b(?:(?:reduces?|reduction|lower|decreases?)\s+(?:in\s+)?latency|latency\s+(?:reduction|decrease|drop))\b", pas_lower))

            if claim_has_inc_latency and pas_has_dec_latency:
                return (
                    VerificationStatus.CONTRADICTED.value,
                    pas_text,
                    pas["page_number"],
                    pas["section_title"],
                    (
                        f"Contradiction identified: The claim asserts that the method increases latency, "
                        f"whereas the source text at Page {pas['page_number']} explicitly demonstrates a latency reduction: \"{pas_text}\"."
                    ),
                    0.95
                )

            if claim_has_dec_latency and pas_has_inc_latency:
                return (
                    VerificationStatus.CONTRADICTED.value,
                    pas_text,
                    pas["page_number"],
                    pas["section_title"],
                    (
                        f"Contradiction identified: The claim asserts a latency reduction, "
                        f"whereas the source text at Page {pas['page_number']} documents increased latency: \"{pas_text}\"."
                    ),
                    0.95
                )

            # Accuracy / Performance Direction Inversion
            claim_has_inc_perf = bool(re.search(r"\b(?:(?:increases?|higher|improves?|elevated|superior)\s+(?:the\s+)?(?:accuracy|performance|f1|success rate)|(?:accuracy|performance|f1|success rate)\s+(?:increase|improvement|gain))\b", claim_lower))
            claim_has_dec_perf = bool(re.search(r"\b(?:(?:decreases?|lower|degrades?|drops?|inferior|worse)\s+(?:the\s+)?(?:accuracy|performance|f1|success rate)|(?:accuracy|performance|f1|success rate)\s+(?:decrease|drop|degradation))\b", claim_lower))
            pas_has_inc_perf = bool(re.search(r"\b(?:(?:increases?|higher|improves?|elevated|superior)\s+(?:the\s+)?(?:accuracy|performance|f1|success rate)|(?:accuracy|performance|f1|success rate)\s+(?:increase|improvement|gain))\b", pas_lower))
            pas_has_dec_perf = bool(re.search(r"\b(?:(?:decreases?|lower|degrades?|drops?|inferior|worse)\s+(?:the\s+)?(?:accuracy|performance|f1|success rate)|(?:accuracy|performance|f1|success rate)\s+(?:decrease|drop|degradation))\b", pas_lower))

            if claim_has_dec_perf and pas_has_inc_perf:
                return (
                    VerificationStatus.CONTRADICTED.value,
                    pas_text,
                    pas["page_number"],
                    pas["section_title"],
                    (
                        f"Contradiction identified: The claim asserts degraded performance/accuracy, "
                        f"whereas the source text at Page {pas['page_number']} explicitly demonstrates performance improvement: \"{pas_text}\"."
                    ),
                    0.95
                )

            if claim_has_inc_perf and pas_has_dec_perf:
                return (
                    VerificationStatus.CONTRADICTED.value,
                    pas_text,
                    pas["page_number"],
                    pas["section_title"],
                    (
                        f"Contradiction identified: The claim asserts performance/accuracy improvement, "
                        f"whereas the source text at Page {pas['page_number']} documents degraded performance: \"{pas_text}\"."
                    ),
                    0.95
                )

        # ------------------------------------------------------------------
        # 3. Check for Non-Metric DIRECT SUPPORT (only if no contradiction)
        # ------------------------------------------------------------------
        if not claim_metrics:
            for pas in passages:
                pas_text = pas["text"]
                pas_lower = pas_text.lower()
                claim_words = set(re.findall(r"\b[a-zA-Z0-9_\-\.%]+\b", claim_lower)) - {"the", "and", "for", "with", "that", "this", "from", "our", "are", "on", "in"}
                pas_words = set(re.findall(r"\b[a-zA-Z0-9_\-\.%]+\b", pas_lower))
                overlap = len(claim_words.intersection(pas_words)) / max(1, len(claim_words))

                if overlap >= 0.75:
                    return (
                        VerificationStatus.SUPPORTED.value,
                        pas_text,
                        pas["page_number"],
                        pas["section_title"],
                        f"Direct support verified: Source text at Page {pas['page_number']} directly validates the claim: \"{pas_text}\".",
                        round(overlap, 2)
                    )

        # ------------------------------------------------------------------
        # 3. Check for PARTIAL SUPPORT
        # ------------------------------------------------------------------
        for pas in passages:
            pas_text = pas["text"]
            pas_lower = pas_text.lower()
            pas_metrics = self.extract_metrics(pas_text)

            # If claim has multiple metrics and at least one is substantiated
            if claim_metrics and pas_metrics:
                claim_vals = [m[0] for m in claim_metrics]
                pas_vals = [m[0] for m in pas_metrics]
                shared = [v for v in claim_vals if v in pas_vals]
                if shared:
                    return (
                        VerificationStatus.PARTIALLY_SUPPORTED.value,
                        pas_text,
                        pas["page_number"],
                        pas["section_title"],
                        (
                            f"Partial support detected: Source text at Page {pas['page_number']} substantiates metric ({', '.join(shared)}), "
                            f"but other asserted elements, scopes, or conditions remain uncorroborated: \"{pas_text}\"."
                        ),
                        0.75
                    )

            claim_words = set(re.findall(r"\b[a-zA-Z0-9_\-\.%]+\b", claim_lower)) - {"the", "and", "for", "with", "that", "this", "from", "our", "are", "on", "in"}
            pas_words = set(re.findall(r"\b[a-zA-Z0-9_\-\.%]+\b", pas_lower))
            overlap = len(claim_words.intersection(pas_words)) / max(1, len(claim_words))

            if overlap >= 0.38:
                return (
                    VerificationStatus.PARTIALLY_SUPPORTED.value,
                    pas_text,
                    pas["page_number"],
                    pas["section_title"],
                    (
                        f"Partial support detected: Source text at Page {pas['page_number']} supports core concepts of the claim "
                        f"(\"{pas_text}\"), but certain asserted conditions, scopes, or metrics remain unverified."
                    ),
                    round(overlap, 2)
                )

        # ------------------------------------------------------------------
        # 4. INSUFFICIENT EVIDENCE Fallback
        # ------------------------------------------------------------------
        return (
            VerificationStatus.INSUFFICIENT_EVIDENCE.value,
            best_evidence_text,
            best_page,
            best_section,
            (
                f"Insufficient evidence: In '{paper.title}', no passage contains factual assertions "
                f"substantiating this specific claim."
            ),
            round(best_score, 2)
        )

    # ----------------------------------------------------------------------
    # 4. Public Verification API Handlers & Persistence
    # ----------------------------------------------------------------------
    async def verify_claim(
        self,
        request: VerifyClaimRequest,
        db: Session
    ) -> VerificationResultResponse:
        """
        Independently validates a single research claim against the source PDF.
        Persistently saves the verification result in SQLite table verification_results.
        """
        paper = None
        if request.paper_id:
            paper = db.query(ResearchPaper).filter(ResearchPaper.id == request.paper_id).first()

        if not paper and request.claim_id:
            claim_rec = db.query(ResearchClaim).filter(ResearchClaim.id == request.claim_id).first()
            if claim_rec:
                paper = db.query(ResearchPaper).filter(ResearchPaper.id == claim_rec.paper_id).first()

        if not paper and request.project_id:
            papers = db.query(ResearchPaper).filter(ResearchPaper.project_id == request.project_id).all()
            if papers:
                paper = papers[0]

        if not paper:
            paper = db.query(ResearchPaper).first()

        if not paper:
            raise ValueError("No research papers found in the platform to verify against.")

        # Ensure claim_id exists in SQLite to satisfy foreign key constraints
        claim_id = request.claim_id
        if not claim_id:
            existing_claim = db.query(ResearchClaim).filter(
                ResearchClaim.paper_id == paper.id,
                ResearchClaim.claim_text == request.claim_text
            ).first()
            if existing_claim:
                claim_id = existing_claim.id
            else:
                new_claim = ResearchClaim(
                    id=str(uuid.uuid4()),
                    paper_id=paper.id,
                    claim_text=request.claim_text,
                    claim_type="performance",
                    confidence_score=1.0
                )
                db.add(new_claim)
                db.flush()
                claim_id = new_claim.id

        # 1. Retrieve original source passages
        passages = await self.retrieve_source_evidence(request.claim_text, paper, db)

        # 2. Evaluate claim against evidence
        status_val, evidence_text, page_num, sec_title, explanation, sim_score = self.evaluate_claim_against_evidence(
            request.claim_text, passages, paper
        )

        is_verified = status_val in [VerificationStatus.SUPPORTED.value, VerificationStatus.PARTIALLY_SUPPORTED.value]

        # 3. Persist in SQLite verification_results table
        verification_record = VerificationResult(
            id=str(uuid.uuid4()),
            claim_id=claim_id,
            paper_id=paper.id,
            claim_text=request.claim_text,
            verifier_agent="evidence_verification_agent",
            verification_status=status_val,
            supporting_evidence=evidence_text if is_verified else None,
            counter_evidence=evidence_text if status_val == VerificationStatus.CONTRADICTED.value else None,
            page_number=page_num,
            explanation=explanation,
            verification_score=sim_score,
            notes=f"Source: {sec_title or 'General'}"
        )
        db.add(verification_record)
        db.commit()

        logger.info(f"Verified claim: status='{status_val}', paper='{paper.title}', score={sim_score}")

        return VerificationResultResponse(
            id=verification_record.id,
            claim_text=request.claim_text,
            source_paper={"paper_id": paper.id, "title": paper.title},
            original_evidence=evidence_text,
            page_number=page_num,
            section_title=sec_title,
            verification_status=status_val,
            explanation=explanation,
            similarity_score=sim_score,
            is_verified_finding=is_verified,
            created_at=str(verification_record.created_at)
        )

    def verify_claim_sync(
        self,
        request: VerifyClaimRequest,
        db: Session
    ) -> VerificationResultResponse:
        """Synchronous version of verify_claim."""
        paper = None
        if request.paper_id:
            paper = db.query(ResearchPaper).filter(ResearchPaper.id == request.paper_id).first()
        if not paper:
            paper = db.query(ResearchPaper).first()
        if not paper:
            raise ValueError("No research papers found in database.")

        claim_id = request.claim_id
        if not claim_id:
            new_claim = ResearchClaim(
                id=str(uuid.uuid4()),
                paper_id=paper.id,
                claim_text=request.claim_text,
                claim_type="performance",
                confidence_score=1.0
            )
            db.add(new_claim)
            db.flush()
            claim_id = new_claim.id

        sections = db.query(PaperSection).filter(PaperSection.paper_id == paper.id).all()
        candidate_passages = []
        for s in sections:
            candidate_passages.append({
                "text": s.content,
                "page_number": s.page_number or 1,
                "section_title": s.section_title or "General",
                "score": 0.85,
                "source": "sqlite_sections"
            })

        status_val, evidence_text, page_num, sec_title, explanation, sim_score = self.evaluate_claim_against_evidence(
            request.claim_text, candidate_passages, paper
        )
        is_verified = status_val in [VerificationStatus.SUPPORTED.value, VerificationStatus.PARTIALLY_SUPPORTED.value]

        verification_record = VerificationResult(
            id=str(uuid.uuid4()),
            claim_id=claim_id,
            paper_id=paper.id,
            claim_text=request.claim_text,
            verifier_agent="evidence_verification_agent",
            verification_status=status_val,
            supporting_evidence=evidence_text if is_verified else None,
            counter_evidence=evidence_text if status_val == VerificationStatus.CONTRADICTED.value else None,
            page_number=page_num,
            explanation=explanation,
            verification_score=sim_score,
            notes=f"Source: {sec_title or 'General'}"
        )
        db.add(verification_record)
        db.commit()

        return VerificationResultResponse(
            id=verification_record.id,
            claim_text=request.claim_text,
            source_paper={"paper_id": paper.id, "title": paper.title},
            original_evidence=evidence_text,
            page_number=page_num,
            section_title=sec_title,
            verification_status=status_val,
            explanation=explanation,
            similarity_score=sim_score,
            is_verified_finding=is_verified,
            created_at=str(verification_record.created_at)
        )

    async def verify_gap(
        self,
        gap_id: str,
        db: Session
    ) -> List[VerificationResultResponse]:
        """
        Validates all evidence passages associated with an identified research gap.
        """
        gap = db.query(ResearchGap).filter(ResearchGap.id == gap_id).first()
        if not gap:
            raise ValueError(f"Research gap '{gap_id}' not found.")

        results: List[VerificationResultResponse] = []
        for ev in gap.evidences:
            paper = db.query(ResearchPaper).filter(ResearchPaper.id == ev.paper_id).first()
            if not paper:
                continue

            req = VerifyClaimRequest(
                claim_text=f"{gap.title}. Context: {ev.quote_or_excerpt[:150]}",
                paper_id=paper.id
            )
            res = await self.verify_claim(req, db)
            results.append(res)

        return results

    async def batch_verify(
        self,
        claims: List[VerifyClaimRequest],
        db: Session
    ) -> BatchVerifyClaimsResponse:
        """
        Batch validates a collection of claims.
        """
        results: List[VerificationResultResponse] = []
        supported_count = 0
        partially_count = 0
        contradicted_count = 0
        insufficient_count = 0

        for req in claims:
            res = await self.verify_claim(req, db)
            results.append(res)
            if res.verification_status == VerificationStatus.SUPPORTED.value:
                supported_count += 1
            elif res.verification_status == VerificationStatus.PARTIALLY_SUPPORTED.value:
                partially_count += 1
            elif res.verification_status == VerificationStatus.CONTRADICTED.value:
                contradicted_count += 1
            elif res.verification_status == VerificationStatus.INSUFFICIENT_EVIDENCE.value:
                insufficient_count += 1

        return BatchVerifyClaimsResponse(
            total_claims=len(claims),
            verified_count=supported_count,
            partially_supported_count=partially_count,
            contradicted_count=contradicted_count,
            insufficient_evidence_count=insufficient_count,
            results=results
        )

verification_agent = EvidenceVerificationAgent()
