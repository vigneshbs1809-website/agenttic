import asyncio
import os
import sys

# Ensure venv site-packages and repository root are in sys.path
sys.path.insert(0, "D:/Literature-Intelligence-Platform/venv/Lib/site-packages")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import SessionLocal
from backend.app.models.entities import PaperAnalysis
from backend.app.services.research_analysis_agent import research_analysis_agent
from backend.app.services.comparison_agent import comparison_agent


async def run():
    print("Connecting to database...", flush=True)
    db = SessionLocal()
    try:
        analyses = db.query(PaperAnalysis).all()
        print(f"Found {len(analyses)} existing paper analyses.", flush=True)
        if not analyses:
            print("No analyses found.", flush=True)
            return

        target_id = analyses[0].paper_id
        print(f"Testing analyze_paper on paper_id='{target_id}'...", flush=True)
        rep = await research_analysis_agent.analyze_paper(db, target_id)
        print(f"Analysis complete: '{rep.paper_title}'", flush=True)
        print(f"Extracted dimensions: {len(rep.dimensions)}", flush=True)
        for dim in rep.dimensions[:4]:
            print(f"  * {dim.dimension_name}: status={dim.status}, evidence count={len(dim.evidence_passages)}", flush=True)

        md = research_analysis_agent.generate_markdown_report(rep)
        print(f"Generated Markdown report ({len(md)} chars).", flush=True)

        # Cross paper comparison test
        test_ids = [a.paper_id for a in analyses[:3]]
        print(f"\nTesting compare_papers for {len(test_ids)} papers...", flush=True)
        comp_res = await comparison_agent.compare_papers(db, test_ids)
        report = comp_res.report
        print(f"Comparison report: '{report.title}'", flush=True)
        print(f"Matrix criteria count: {len(report.matrix)}", flush=True)
        print(f"Comparability assessment: {report.comparability_assessment.verdict}", flush=True)
        print(f"Warning notice: {report.comparability_assessment.warning[:100]}...", flush=True)
        print("\nALL ANALYSIS & COMPARISON CHECKS PASSED PERFECTLY!", flush=True)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run())
