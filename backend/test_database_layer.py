import asyncio
import sys
import uuid
from pathlib import Path
from datetime import datetime
import httpx

# Set up module path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect
from backend.app.core.database import engine, SessionLocal, init_db, check_db_health, DB_PATH
from backend.app.models.entities import (
    Base,
    ResearchProject,
    ResearchPaper,
    Author,
    PaperSection,
    PaperAnalysis,
    ExtractedEntity,
    ResearchGap,
    GapEvidence,
    ResearchClaim,
    VerificationResult,
    AgentExecutionHistory,
    GeneratedReport,
    ReviewerFeedback,
    paper_authors
)
from backend.app.models.project_schemas import ProjectCreate, ProjectUpdate
from backend.app.services.project_service import project_service
from backend.app.main import app

def test_database_and_apis():
    print("=" * 70)
    print("  SQLAlchemy SQLite Database Layer & API Operations Verification")
    print("=" * 70)

    # 1. Initialize DB and inspect all 13 tables
    print("\n[1/5] Initializing Database & Inspecting Normalized Tables...")
    init_db()
    inspector = inspect(engine)
    created_tables = inspector.get_table_names()
    print(f"  -> Total Tables Created: {len(created_tables)}")
    print(f"  -> Tables: {created_tables}")

    required_tables = [
        "research_projects",
        "research_papers",
        "authors",
        "paper_authors",
        "paper_sections",
        "paper_analyses",
        "extracted_entities",
        "research_gaps",
        "gap_evidences",
        "research_claims",
        "verification_results",
        "agent_execution_histories",
        "generated_reports",
        "reviewer_feedbacks"
    ]
    for tbl in required_tables:
        assert tbl in created_tables, f"Table '{tbl}' missing from SQLite database!"
    print("  -> All 14 normalized tables & association tables confirmed.")

    # 2. Insert records across all 13 models to test relations, FKs & cascade constraints
    print("\n[2/5] Testing Real Entity Creation Across All 13 Models...")
    db = SessionLocal()
    try:
        # 1. Research Project
        project = ResearchProject(
            title="Transformer Compression & Local LLM Optimization",
            description="Investigating 4-bit quantization and KV cache pruning on low-resource hardware.",
            domain="Machine Learning",
            status="active"
        )
        db.add(project)
        db.flush()
        print(f"  -> [1/13] ResearchProject created: ID={project.id}")

        # 2. Research Paper
        test_doi = f"10.1145/{uuid.uuid4().hex[:10]}"
        paper = ResearchPaper(
            project_id=project.id,
            title="Qwen2.5: Efficient Local Language Modeling on Edge CPUs",
            doi=test_doi,
            publication_year=2024,
            journal_or_conference="arXiv Preprint",
            abstract="We present quantization techniques for sub-2B parameter language models.",
            filename="qwen25_edge.pdf",
            file_path="data/uploads/qwen25_edge.pdf",
            file_size_bytes=1048576,
            total_pages=12,
            processed_status="completed"
        )
        db.add(paper)
        db.flush()
        print(f"  -> [2/13] ResearchPaper created: ID={paper.id} (DOI={test_doi})")

        # 3. Author & PaperAuthor Many-to-Many
        test_orcid = f"0000-0002-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}"
        author = Author(
            name="Dr. Alex Rivera",
            email=f"arivera_{uuid.uuid4().hex[:6]}@ai-research.org",
            affiliation="Institute for Local AI",
            orcid=test_orcid
        )
        db.add(author)
        db.flush()
        paper.authors.append(author)
        db.flush()
        print(f"  -> [3/13] Author & PaperAuthor created: ID={author.id}")

        # 4. Paper Section
        section = PaperSection(
            paper_id=paper.id,
            section_index=1,
            section_title="Introduction and Edge Computing Motivation",
            section_type="introduction",
            content="Running frontier neural models directly on client hardware eliminates privacy leaks...",
            token_count=180
        )
        db.add(section)
        db.flush()
        print(f"  -> [4/13] PaperSection created: ID={section.id}")

        # 5. Paper Analysis
        analysis = PaperAnalysis(
            paper_id=paper.id,
            methodology_summary="Post-training 4-bit quantization with group-wise scale factors.",
            key_findings="Maintained 96% perplexity parity while dropping RAM requirements to 1.4 GB.",
            strengths="Exceptional memory efficiency on 8 GB RAM systems.",
            limitations="Slight degradation on high-dimensional multi-hop reasoning tasks.",
            future_work="Integrating speculative decoding with small draft models.",
            confidence_score=0.95,
            model_used="qwen3:1.7b"
        )
        db.add(analysis)
        db.flush()
        print(f"  -> [5/13] PaperAnalysis created: ID={analysis.id}")

        # 6. Extracted Entity
        entity = ExtractedEntity(
            paper_id=paper.id,
            name="Q4_K_M Quantization",
            entity_type="method",
            context_snippet="We evaluate Q4_K_M quantization schemes across 1.7B parameter footprints.",
            frequency=6
        )
        db.add(entity)
        db.flush()
        print(f"  -> [6/13] ExtractedEntity created: ID={entity.id}")

        # 7. Research Gap
        gap = ResearchGap(
            project_id=project.id,
            title="Dynamic KV Cache Eviction Under Strict 8 GB RAM Ceilings",
            description="Lack of real-time cache compression mechanisms during extended context generation.",
            gap_type="methodological",
            significance_score=0.88,
            status="open"
        )
        db.add(gap)
        db.flush()
        print(f"  -> [7/13] ResearchGap created: ID={gap.id}")

        # 8. Gap Evidence
        evidence = GapEvidence(
            gap_id=gap.id,
            paper_id=paper.id,
            quote_or_excerpt="Current implementations maintain the entire KV cache in resident system memory without dynamic pruning.",
            page_number=8,
            confidence=0.92
        )
        db.add(evidence)
        db.flush()
        print(f"  -> [8/13] GapEvidence created: ID={evidence.id}")

        # 9. Research Claim
        claim = ResearchClaim(
            paper_id=paper.id,
            claim_text="Sub-2B parameter models achieve sub-100ms time-to-first-token on modern AVX2 CPUs.",
            claim_type="performance",
            confidence_score=0.89
        )
        db.add(claim)
        db.flush()
        print(f"  -> [9/13] ResearchClaim created: ID={claim.id}")

        # 10. Verification Result
        verification = VerificationResult(
            claim_id=claim.id,
            verifier_agent="claim_checker_agent",
            verification_status="supported",
            supporting_evidence="Benchmark Section 4.2 validates 78ms latency across Intel 12th Gen CPUs.",
            verification_score=0.91,
            notes="Consistent with local testing on Windows 11 host."
        )
        db.add(verification)
        db.flush()
        print(f"  -> [10/13] VerificationResult created: ID={verification.id}")

        # 11. Agent Execution History
        agent_log = AgentExecutionHistory(
            project_id=project.id,
            agent_name="literature_gap_analyzer",
            action_type="gap_analysis",
            input_payload='{"focus_domain": "quantized_llms"}',
            output_summary="Identified 1 critical memory eviction research gap.",
            status="completed",
            duration_ms=4200
        )
        db.add(agent_log)
        db.flush()
        print(f"  -> [11/13] AgentExecutionHistory created: ID={agent_log.id}")

        # 12. Generated Report
        report = GeneratedReport(
            project_id=project.id,
            report_title="Synthesis Report: Local LLM Viability on 8GB Systems",
            report_type="comprehensive_synthesis",
            content_markdown="# Local LLM Viability Report\nAnalysis confirms qwen3:1.7b operates within a 1.8GB envelope.",
            generation_model="qwen3:1.7b"
        )
        db.add(report)
        db.flush()
        print(f"  -> [12/13] GeneratedReport created: ID={report.id}")

        # 13. Reviewer Feedback
        feedback = ReviewerFeedback(
            report_id=report.id,
            reviewer_name="Prof. Sarah Chen",
            rating=5,
            comments="Thorough evaluation with rigorous empirical latency benchmarks.",
            suggested_edits="Include thermal throttling observations under sustained inference.",
            status="accepted"
        )
        db.add(feedback)
        db.flush()
        print(f"  -> [13/13] ReviewerFeedback created: ID={feedback.id}")

        db.commit()
        print("  -> All 13 models committed successfully to SQLite!")
        created_project_id = project.id

    except Exception as e:
        db.rollback()
        print(f"  ERROR creating entities: {e}")
        raise e
    finally:
        db.close()

    # 3. Test Persistence across DB sessions
    print("\n[3/5] Testing Data Persistence Across Session Reconnection...")
    fresh_db = SessionLocal()
    try:
        retrieved_proj = fresh_db.query(ResearchProject).filter(ResearchProject.id == created_project_id).first()
        assert retrieved_proj is not None, "Project not persisted!"
        assert len(retrieved_proj.papers) == 1, "Paper relation not persisted!"
        assert len(retrieved_proj.papers[0].authors) == 1, "Author relation not persisted!"
        assert len(retrieved_proj.gaps) == 1, "Gap relation not persisted!"
        assert len(retrieved_proj.reports) == 1, "Report relation not persisted!"
        print(f"  -> Successfully verified persistent project: '{retrieved_proj.title}'")
        print(f"  -> Author via M2M relation: '{retrieved_proj.papers[0].authors[0].name}'")
        print(f"  -> Analysis via 1-to-1: '{retrieved_proj.papers[0].analysis.model_used}'")
    finally:
        fresh_db.close()

    # 4. Test Service Layer CRUD Operations
    print("\n[4/5] Testing Project Service Layer CRUD...")
    db_session = SessionLocal()
    try:
        # Create
        new_proj_data = ProjectCreate(
            title="Autonomous Multi-Agent Literature Synthesis",
            description="Coordinating reader, verifier, and synthesizer agents.",
            domain="Autonomous Agents",
            status="active"
        )
        p2 = project_service.create_project(db_session, new_proj_data)
        print(f"  -> Service Created Project: ID={p2.id}")

        # Read
        p2_fetched = project_service.get_project_by_id(db_session, p2.id)
        assert p2_fetched is not None and p2_fetched.title == new_proj_data.title

        # Update
        update_data = ProjectUpdate(title="Autonomous Multi-Agent Synthesis (Updated)", status="completed")
        p2_updated = project_service.update_project(db_session, p2.id, update_data)
        assert p2_updated.title == "Autonomous Multi-Agent Synthesis (Updated)"
        assert p2_updated.status == "completed"
        print(f"  -> Service Updated Project: '{p2_updated.title}', Status={p2_updated.status}")

        # Delete
        deleted = project_service.delete_project(db_session, p2.id)
        assert deleted is True
        assert project_service.get_project_by_id(db_session, p2.id) is None
        print("  -> Service Deleted Project verified.")
    finally:
        db_session.close()

    # 5. Test FastAPI HTTP Endpoints
    print("\n[5/5] Testing FastAPI Project Endpoints via HTTP...")
    async def run_api_tests():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # POST /api/projects
            create_payload = {
                "title": "Quantum Error Correction in Deep Circuits",
                "description": "Systematic review of surface code variations.",
                "domain": "Quantum Computing",
                "status": "active"
            }
            res_create = await client.post("/api/projects", json=create_payload)
            print(f"  -> POST /api/projects: HTTP {res_create.status_code}")
            assert res_create.status_code == 201, f"POST /api/projects failed: {res_create.text}"
            created_json = res_create.json()
            api_proj_id = created_json["id"]
            print(f"     Created Project ID: {api_proj_id}")

            # GET /api/projects
            res_list = await client.get("/api/projects")
            print(f"  -> GET /api/projects: HTTP {res_list.status_code}")
            assert res_list.status_code == 200
            projects_list = res_list.json()
            print(f"     Found {len(projects_list)} projects in database.")
            assert any(p["id"] == api_proj_id for p in projects_list)

            # GET /api/projects/{project_id}
            res_get = await client.get(f"/api/projects/{api_proj_id}")
            print(f"  -> GET /api/projects/{api_proj_id}: HTTP {res_get.status_code}")
            assert res_get.status_code == 200
            get_json = res_get.json()
            assert get_json["title"] == create_payload["title"]

            # PUT /api/projects/{project_id}
            put_payload = {
                "description": "Updated literature scope on surface and color codes.",
                "status": "archived"
            }
            res_put = await client.put(f"/api/projects/{api_proj_id}", json=put_payload)
            print(f"  -> PUT /api/projects/{api_proj_id}: HTTP {res_put.status_code}")
            assert res_put.status_code == 200
            put_json = res_put.json()
            assert put_json["status"] == "archived"
            assert put_json["description"] == put_payload["description"]

            # DELETE /api/projects/{project_id}
            res_del = await client.delete(f"/api/projects/{api_proj_id}")
            print(f"  -> DELETE /api/projects/{api_proj_id}: HTTP {res_del.status_code}")
            assert res_del.status_code == 200

            # Verify 404 after deletion
            res_get_deleted = await client.get(f"/api/projects/{api_proj_id}")
            print(f"  -> GET /api/projects/{api_proj_id} (Post-Delete): HTTP {res_get_deleted.status_code}")
            assert res_get_deleted.status_code == 404

    asyncio.run(run_api_tests())

    print("\n" + "=" * 70)
    print("  SUCCESS: ALL 13 MODELS, PERSISTENCE, & 5 CRUD APIs VERIFIED!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = test_database_and_apis()
    sys.exit(0 if success else 1)
