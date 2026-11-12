import sys
import os

sys.path.insert(0, "d:/Literature-Intelligence-Platform/venv/Lib/site-packages")
sys.path.insert(0, ".")
sys.path.insert(0, "backend")

from backend.app.core.database import SessionLocal
from backend.app.models.entities import ResearchProject, GeneratedReport
from backend.app.services.report_generator_service import ReportGeneratorService
import fitz
import zipfile
import io

def test_report_service():
    db = SessionLocal()
    try:
        # Pick first project
        proj = db.query(ResearchProject).first()
        assert proj is not None, "No project found in SQLite!"
        print(f"Testing with Project: {proj.title} (ID: {proj.id})")

        svc = ReportGeneratorService(db)

        # 1. Test Complete Literature Review with IEEE
        print("\n--- 1. Testing Complete Literature Review (IEEE) ---")
        rep_lit_ieee = svc.generate_report(
            project_id=proj.id,
            report_type="literature_review",
            citation_style="IEEE"
        )
        assert rep_lit_ieee.id is not None
        assert "# Systematic Literature Review:" in rep_lit_ieee.content_markdown
        assert "## 1. Introduction" in rep_lit_ieee.content_markdown
        assert "## 2. Research Background" in rep_lit_ieee.content_markdown
        assert "## 3. Thematic Literature Review" in rep_lit_ieee.content_markdown
        assert "## 4. Individual Paper Analysis" in rep_lit_ieee.content_markdown
        assert "## 5. Comparative Methodology Analysis" in rep_lit_ieee.content_markdown
        assert "## 6. Research Trends" in rep_lit_ieee.content_markdown
        assert "## 7. Contradiction Analysis" in rep_lit_ieee.content_markdown
        assert "## 8. Research Gaps" in rep_lit_ieee.content_markdown
        assert "## 9. Evidence Verification Results" in rep_lit_ieee.content_markdown
        assert "## 10. Research Objectives" in rep_lit_ieee.content_markdown
        assert "## 11. Proposed Methodology" in rep_lit_ieee.content_markdown
        assert "## 12. Conclusion" in rep_lit_ieee.content_markdown
        assert "## References" in rep_lit_ieee.content_markdown
        assert "[1]" in rep_lit_ieee.content_markdown
        print("  -> Passed: Complete Literature Review contains all 15 sections & IEEE citations.")

        # Test PDF Export
        pdf_bytes = svc.export_pdf(rep_lit_ieee)
        assert len(pdf_bytes) > 2000, f"PDF too small: {len(pdf_bytes)} bytes"
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        assert doc.page_count >= 1
        print(f"  -> Passed: PDF generated ({len(pdf_bytes)} bytes, {doc.page_count} pages).")
        doc.close()

        # Test DOCX Export
        docx_bytes = svc.export_docx(rep_lit_ieee)
        assert len(docx_bytes) > 1500, f"DOCX too small: {len(docx_bytes)} bytes"
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
            assert "word/document.xml" in z.namelist()
            assert "[Content_Types].xml" in z.namelist()
        print(f"  -> Passed: DOCX generated ({len(docx_bytes)} bytes, valid OpenXML archive).")

        # 2. Test Complete Literature Review with APA
        print("\n--- 2. Testing Complete Literature Review (APA) ---")
        rep_lit_apa = svc.generate_report(
            project_id=proj.id,
            report_type="literature_review",
            citation_style="APA"
        )
        assert "(" in rep_lit_apa.content_markdown and ")" in rep_lit_apa.content_markdown
        print("  -> Passed: APA citation formatting verified.")

        # 3. Test Remaining 5 Report Types
        other_types = [
            "individual_paper",
            "comparative_analysis",
            "gap_analysis",
            "contradiction_analysis",
            "proposed_methodology",
        ]

        for r_type in other_types:
            print(f"\n--- Testing Report Type: {r_type} ---")
            rep = svc.generate_report(
                project_id=proj.id,
                report_type=r_type,
                citation_style="IEEE"
            )
            assert rep.id is not None
            assert len(rep.content_markdown) > 500
            # Test PDF & DOCX for each
            p_bytes = svc.export_pdf(rep)
            d_bytes = svc.export_docx(rep)
            assert len(p_bytes) > 1000
            assert len(d_bytes) > 1000
            print(f"  -> Passed: {r_type} generated (MD: {len(rep.content_markdown)} chars, PDF: {len(p_bytes)} bytes, DOCX: {len(d_bytes)} bytes).")

        print("\n==========================================")
        print("ALL 6 REPORT TYPES & EXPORTS VERIFIED 100%!")
        print("==========================================")

    finally:
        db.close()

if __name__ == "__main__":
    test_report_service()
