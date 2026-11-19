import asyncio
import os
import sys

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import SessionLocal
from backend.app.models.entities import ResearchPaper, PaperAnalysis
from backend.app.services.research_analysis_agent import research_analysis_agent
from backend.app.services.comparison_agent import comparison_agent


async def main():
    print("=== Testing Paper Analysis & Cross-Paper Comparison ===", flush=True)
    db = SessionLocal()
    try:
        analyzed_papers = db.query(PaperAnalysis).all()
        print(f"Total analyzed papers in database: {len(analyzed_papers)}", flush=True)
        assert len(analyzed_papers) >= 2, "Need at least 2 analyzed papers in DB"

        # 1. Test Paper Analysis Retrieval
        target_id = analyzed_papers[0].paper_id
        target_paper = db.query(ResearchPaper).filter(ResearchPaper.id == target_id).first()
        print(f"\n1. Testing Paper Analysis for paper '{target_id}' ({target_paper.title[:40]}...)", flush=True)
        analysis_report = await research_analysis_agent.analyze_paper(db, target_id)
        assert analysis_report is not None, "Analysis report should not be None"
        assert analysis_report.paper_id == target_id
        assert analysis_report.title is not None
        print(f"  [PASS] Successfully retrieved analysis report with {len(analysis_report.dimensions)} dimensions.", flush=True)
        for dim in analysis_report.dimensions[:3]:
            print(f"    - Dimension '{dim.dimension_name}': status={dim.status}, evidence count={len(dim.evidence_passages)}", flush=True)

        # 2. Test Markdown Generation
        md_text = research_analysis_agent.generate_markdown_report(analysis_report)
        assert len(md_text) > 100
        print(f"  [PASS] Markdown dossier generated ({len(md_text)} characters).", flush=True)

        # 3. Test Cross-Paper Comparison
        sample_ids = [a.paper_id for a in analyzed_papers[:3]]
        print(f"\n2. Testing Cross-Paper Comparison for {len(sample_ids)} papers: {sample_ids}", flush=True)
        comparison_res = await comparison_agent.compare_papers(db, sample_ids)
        assert comparison_res is not None, "Comparison response should not be None"
        report = comparison_res.report
        print(f"  [PASS] Comparison successful: '{report.title}'", flush=True)
        print(f"  [PASS] Matrix rows: {len(report.matrix)}", flush=True)
        assert len(report.matrix) > 0, "Matrix rows should not be empty"
        print(f"  [PASS] Similarities: {len(report.similarities)}, Differences: {len(report.methodological_differences)}", flush=True)
        print(f"  [PASS] Comparability assessment valid: is_comparable={report.comparability_assessment.is_comparable}", flush=True)
        print(f"    Assessment verdict: {report.comparability_assessment.verdict}", flush=True)
        print(f"    Warning: {report.comparability_assessment.warning}", flush=True)

        # Check evidence attached to cells
        row0 = report.matrix[0]
        print(f"  Matrix row sample: '{row0.criterion}' across {len(row0.cells)} papers", flush=True)
        for cell in row0.cells:
            print(f"    - Paper {cell.paper_id}: summary='{cell.summary[:30]}...', evidence items={len(cell.evidence)}", flush=True)

        print("\nALL ANALYSIS & COMPARISON BACKEND TESTS PASSED SUCCESSFULLY!", flush=True)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
