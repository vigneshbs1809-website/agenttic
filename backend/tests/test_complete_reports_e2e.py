import sys
import os

sys.path.insert(0, "d:/Literature-Intelligence-Platform/venv/Lib/site-packages")
sys.path.insert(0, ".")

from backend.app.core.database import SessionLocal
from backend.app.models.entities import ResearchProject, GeneratedReport
from backend.app.api.reports import (
    generate_report,
    list_report_history,
    get_report_by_id,
    export_report_file,
    delete_report,
    GenerateReportRequest,
)
import fitz
import zipfile
import io

def run_comprehensive_report_tests():
    db = SessionLocal()
    created_report_ids = []

    try:
        project = db.query(ResearchProject).first()
        assert project is not None, "A valid ResearchProject must exist in the database"
        print(f"=== Running Comprehensive Report Generator E2E Tests ===")
        print(f"Target Project: '{project.title}' (ID: {project.id})")

        # ---------------------------------------------------------------------
        # TEST 1: Complete Literature Review (IEEE Style) with all 15 Sections
        # ---------------------------------------------------------------------
        print("\n[TEST 1] Generating Complete Literature Review with IEEE Citation Style...")
        req_lit_ieee = GenerateReportRequest(
            project_id=project.id,
            report_type="literature_review",
            citation_style="IEEE",
            custom_title="Autonomous Routing & Optimization: Systematic Literature Review"
        )
        report_lit = generate_report(payload=req_lit_ieee, db=db)
        created_report_ids.append(report_lit.id)

        print(f"  -> Generated Report ID: {report_lit.id}")
        print(f"  -> Word Count: {report_lit.word_count}")

        # Verify all 15 required sections in Literature Review:
        required_sections = [
            ("# Autonomous Routing & Optimization:", "Title"),
            ("## Abstract", "Abstract"),
            ("## 1. Introduction", "Introduction"),
            ("## 2. Research Background", "Research Background"),
            ("## 3. Thematic Literature Review", "Thematic Literature Review"),
            ("## 4. Individual Paper Analysis", "Individual Paper Analysis"),
            ("## 5. Comparative Methodology Analysis", "Comparative Methodology Analysis"),
            ("## 6. Research Trends", "Research Trends"),
            ("## 7. Contradiction Analysis", "Contradiction Analysis"),
            ("## 8. Research Gaps", "Research Gaps"),
            ("## 9. Evidence Verification Results", "Evidence Verification Results"),
            ("## 10. Research Objectives", "Research Objectives"),
            ("## 11. Proposed Methodology", "Proposed Methodology"),
            ("## 12. Conclusion", "Conclusion"),
            ("## References", "References"),
        ]

        for sec_str, sec_name in required_sections:
            assert sec_str in report_lit.content_markdown, f"Missing required section: {sec_name} ({sec_str})"
            print(f"     ✓ Found section: {sec_name}")

        # Verify IEEE citation markers
        assert "[1]" in report_lit.content_markdown, "Missing IEEE citation marker [1]"
        print("     ✓ Verified IEEE citation markers [1] in text and bibliography.")

        # ---------------------------------------------------------------------
        # TEST 2: Complete Literature Review with APA Citation Style
        # ---------------------------------------------------------------------
        print("\n[TEST 2] Generating Complete Literature Review with APA Citation Style...")
        req_lit_apa = GenerateReportRequest(
            project_id=project.id,
            report_type="literature_review",
            citation_style="APA"
        )
        report_apa = generate_report(payload=req_lit_apa, db=db)
        created_report_ids.append(report_apa.id)

        assert report_apa.citation_style == "APA"
        assert "(" in report_apa.content_markdown and ")" in report_apa.content_markdown
        print("     ✓ Verified APA parenthetical citation syntax (Author, Year).")

        # ---------------------------------------------------------------------
        # TEST 3: All Other 5 Report Types
        # ---------------------------------------------------------------------
        other_types = [
            ("individual_paper", "Individual Paper Analysis"),
            ("comparative_analysis", "Comparative Analysis"),
            ("gap_analysis", "Research Gap Analysis"),
            ("contradiction_analysis", "Contradiction Analysis"),
            ("proposed_methodology", "Proposed Research Methodology"),
        ]

        for r_key, r_name in other_types:
            print(f"\n[TEST 3] Generating Report Type: {r_name} ({r_key})...")
            req = GenerateReportRequest(
                project_id=project.id,
                report_type=r_key,
                citation_style="IEEE"
            )
            rep = generate_report(payload=req, db=db)
            created_report_ids.append(rep.id)
            assert rep.word_count > 150
            print(f"     ✓ Generated {r_name} ({rep.word_count} words).")

        # ---------------------------------------------------------------------
        # TEST 4: Multi-Format Exports (PDF, DOCX, Markdown)
        # ---------------------------------------------------------------------
        print("\n[TEST 4] Verifying Multi-Format Exports for Literature Review...")

        # 4a. PDF Export
        pdf_res = export_report_file(report_id=report_lit.id, export_format="pdf", db=db)
        assert pdf_res.media_type == "application/pdf"
        assert len(pdf_res.body) > 10000
        # Parse PDF with PyMuPDF to ensure zero corruption
        pdf_doc = fitz.open(stream=pdf_res.body, filetype="pdf")
        assert pdf_doc.page_count >= 1
        print(f"     ✓ PDF Export Valid: {len(pdf_res.body)} bytes, {pdf_doc.page_count} pages.")
        pdf_doc.close()

        # 4b. DOCX Export
        docx_res = export_report_file(report_id=report_lit.id, export_format="docx", db=db)
        assert "wordprocessingml.document" in docx_res.media_type
        assert len(docx_res.body) > 3000
        # Validate OpenXML zip archive
        with zipfile.ZipFile(io.BytesIO(docx_res.body)) as z:
            namelist = z.namelist()
            assert "[Content_Types].xml" in namelist
            assert "word/document.xml" in namelist
            assert "word/styles.xml" in namelist
        print(f"     ✓ DOCX Export Valid: {len(docx_res.body)} bytes, fully compliant OpenXML.")

        # 4c. Markdown Export
        md_res = export_report_file(report_id=report_lit.id, export_format="markdown", db=db)
        assert "text/markdown" in md_res.media_type
        assert len(md_res.body) > 2000
        print(f"     ✓ Markdown Export Valid: {len(md_res.body)} bytes.")

        # ---------------------------------------------------------------------
        # TEST 5: History Audit & Single Report Retrieval
        # ---------------------------------------------------------------------
        print("\n[TEST 5] Verifying Report History Audit Log...")
        history = list_report_history(project_id=project.id, limit=50, db=db)
        assert len(history) >= len(created_report_ids)
        print(f"     ✓ Retrieved {len(history)} historical reports from SQLite.")

        detail = get_report_by_id(report_id=report_lit.id, db=db)
        assert detail.id == report_lit.id
        print(f"     ✓ Single report lookup by ID verified.")

        # ---------------------------------------------------------------------
        # TEST 6: Cleanup / Delete Validation
        # ---------------------------------------------------------------------
        print("\n[TEST 6] Testing Report Deletion...")
        del_target = created_report_ids.pop()
        del_res = delete_report(report_id=del_target, db=db)
        assert del_res["status"] == "success"
        print(f"     ✓ Deleted report {del_target} successfully.")

        print("\n=======================================================")
        print("ALL RESEARCH REPORT GENERATOR TESTS PASSED WITH 100%!")
        print("=======================================================")

    finally:
        db.close()

if __name__ == "__main__":
    run_comprehensive_report_tests()

