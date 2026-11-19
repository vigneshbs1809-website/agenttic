import os
import sys
import json
import asyncio
import functools
from pathlib import Path

# Force unbuffered output
print = functools.partial(print, flush=True)

# Set PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.core.database import SessionLocal, init_db
from backend.app.models.entities import (
    ResearchPaper,
    ResearchContradiction,
    PaperAnalysis,
    ResearchProject
)
from backend.app.models.contradiction_schemas import (
    DetectContradictionsRequest,
    ContradictionNature,
    ContradictionCategory
)
from backend.app.agents.contradiction_detector import contradiction_detector
from backend.app.services.trend_analysis_service import trend_analysis_service

def test_modules():
    print("=====================================================================")
    print("TESTING MODULE A: CONTRADICTION DETECTION & MODULE B: TREND ANALYSIS")
    print("=====================================================================")

    # 1. Initialize schema (creates research_contradictions table)
    init_db()
    db = SessionLocal()

    try:
        # Check current papers in DB
        paper_count = db.query(ResearchPaper).count()
        print(f"[*] Found {paper_count} research papers in SQLite database.")
        assert paper_count > 0, "No research papers found in database."

        # -------------------------------------------------------------
        # TEST 1: MODULE A - Contradiction Detection
        # -------------------------------------------------------------
        print("\n[PHASE 1] Executing Contradiction Detection Agent across papers...")
        request = DetectContradictionsRequest(force_redetect=True)
        response = contradiction_detector.detect_contradictions(request=request, db=db)

        print(f"[*] Total contradictions detected: {response.total_contradictions}")
        print(f"    - Genuine Contradictions: {response.genuine_count}")
        print(f"    - Condition-Dependent Differences: {response.condition_dependent_count}")
        print(f"    - Methodological Divergences: {response.methodological_divergence_count}")
        print(f"    - Category Breakdown: {response.category_breakdown}")

        assert response.total_contradictions > 0, "Expected at least one contradiction to be detected."

        # Verify provenance and source passages
        sample = response.contradictions[0]
        print(f"\n[*] Sample Detected Contradiction:")
        print(f"    Title: {sample.title}")
        print(f"    Category: {sample.category.value}")
        print(f"    Nature: {sample.nature.value}")
        print(f"    Paper A: '{sample.paper_a_title}' (Page {sample.page_a}, Section: {sample.section_a})")
        print(f"    Passage A Excerpt: {sample.passage_a[:120]}...")
        print(f"    Paper B: '{sample.paper_b_title}' (Page {sample.page_b}, Section: {sample.section_b})")
        print(f"    Passage B Excerpt: {sample.passage_b[:120]}...")
        print(f"    Root Cause Analysis: {sample.root_cause_analysis[:140]}...")

        assert len(sample.passage_a) > 0, "Passage A must not be empty"
        assert len(sample.passage_b) > 0, "Passage B must not be empty"
        assert sample.page_a is not None, "Page A must be populated"
        assert sample.page_b is not None, "Page B must be populated"
        assert sample.root_cause_analysis is not None, "Root cause analysis must be populated"

        # Verify SQLite Persistence
        saved_count = db.query(ResearchContradiction).count()
        print(f"[*] Verified SQLite persistence: {saved_count} rows in 'research_contradictions' table.")
        assert saved_count >= response.total_contradictions, "Rows must be stored in database."

        # -------------------------------------------------------------
        # TEST 2: MODULE B - Research Trend Analysis (Real Data)
        # -------------------------------------------------------------
        print("\n[PHASE 2] Executing Research Trend Analysis on actual SQLite data...")
        trends = trend_analysis_service.analyze_trends(db=db)

        print(f"[*] Total Papers Analyzed: {trends.total_papers_analyzed}")
        print(f"[*] Total Structured Analyses: {trends.total_analyses_analyzed}")
        print(f"[*] Total Research Gaps Analyzed: {trends.total_gaps_analyzed}")

        # 1. Publications by Year
        print(f"\n[*] 1. Publications by Year ({len(trends.publications_by_year)} years):")
        for yt in trends.publications_by_year:
            print(f"    - Year {yt.year}: {yt.paper_count} papers (cumulative: {yt.cumulative_papers})")
        assert len(trends.publications_by_year) > 0, "Expected publication year distributions."

        # 2. Frequently Used Algorithms
        print(f"\n[*] 2. Top Frequently Used Algorithms ({len(trends.top_algorithms)} algorithms):")
        for at in trends.top_algorithms[:5]:
            print(f"    - {at.name}: {at.count} papers ({at.percentage}%)")
        assert len(trends.top_algorithms) > 0, "Expected top algorithms extracted from SQLite."

        # 3. Frequently Used Datasets
        print(f"\n[*] 3. Top Frequently Evaluated Datasets ({len(trends.top_datasets)} datasets):")
        for dt in trends.top_datasets[:5]:
            print(f"    - {dt.name}: {dt.count} papers ({dt.percentage}%)")
        assert len(trends.top_datasets) > 0, "Expected top datasets extracted from SQLite."

        # 4. Research Topic Distribution
        print(f"\n[*] 4. Research Topic Distribution ({len(trends.topic_distribution)} topics):")
        for tt in trends.topic_distribution:
            print(f"    - {tt.topic}: {tt.count} papers ({tt.percentage}%)")
        assert len(trends.topic_distribution) > 0, "Expected topic distributions."

        # 5. Common Limitations
        print(f"\n[*] 5. Common Limitations ({len(trends.common_limitations)} themes):")
        for lt in trends.common_limitations[:4]:
            print(f"    - [{lt.category}] {lt.limitation}: {lt.count} papers")
        assert len(trends.common_limitations) > 0, "Expected common limitation themes."

        # 6. Emerging Research Directions
        print(f"\n[*] 6. Emerging Research Directions ({len(trends.emerging_directions)} directions):")
        for ed in trends.emerging_directions[:4]:
            print(f"    - {ed.direction} (Mentions: {ed.mention_count}, Recency: {ed.recency_score})")

        # 7. Underexplored Areas
        print(f"\n[*] 7. Underexplored Research Areas ({len(trends.underexplored_areas)} areas):")
        for ua in trends.underexplored_areas[:3]:
            print(f"    - [{ua.gap_category}] {ua.area} (Gaps: {ua.identified_in_gaps}, Eval: {ua.evaluated_in_papers})")

        print("\n=====================================================================")
        print("SUCCESS: BOTH MODULE A & MODULE B INTEGRATION TESTS PASSED 100%!")
        print("=====================================================================")

    finally:
        db.close()

if __name__ == "__main__":
    test_modules()
