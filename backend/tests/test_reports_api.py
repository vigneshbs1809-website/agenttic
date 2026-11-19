import sys
sys.path.insert(0, "d:/Literature-Intelligence-Platform/venv/Lib/site-packages")
sys.path.insert(0, ".")

from backend.app.core.database import SessionLocal
from backend.app.models.entities import ResearchProject
from backend.app.api.reports import (
    generate_report,
    list_report_history,
    get_report_by_id,
    export_report_file,
    delete_report,
    GenerateReportRequest,
)

def test_api_direct():
    db = SessionLocal()
    try:
        proj = db.query(ResearchProject).first()
        assert proj is not None, "Project required for testing"
        print(f"Testing API handlers with Project: {proj.title} (ID: {proj.id})")

        # 1. Test generate_report (Complete Literature Review, APA)
        print("\n--- 1. Testing generate_report endpoint ---")
        req = GenerateReportRequest(
            project_id=proj.id,
            report_type="literature_review",
            citation_style="APA",
            custom_title="Grounded Literature Review: Local LLM Viability"
        )
        created = generate_report(payload=req, db=db)
        rep_id = created.id
        print(f"  -> Generated Report: {rep_id} | {created.report_title}")
        assert created.citation_style == "APA"
        assert "Systematic Literature Review" in created.content_markdown
        assert created.word_count > 200

        # 2. Test list_report_history
        print("\n--- 2. Testing list_report_history endpoint ---")
        history = list_report_history(project_id=proj.id, limit=50, db=db)
        print(f"  -> History returned {len(history)} items for project.")
        assert len(history) > 0
        found = any(h.id == rep_id for h in history)
        assert found, f"Report {rep_id} not found in history"

        # 3. Test get_report_by_id
        print(f"\n--- 3. Testing get_report_by_id ({rep_id}) ---")
        detail = get_report_by_id(report_id=rep_id, db=db)
        assert detail.id == rep_id
        assert detail.report_title == created.report_title
        print(f"  -> Successfully retrieved report detail ({detail.word_count} words).")

        # 4. Test export_report_file (PDF)
        print(f"\n--- 4. Testing export_report_file PDF ---")
        pdf_resp = export_report_file(report_id=rep_id, export_format="pdf", db=db)
        assert pdf_resp.media_type == "application/pdf"
        assert len(pdf_resp.body) > 2000
        print(f"  -> PDF export verified ({len(pdf_resp.body)} bytes).")

        # 5. Test export_report_file (DOCX)
        print(f"\n--- 5. Testing export_report_file DOCX ---")
        docx_resp = export_report_file(report_id=rep_id, export_format="docx", db=db)
        assert "wordprocessingml.document" in docx_resp.media_type
        assert len(docx_resp.body) > 1000
        print(f"  -> DOCX export verified ({len(docx_resp.body)} bytes).")

        # 6. Test export_report_file (Markdown)
        print(f"\n--- 6. Testing export_report_file Markdown ---")
        md_resp = export_report_file(report_id=rep_id, export_format="markdown", db=db)
        assert "text/markdown" in md_resp.media_type
        assert len(md_resp.body) > 500
        print(f"  -> Markdown export verified ({len(md_resp.body)} bytes).")

        # 7. Test delete_report
        print(f"\n--- 7. Testing delete_report ---")
        del_resp = delete_report(report_id=rep_id, db=db)
        assert del_resp["status"] == "success"
        print(f"  -> Deleted report {rep_id} successfully.")

        # Confirm 404 on deleted report
        try:
            get_report_by_id(report_id=rep_id, db=db)
            assert False, "Expected 404 HTTPException"
        except Exception as e:
            assert getattr(e, "status_code", None) == 404
            print("  -> Confirmed 404 response on deleted report.")

        print("\n==========================================")
        print("ALL REPORTS API ROUTER HANDLERS VERIFIED 100%!")
        print("==========================================")

    finally:
        db.close()

if __name__ == "__main__":
    test_api_direct()
