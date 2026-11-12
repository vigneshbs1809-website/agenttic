import os
import sys
import json

# Ensure repository root and venv site-packages are in sys.path
sys.path.insert(0, "D:/Literature-Intelligence-Platform/venv/Lib/site-packages")
sys.path.insert(0, os.path.abspath("."))

from backend.app.core.database import SessionLocal
from backend.app.models.entities import (
    ResearchPaper,
    ResearchProject,
    ResearchGap,
    GapEvidence,
    VerificationResult
)
from backend.app.services.graph_service import graph_service
from backend.app.services.gap_agent import gap_agent


def test_three_intelligence_pages():
    print("=================================================================", flush=True)
    print("TESTING 3 CORE RESEARCH INTELLIGENCE MODULES (GRAPH, GAPS, VERIFICATION)", flush=True)
    print("=================================================================", flush=True)

    db = SessionLocal()
    try:
        # ---------------------------------------------------------------------
        # PART 1: KNOWLEDGE GRAPH AGENT (NetworkX)
        # ---------------------------------------------------------------------
        print("\n--- 1. PAGE A: KNOWLEDGE GRAPH BACKEND ---", flush=True)
        graph_resp = graph_service.get_global_overview(db=db, max_papers=40)
        assert graph_resp is not None, "Graph response should not be None"
        print(f"Total Nodes generated: {len(graph_resp.nodes)}", flush=True)
        print(f"Total Edges generated: {len(graph_resp.edges)}", flush=True)
        assert len(graph_resp.nodes) > 0, "Graph must contain nodes"
        assert len(graph_resp.edges) > 0, "Graph must contain edges"

        # Check entity types present
        node_types = set(n.type for n in graph_resp.nodes)
        print(f"Node Types present: {node_types}", flush=True)
        for expected_type in ["paper", "author", "algorithm", "dataset"]:
            assert expected_type in node_types, f"Expected node type '{expected_type}' in knowledge graph"

        # Check edge relations present
        edge_relations = set(e.relation for e in graph_resp.edges)
        print(f"Edge Relations present: {edge_relations}", flush=True)
        assert any("algorithm" in r or "dataset" in r or "cites" in r or "author" in r for r in edge_relations)

        # Check graph stats
        stats = graph_resp.stats
        print(f"Graph Stats: Total Nodes={stats.total_nodes}, Total Edges={stats.total_edges}, Node Types={stats.node_types}", flush=True)
        print("  [PASS] Knowledge Graph multi-relational generation verified.")

        # ---------------------------------------------------------------------
        # PART 2: RESEARCH GAPS DISCOVERY AGENT
        # ---------------------------------------------------------------------
        print("\n--- 2. PAGE B: RESEARCH GAPS BACKEND ---", flush=True)
        gaps = db.query(ResearchGap).all()
        print(f"Total ResearchGap records in SQLite: {len(gaps)}", flush=True)
        assert len(gaps) > 0, "No ResearchGap records found in SQLite"

        # Verify gap categories and confidence justifications
        sample_gap = gaps[0]
        print(f"Sample Gap: '{sample_gap.title}' (ID: {sample_gap.id})", flush=True)
        print(f"  - Category: {sample_gap.gap_type}", flush=True)
        print(f"  - Identification Method: {sample_gap.identification_method}", flush=True)
        print(f"  - Confidence Score: {sample_gap.confidence_score}", flush=True)
        print(f"  - Confidence Justification: {sample_gap.confidence_justification[:80] if sample_gap.confidence_justification else 'N/A'}...", flush=True)
        print(f"  - Suggested Direction: {sample_gap.suggested_direction[:80] if sample_gap.suggested_direction else 'N/A'}...", flush=True)

        evidences = db.query(GapEvidence).filter(GapEvidence.gap_id == sample_gap.id).all()
        print(f"  - Evidences count: {len(evidences)}", flush=True)
        for ev in evidences[:2]:
            quote = ev.quote_or_excerpt or ""
            print(f"    * Passage: '{quote[:60]}...' (Page {ev.page_number}, counter={ev.is_counter_evidence})", flush=True)

        # Test Gap Status Update (Approval & Editing)
        orig_status = sample_gap.status
        sample_gap.status = "approved"
        db.commit()
        db.refresh(sample_gap)
        assert sample_gap.status == "approved", "Gap status should be updated to approved"
        print("  [PASS] Gap approval update succeeded.", flush=True)

        sample_gap.status = orig_status
        db.commit()
        print("  [PASS] Research Gaps schema and provenance verified.")

        # ---------------------------------------------------------------------
        # PART 3: EVIDENCE VERIFICATION AGENT
        # ---------------------------------------------------------------------
        print("\n--- 3. PAGE C: EVIDENCE VERIFICATION BACKEND ---", flush=True)
        verifs = db.query(VerificationResult).all()
        print(f"Total VerificationResult records in SQLite: {len(verifs)}", flush=True)
        assert len(verifs) > 0, "No VerificationResult records found in SQLite"

        # Verify all 4 required statuses exist in the benchmark set
        statuses = set(v.verification_status for v in verifs)
        print(f"Verification Statuses present in SQLite: {statuses}", flush=True)
        for expected_status in ["Supported", "Partially Supported", "Contradicted", "Insufficient Evidence"]:
            assert expected_status in statuses, f"Missing status '{expected_status}' in verification database"

        # Check evidence and page citations on a supported and contradicted claim
        for v in verifs[:6]:
            c_text = v.claim_text or v.notes or "Factual proposition"
            print(f"Claim [{v.verification_status}]: '{c_text[:50]}...'", flush=True)
            print(f"  - Source Paper ID: {v.paper_id}, Page: {v.page_number}", flush=True)
            print(f"  - Explanation: {v.explanation[:80] if v.explanation else 'N/A'}...", flush=True)
            quote = getattr(v, "supporting_evidence", None) or getattr(v, "original_evidence", None)
            if quote:
                print(f"  - Supporting Evidence Quote: '{quote[:60]}...'", flush=True)
            if v.counter_evidence:
                print(f"  - Counter Evidence Quote: '{v.counter_evidence[:60]}...'", flush=True)

        print("\n=================================================================", flush=True)
        print("ALL 3 CORE RESEARCH INTELLIGENCE MODULES PASSED INTEGRITY TESTS!", flush=True)
        print("=================================================================", flush=True)

    finally:
        db.close()


if __name__ == "__main__":
    test_three_intelligence_pages()
