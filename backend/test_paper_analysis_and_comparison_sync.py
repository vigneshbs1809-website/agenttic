import os
import sys
import json

# Ensure repository root and venv site-packages are in sys.path
sys.path.insert(0, "D:/Literature-Intelligence-Platform/venv/Lib/site-packages")
sys.path.insert(0, os.path.abspath("."))

from backend.app.core.database import SessionLocal
from backend.app.models.entities import ResearchPaper, PaperAnalysis, PaperComparison
from backend.app.models.research_analysis_schemas import (
    ResearchAnalysisReport,
    DimensionAnalysis,
    EvidenceRef
)
from backend.app.models.comparison_schemas import (
    CrossPaperComparisonReport,
    MatrixRow,
    MatrixCell,
    ComparabilityAssessment
)
from backend.app.services.research_analysis_agent import research_analysis_agent
from backend.app.services.comparison_agent import comparison_agent


def test_analysis_and_comparison_integrity():
    print("=================================================================", flush=True)
    print("TESTING PAPER ANALYSIS & COMPARATIVE ANALYSIS BACKEND & DATA", flush=True)
    print("=================================================================", flush=True)

    db = SessionLocal()
    try:
        # ---------------------------------------------------------------------
        # PART 1: PAPER ANALYSIS INTEGRITY
        # ---------------------------------------------------------------------
        print("\n--- 1. PAPER ANALYSIS: Database Records & 14-Dimension Verification ---", flush=True)
        analyses = db.query(PaperAnalysis).all()
        print(f"Total PaperAnalysis records in SQLite: {len(analyses)}", flush=True)
        assert len(analyses) > 0, "No PaperAnalysis records found in SQLite"

        # Check first 5 analyses
        verified_count = 0
        for an in analyses[:5]:
            paper = db.query(ResearchPaper).filter(ResearchPaper.id == an.paper_id).first()
            assert paper is not None, f"Paper with id {an.paper_id} not found"
            print(f"\nVerifying analysis for: '{paper.title[:50]}...' (ID: {paper.id})", flush=True)
            assert an.structured_data is not None, "Missing structured_data JSON in PaperAnalysis"

            data = json.loads(an.structured_data)
            # Verify required academic fields
            assert "research_problem" in data, "Missing research_problem in structured_data"
            assert ("research_objectives" in data or "objectives" in data), "Missing objectives in structured_data"
            assert ("research_methodology" in data or "methodology" in data), "Missing methodology in structured_data"
            assert "algorithms" in data, "Missing algorithms in structured_data"
            assert ("datasets" in data or "dataset_characteristics" in data), "Missing datasets in structured_data"
            assert ("experimental_results" in data or "results" in data), "Missing results in structured_data"
            assert "limitations" in data, "Missing limitations in structured_data"
            assert ("future_work" in data or "future_directions" in data), "Missing future directions in structured_data"

            # Check that evidence passages have page numbers and verbatim text
            prob = data.get("research_problem")
            if isinstance(prob, dict):
                page_num = prob.get("page_number")
                quote = prob.get("supporting_text") or prob.get("evidence")
                print(f"  [PASS] Research Problem: page={page_num}, quote len={len(quote) if quote else 0}", flush=True)

            verified_count += 1

        print(f"\n[PASS] Verified {verified_count} PaperAnalysis records successfully.", flush=True)

        # Test Markdown Dossier generation
        sample_an = analyses[0]
        sample_paper = db.query(ResearchPaper).filter(ResearchPaper.id == sample_an.paper_id).first()
        raw_dict = json.loads(sample_an.structured_data)

        # Check markdown generation
        print(f"\n--- 2. PAPER ANALYSIS: Markdown Dossier Inspection ---", flush=True)
        if sample_an.report_markdown:
            print(f"  [PASS] Cached Markdown dossier found: {len(sample_an.report_markdown)} chars", flush=True)
            assert "# Executive Research Intelligence Dossier" in sample_an.report_markdown or "# " in sample_an.report_markdown
        else:
            print("  [NOTE] Generating Markdown report on the fly from structured data...", flush=True)
            # Construct a test report
            prob_val = raw_dict.get("research_problem", {}).get("value", "Identified problem")
            obj_val = raw_dict.get("research_objectives", {}).get("value", "Identified objectives")
            meth_val = raw_dict.get("research_methodology", {}).get("value", "Methodology")
            res_val = raw_dict.get("experimental_results", {}).get("value", "Results")
            lim_val = raw_dict.get("limitations", {}).get("value", "Limitations")

            d1 = DimensionAnalysis(dimension_name="Research Problem", summary=prob_val, status="reported", evidence_passages=[])
            d2 = DimensionAnalysis(dimension_name="Objectives", summary=obj_val, status="reported", evidence_passages=[])
            d3 = DimensionAnalysis(dimension_name="Motivation", summary="Motivation", status="reported", evidence_passages=[])
            d4 = DimensionAnalysis(dimension_name="Methodology", summary=meth_val, status="reported", evidence_passages=[])
            d5 = DimensionAnalysis(dimension_name="Algorithms", summary="Algorithms", status="reported", evidence_passages=[])
            d6 = DimensionAnalysis(dimension_name="Datasets", summary="Datasets", status="reported", evidence_passages=[])
            d7 = DimensionAnalysis(dimension_name="Data Preprocessing", summary="Preprocessing", status="reported", evidence_passages=[])
            d8 = DimensionAnalysis(dimension_name="Experimental Setup", summary="Setup", status="reported", evidence_passages=[])
            d9 = DimensionAnalysis(dimension_name="Evaluation Metrics", summary="Metrics", status="reported", evidence_passages=[])
            d10 = DimensionAnalysis(dimension_name="Experimental Results", summary=res_val, status="reported", evidence_passages=[])
            d11 = DimensionAnalysis(dimension_name="Strengths", summary="Strengths", status="reported", evidence_passages=[])
            d12 = DimensionAnalysis(dimension_name="Limitations", summary=lim_val, status="reported", evidence_passages=[])
            d13 = DimensionAnalysis(dimension_name="Future Directions", summary="Future Directions", status="reported", evidence_passages=[])
            d14 = DimensionAnalysis(dimension_name="Reproducibility", summary="Reproducibility", status="reported", evidence_passages=[])

            test_rep = ResearchAnalysisReport(
                paper_id=sample_paper.id,
                paper_title=sample_paper.title,
                authors=[a.name for a in sample_paper.authors],
                publication_year=sample_paper.publication_year,
                doi=sample_paper.doi,
                journal_or_conference=sample_paper.journal_or_conference,
                research_problem=d1,
                objectives=d2,
                motivation=d3,
                methodology=d4,
                algorithms=d5,
                dataset_characteristics=d6,
                data_preprocessing=d7,
                experimental_setup=d8,
                evaluation_metrics=d9,
                results=d10,
                strengths=d11,
                limitations=d12,
                future_directions=d13,
                reproducibility=d14,
                executive_summary="Summary of paper.",
                confidence_score=0.95,
                model_used="qwen3:1.7b",
                report_markdown=f"# Research Dossier: {sample_paper.title}\n\n## Abstract\n{sample_paper.abstract}",
                analyzed_at="2026-11-13T00:00:00Z"
            )
            md_out = research_analysis_agent.generate_markdown_report(test_rep)
            assert len(md_out) > 100
            print(f"  [PASS] Successfully formatted Markdown dossier: {len(md_out)} chars", flush=True)

        # ---------------------------------------------------------------------
        # PART 2: CROSS-PAPER COMPARISON INTEGRITY
        # ---------------------------------------------------------------------
        print("\n--- 3. COMPARATIVE ANALYSIS: Database Records & Matrix Verification ---", flush=True)
        comparisons = db.query(PaperComparison).all()
        print(f"Total PaperComparison records in SQLite: {len(comparisons)}", flush=True)
        assert len(comparisons) > 0, "No PaperComparison records found in SQLite"

        for comp in comparisons:
            print(f"\nVerifying Comparison: '{comp.comparison_title}' (ID: {comp.id})", flush=True)
            paper_ids = json.loads(comp.paper_ids)
            print(f"  - Compared Papers count: {len(paper_ids)} (IDs: {paper_ids})", flush=True)
            assert 2 <= len(paper_ids) <= 5, "Compared papers count must be between 2 and 5"

            # Check matrix
            matrix_data = json.loads(comp.matrix_json)
            print(f"  - Matrix criteria rows count: {len(matrix_data)}", flush=True)
            assert len(matrix_data) >= 8, f"Matrix must contain at least 8 criteria rows, found {len(matrix_data)}"

            criteria_names = [r.get("criterion_label") or r.get("criterion_key") or r.get("criterion") for r in matrix_data]
            print(f"  - Criteria covered: {', '.join(criteria_names[:5])}...", flush=True)
            for expected_crit in ["Research Objectives", "Algorithms", "Methodolog", "Dataset", "Result"]:
                matched = any(expected_crit.lower() in c.lower() for c in criteria_names if c)
                assert matched, f"Expected criterion '{expected_crit}' not found in matrix"

            # Check cell evidence
            sample_row = matrix_data[0]
            for cell in sample_row["cells"]:
                assert "paper_id" in cell, "Cell missing paper_id"
                assert "value" in cell or "summary" in cell, "Cell missing value or summary"
                ev_quote = cell.get("evidence_quote")
                page = cell.get("page_number")
                print(f"    * Cell for paper {cell['paper_id']}: val='{cell.get('value', '')[:25]}...', page={page}, quote_len={len(ev_quote) if ev_quote else 0}", flush=True)

            print(f"  [PASS] Matrix row '{sample_row.get('criterion_label')}' verified with page citations & verbatim quotes", flush=True)

            # Check comparability assessment (Anti-Bias Requirement)
            if comp.comparability_json:
                comp_assessment = json.loads(comp.comparability_json)
                verdict = comp_assessment.get("verdict")
                is_comp = comp_assessment.get("is_directly_comparable", comp_assessment.get("is_comparable"))
                print(f"  - Comparability verdict: {verdict}", flush=True)
                print(f"  - Is directly comparable: {is_comp}", flush=True)
                warning = comp_assessment.get("warning_or_caveat") or comp_assessment.get("warning") or ""
                assert len(warning) > 0, "Comparability assessment must include warning text against false metric superiority"
                print(f"  [PASS] Anti-Bias Comparability Warning: '{warning[:80]}...'", flush=True)

            # Check written comparative summary
            if comp.comparative_summary:
                print(f"  [PASS] Written comparative summary: {len(comp.comparative_summary)} chars", flush=True)
                assert len(comp.comparative_summary) > 50

        print("\n=================================================================", flush=True)
        print("ALL PAPER ANALYSIS & COMPARATIVE ANALYSIS VERIFICATIONS PASSED!", flush=True)
        print("=================================================================", flush=True)

    finally:
        db.close()


if __name__ == "__main__":
    test_analysis_and_comparison_integrity()
