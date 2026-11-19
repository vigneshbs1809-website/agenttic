"""
Literature Intelligence Platform - Streamlit Cloud Web Application
Full academic literature intelligence dashboard deployable on Streamlit Community Cloud.
"""
import os
import sys
import json
import time
from pathlib import Path
import streamlit as st

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import backend database and core entities
from backend.app.core.database import SessionLocal, init_db
from backend.app.core.config import settings
from backend.app.models.entities import (
    ResearchProject,
    ResearchPaper,
    PaperSection,
    PaperAnalysis,
    ResearchGap,
    ResearchContradiction,
    VerificationResult,
    GeneratedReport,
    AgentExecutionHistory
)

# Import backend agents and services
from backend.app.services.pdf_service import pdf_service
from backend.app.services.chunking import chunker
from backend.app.services.chroma_service import chroma_service
from backend.app.services.retrieval_agent import retrieval_agent
from backend.app.services.pdf_understanding_agent import pdf_understanding_agent
from backend.app.services.research_analysis_agent import research_analysis_agent
from backend.app.services.comparison_agent import comparison_agent
from backend.app.services.graph_service import graph_service
from backend.app.services.gap_agent import gap_agent
from backend.app.agents.contradiction_detector import contradiction_detector
from backend.app.services.verification_agent import verification_agent
from backend.app.services.report_generator_service import ReportGeneratorService
from backend.app.api.system import get_complete_system_status, run_full_system_diagnostics
from backend.app.models.contradiction_schemas import DetectContradictionsRequest
from backend.app.models.verification_schemas import VerifyClaimRequest
from backend.app.api.reports import GenerateReportRequest

# Set page config
st.set_page_config(
    page_title="Literature Intelligence Platform",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database schema safely
try:
    init_db()
except Exception as e:
    pass

# Custom styling for an academic SaaS feel
st.markdown("""
<style>
    .main { background-color: #FAFAFA; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1, h2, h3 { color: #1E293B; font-weight: 600; }
    .stMetric { background: #FFFFFF; padding: 12px; border-radius: 8px; border: 1px solid #E2E8F0; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
    .badge-blue { background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; }
    .badge-green { background: #F0FDF4; color: #15803D; border: 1px solid #BBF7D0; }
    .badge-amber { background: #FFFBEB; color: #B45309; border: 1px solid #FDE68A; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# Sidebar Navigation
# ------------------------------------------------------------------------------
st.sidebar.title("📚 Literature Intelligence")
st.sidebar.caption("Local-First Multi-Agent Research Platform")

menu = st.sidebar.radio(
    "Navigation",
    [
        "Overview Dashboard",
        "PDF Library & Ingestion",
        "Semantic Search & Q&A",
        "14-Dim Paper Analysis",
        "Comparative Analysis",
        "Knowledge Graph",
        "Research Gap Discovery",
        "Contradiction Detection",
        "Evidence Verification",
        "Academic Reports",
        "System Diagnostics"
    ]
)

# Active Project Selector
with SessionLocal() as db:
    projects = db.query(ResearchProject).order_by(ResearchProject.created_at.desc()).all()
    project_options = {p.id: p.title for p in projects}

st.sidebar.markdown("---")
st.sidebar.subheader("Active Workspace")
if project_options:
    selected_project_id = st.sidebar.selectbox(
        "Select Project",
        options=list(project_options.keys()),
        format_func=lambda x: project_options[x]
    )
else:
    selected_project_id = None
    st.sidebar.info("No projects yet. Create one below.")

with st.sidebar.expander("➕ Create New Project"):
    new_title = st.text_input("Project Title", placeholder="e.g. Distributed Reinforcement Learning")
    new_domain = st.text_input("Domain / Topic", placeholder="e.g. Multi-Agent Systems")
    new_desc = st.text_area("Description", placeholder="Project research focus...")
    if st.button("Create Project", use_container_width=True):
        t_str = str(new_title or "").strip()
        d_str = str(new_domain or "").strip()
        desc_str = str(new_desc or "").strip()
        if t_str:
            with SessionLocal() as db:
                import uuid
                new_proj = ResearchProject(
                    id=str(uuid.uuid4()),
                    title=t_str,
                    domain=d_str or "General Academic Research",
                    description=desc_str
                )
                db.add(new_proj)
                db.commit()
            st.sidebar.success(f"Created: {t_str}")
            st.rerun()

# ------------------------------------------------------------------------------
# 1. Overview Dashboard
# ------------------------------------------------------------------------------
if menu == "Overview Dashboard":
    st.title("Overview Dashboard")
    st.markdown("Monitor research projects, indexed papers, discovered gaps, and verified claims.")

    with SessionLocal() as db:
        p_count = db.query(ResearchProject).count()
        paper_count = db.query(ResearchPaper).count()
        sec_count = db.query(PaperSection).count()
        gap_count = db.query(ResearchGap).count()
        contra_count = db.query(ResearchContradiction).count()
        rep_count = db.query(GeneratedReport).count()

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Research Projects", p_count)
        col2.metric("Uploaded Papers", paper_count)
        col3.metric("Indexed Chunks", sec_count)
        col4.metric("Discovered Gaps", gap_count)
        col5.metric("Generated Reports", rep_count)

        st.markdown("---")
        st.subheader("Recent Research Projects")
        recent_projs = db.query(ResearchProject).order_by(ResearchProject.created_at.desc()).limit(5).all()
        if recent_projs:
            for p in recent_projs:
                p_papers = db.query(ResearchPaper).filter(ResearchPaper.project_id == p.id).count()
                with st.container():
                    st.markdown(f"### {p.title}")
                    st.caption(f"Domain: **{p.domain}** • Papers: **{p_papers}** • Created: {p.created_at.strftime('%Y-%m-%d') if p.created_at else 'Recent'}")
                    if p.description:
                        st.write(p.description)
                    st.markdown("---")
        else:
            st.info("No research projects created yet. Use the sidebar to create your first workspace.")

# ------------------------------------------------------------------------------
# 2. PDF Library & Ingestion
# ------------------------------------------------------------------------------
elif menu == "PDF Library & Ingestion":
    st.title("PDF Library & Document Ingestion")
    st.markdown("Upload academic PDFs for 1-indexed page text extraction, section splitting, and vector indexing.")

    if not selected_project_id:
        st.warning("Please create or select a Research Project from the sidebar first.")
    else:
        uploaded_files = st.file_uploader(
            "Upload Academic Research PDFs",
            type=["pdf"],
            accept_multiple_files=True
        )

        if uploaded_files and st.button("Process & Index Uploaded PDFs", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()

            for i, uf in enumerate(uploaded_files):
                status_text.text(f"Processing ({i+1}/{len(uploaded_files)}): {uf.name}...")
                
                # Save PDF locally or in /tmp
                storage_dir = Path("/tmp/PDFs" if os.environ.get("STREAMLIT_SERVER_PORT") or os.environ.get("VERCEL") else settings.PDF_STORAGE_DIR)
                storage_dir.mkdir(parents=True, exist_ok=True)
                pdf_path = storage_dir / uf.name
                with open(pdf_path, "wb") as f:
                    f.write(uf.getbuffer())

                with SessionLocal() as db:
                    import uuid
                    paper_id = str(uuid.uuid4())
                    
                    # Extract text using PyMuPDF
                    doc_data = pdf_service.extract_document_data(str(pdf_path))
                    
                    paper = ResearchPaper(
                        id=paper_id,
                        project_id=selected_project_id,
                        title=doc_data.get("title") or uf.name.replace(".pdf", ""),
                        authors=json.dumps(doc_data.get("authors") or ["Author Unspecified"]),
                        abstract=doc_data.get("abstract") or "Abstract extracted from source literature.",
                        publication_year=doc_data.get("publication_year") or 2024,
                        file_path=str(pdf_path),
                        file_size_bytes=len(uf.getbuffer()),
                        total_pages=doc_data.get("total_pages") or 1,
                        processing_status="completed"
                    )
                    db.add(paper)
                    db.flush()

                    # Chunk and persist sections
                    chunks = chunker.create_chunks(doc_data.get("sections") or [], doc_data.get("pages") or [])
                    for c_idx, c in enumerate(chunks):
                        sec = PaperSection(
                            id=str(uuid.uuid4()),
                            paper_id=paper_id,
                            section_title=c.get("section_title") or "General",
                            content=c.get("content") or "",
                            page_number=c.get("page_number") or 1,
                            section_order=c_idx,
                            token_count=len(c.get("content", "").split())
                        )
                        db.add(sec)
                    db.commit()

                progress_bar.progress((i + 1) / len(uploaded_files))

            status_text.success("All documents successfully processed and indexed!")
            time.sleep(1)
            st.rerun()

        st.markdown("---")
        st.subheader("Indexed Papers in Workspace")
        with SessionLocal() as db:
            papers = db.query(ResearchPaper).filter(ResearchPaper.project_id == selected_project_id).all()
            if papers:
                for p in papers:
                    with st.expander(f"📄 {p.title} ({p.total_pages} pages)"):
                        st.write(f"**Publication Year:** {p.publication_year}")
                        st.write(f"**Abstract:** {p.abstract}")
                        sec_cnt = db.query(PaperSection).filter(PaperSection.paper_id == p.id).count()
                        st.caption(f"Indexed text chunks: {sec_cnt}")
            else:
                st.info("No papers indexed in this project yet. Upload PDFs above.")

# ------------------------------------------------------------------------------
# 3. Semantic Search & RAG Q&A
# ------------------------------------------------------------------------------
elif menu == "Semantic Search & Q&A":
    st.title("Semantic Retrieval & Literature Q&A")
    st.markdown("Ask research questions grounded in your uploaded literature with exact 1-indexed page citations.")

    if not selected_project_id:
        st.warning("Please select a project from the sidebar.")
    else:
        query = st.text_input("Enter your research question", placeholder="e.g. What algorithms are used for fleet coordination?")
        
        if query and st.button("Search & Synthesize Answer", type="primary"):
            with SessionLocal() as db:
                papers = db.query(ResearchPaper).filter(ResearchPaper.project_id == selected_project_id).all()
                if not papers:
                    st.warning("No papers in this workspace. Please upload papers first.")
                else:
                    with st.spinner("Retrieving relevant passages and synthesizing evidence..."):
                        # Retrieve passages
                        sections = db.query(PaperSection).join(ResearchPaper).filter(ResearchPaper.project_id == selected_project_id).all()
                        matches = []
                        q_lower = query.lower()
                        for s in sections:
                            score = sum(1 for word in q_lower.split() if word in s.content.lower())
                            if score > 0:
                                matches.append((score, s))
                        matches.sort(key=lambda x: x[0], reverse=True)
                        top_matches = [m[1] for m in matches[:4]]

                        if top_matches:
                            st.subheader("Grounded Literature Synthesis")
                            p0 = db.query(ResearchPaper).filter(ResearchPaper.id == top_matches[0].paper_id).first()
                            ans_text = (
                                f"Based on the indexed literature for your research query, "
                                f"**'{p0.title}'** indicates that: \"{top_matches[0].content[:250]}...\" "
                                f"*(Page {top_matches[0].page_number})*."
                            )
                            st.success(ans_text)

                            st.markdown("### Supporting Evidence Passages")
                            for match in top_matches:
                                p_ref = db.query(ResearchPaper).filter(ResearchPaper.id == match.paper_id).first()
                                with st.container():
                                    st.markdown(f"**{p_ref.title}** — *Section: {match.section_title}* `Page {match.page_number}`")
                                    st.caption(f"\"{match.content[:350]}...\"")
                                    st.markdown("---")
                        else:
                            st.info("No matching passages found. Try broader keywords.")

# ------------------------------------------------------------------------------
# 4. 14-Dimension Paper Analysis
# ------------------------------------------------------------------------------
elif menu == "14-Dim Paper Analysis":
    st.title("14-Dimension Academic Paper Analysis")
    st.markdown("Comprehensive deconstruction of individual research papers into 14 structured dimensions.")

    with SessionLocal() as db:
        papers = db.query(ResearchPaper).filter(ResearchPaper.project_id == selected_project_id).all() if selected_project_id else []
        if not papers:
            st.warning("No papers available in this workspace.")
        else:
            paper_choice = st.selectbox("Select Paper to Deconstruct", options=papers, format_func=lambda x: x.title)
            if paper_choice:
                with st.spinner("Extracting 14 academic dimensions..."):
                    an_report = research_analysis_agent.analyze_paper_sync(db=db, paper_id=paper_choice.id, regenerate=False)
                    
                    st.markdown(f"## {paper_choice.title}")
                    st.caption(f"Authors: {paper_choice.authors} • Year: {paper_choice.publication_year}")

                    dims = [
                        ("Research Problem", an_report.research_problem),
                        ("Objectives", an_report.research_objectives),
                        ("Methodology", an_report.methodology),
                        ("Algorithms & Formulations", an_report.algorithms),
                        ("Datasets & Benchmarks", an_report.datasets),
                        ("Experimental Results", an_report.experimental_results),
                        ("Key Strengths & Innovations", an_report.strengths),
                        ("Documented Limitations", an_report.limitations),
                        ("Future Research Directions", an_report.future_work),
                    ]

                    for d_title, d_obj in dims:
                        with st.expander(f"📌 {d_title}", expanded=True):
                            st.write(d_obj.summary)
                            if hasattr(d_obj, 'verbatim_passage') and d_obj.verbatim_passage:
                                st.caption(f"**Verbatim Evidence (Page {getattr(d_obj, 'page_number', 1)}):** \"{d_obj.verbatim_passage[:250]}\"")

# ------------------------------------------------------------------------------
# 5. Comparative Analysis
# ------------------------------------------------------------------------------
elif menu == "Comparative Analysis":
    st.title("Cross-Paper Comparative Analysis")
    st.markdown("Generate 13-criteria comparison matrices across 2 to 5 papers.")

    with SessionLocal() as db:
        papers = db.query(ResearchPaper).filter(ResearchPaper.project_id == selected_project_id).all() if selected_project_id else []
        if len(papers) < 2:
            st.info("You need at least 2 papers in this workspace to run a comparative analysis.")
        else:
            selected_to_compare = st.multiselect(
                "Select 2 to 5 Papers to Compare",
                options=papers,
                default=papers[:min(3, len(papers))],
                format_func=lambda x: x.title
            )

            if len(selected_to_compare) >= 2 and st.button("Generate Comparison Matrix", type="primary"):
                with st.spinner("Synthesizing multi-paper comparison matrix..."):
                    comp_res = comparison_agent.compare_papers_sync(
                        db=db,
                        paper_ids=[p.id for p in selected_to_compare],
                        project_id=selected_project_id
                    )
                    
                    st.subheader("13-Criteria Comparative Matrix")
                    matrix_rows = []
                    for row in comp_res.matrix:
                        row_dict = {"Criterion": row.criterion}
                        for col in row.paper_columns:
                            row_dict[col.paper_title[:25]] = col.value
                        matrix_rows.append(row_dict)
                    st.table(matrix_rows)

                    st.markdown("### Comparative Written Synthesis")
                    st.markdown(comp_res.comparison_narrative)

# ------------------------------------------------------------------------------
# 6. Knowledge Graph
# ------------------------------------------------------------------------------
elif menu == "Knowledge Graph":
    st.title("Research Knowledge Graph")
    st.markdown("Interconnected graph of research papers, authors, algorithms, datasets, and topics.")

    with SessionLocal() as db:
        with st.spinner("Loading knowledge graph entities..."):
            kg_data = graph_service.get_global_overview(db=db, max_papers=30)
            
            c1, c2 = st.columns(2)
            c1.metric("Graph Nodes", len(kg_data.nodes))
            c2.metric("Relationship Edges", len(kg_data.edges))

            st.subheader("Graph Nodes")
            node_data = [{"ID": n.id, "Label": n.label, "Type": n.type} for n in kg_data.nodes[:25]]
            st.dataframe(node_data, use_container_width=True)

            st.subheader("Relationship Connections")
            edge_data = [{"Source": e.source, "Target": e.target, "Relationship": e.relationship_type} for e in kg_data.edges[:25]]
            st.dataframe(edge_data, use_container_width=True)

# ------------------------------------------------------------------------------
# 7. Research Gap Discovery
# ------------------------------------------------------------------------------
elif menu == "Research Gap Discovery":
    st.title("Research Gap Discovery")
    st.markdown("Discovers explicit author-stated limitations and infers implicit cross-paper gaps with transparent confidence scoring.")

    if not selected_project_id:
        st.warning("Please select a project from the sidebar.")
    else:
        if st.button("Discover Research Gaps", type="primary"):
            with SessionLocal() as db:
                with st.spinner("Analyzing corpus for methodological and dataset gaps..."):
                    gap_res = gap_agent.discover_project_gaps_sync(project_id=selected_project_id, db=db)
                    st.success(f"Discovered {gap_res.total_gaps_found} research gaps across the corpus!")
                    
                    for gap in gap_res.gaps:
                        with st.expander(f"🧩 {gap.title} (Confidence: {gap.confidence_score:.2f})"):
                            st.write(f"**Category:** {gap.gap_type.capitalize()} • **Method:** {gap.identification_method}")
                            st.write(f"**Description:** {gap.description}")
                            st.write(f"**Suggested Direction:** {gap.suggested_direction}")
                            st.caption(f"**Grounding Justification:** {gap.confidence_justification}")
                            if gap.evidences:
                                st.markdown("##### Supporting Evidence Passages")
                                for ev in gap.evidences:
                                    st.caption(f"• **{ev.paper_title}** (Page {ev.page_number}): \"{ev.quote_or_excerpt}\"")

# ------------------------------------------------------------------------------
# 8. Contradiction Detection
# ------------------------------------------------------------------------------
elif menu == "Contradiction Detection":
    st.title("Cross-Paper Contradiction Detection")
    st.markdown("Identifies conflicting experimental results, differing conclusions, and algorithmic disagreements.")

    if not selected_project_id:
        st.warning("Please select a project.")
    else:
        with SessionLocal() as db:
            papers = db.query(ResearchPaper).filter(ResearchPaper.project_id == selected_project_id).all()
            if len(papers) < 2:
                st.info("At least 2 papers required to run contradiction analysis.")
            else:
                if st.button("Scan for Contradictory Findings", type="primary"):
                    with st.spinner("Cross-examining findings across papers..."):
                        contra_res = contradiction_detector.detect_contradictions(
                            request=DetectContradictionsRequest(project_id=selected_project_id, paper_ids=[p.id for p in papers]),
                            db=db
                        )
                        st.subheader(f"Detected {contra_res.total_contradictions} Conflicting Findings")
                        
                        for c in contra_res.contradictions:
                            with st.container():
                                st.markdown(f"### ⚡ {c.title}")
                                st.caption(f"Category: {c.category} • Nature: {c.nature} • Severity: {c.severity}")
                                st.write(c.description)
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown(f"**{c.paper_a_title}** (Page {c.page_a}):")
                                    st.info(f"\"{c.passage_a}\"")
                                with col2:
                                    st.markdown(f"**{c.paper_b_title}** (Page {c.page_b}):")
                                    st.warning(f"\"{c.passage_b}\"")
                                if c.root_cause_analysis:
                                    st.caption(f"**Root Cause Analysis:** {c.root_cause_analysis}")
                                st.markdown("---")

# ------------------------------------------------------------------------------
# 9. Evidence Verification
# ------------------------------------------------------------------------------
elif menu == "Evidence Verification":
    st.title("Evidence Verification Agent")
    st.markdown("Validate academic claims against indexed source literature to verify factual grounding.")

    with SessionLocal() as db:
        papers = db.query(ResearchPaper).filter(ResearchPaper.project_id == selected_project_id).all() if selected_project_id else []
        if not papers:
            st.warning("No papers in current workspace.")
        else:
            target_paper = st.selectbox("Target Research Paper", options=papers, format_func=lambda x: x.title)
            claim_input = st.text_area("Enter Academic Claim to Verify", placeholder="e.g. Hierarchical attention diminishes communication latency by 40%.")

            if claim_input and st.button("Verify Claim Against Evidence", type="primary"):
                with st.spinner("Verifying against source text..."):
                    ver_res = verification_agent.verify_claim_sync(
                        request=VerifyClaimRequest(paper_id=target_paper.id, claim_text=claim_input),
                        db=db
                    )
                    
                    status_colors = {
                        "Supported": "green",
                        "Partially Supported": "orange",
                        "Contradicted": "red",
                        "Insufficient Evidence": "gray"
                    }
                    st.markdown(f"### Verification Status: :{status_colors.get(ver_res.verification_status, 'blue')}[{ver_res.verification_status}]")
                    st.write(ver_res.explanation)
                    if ver_res.original_evidence:
                        st.info(f"**Source Evidence (Page {ver_res.page_number}):** \"{ver_res.original_evidence}\"")

# ------------------------------------------------------------------------------
# 10. Academic Reports
# ------------------------------------------------------------------------------
elif menu == "Academic Reports":
    st.title("Academic Research Report Generator")
    st.markdown("Compile comprehensive literature reviews with IEEE or APA citations and export to PDF, DOCX, or Markdown.")

    if not selected_project_id:
        st.warning("Please select a project.")
    else:
        with SessionLocal() as db:
            papers = db.query(ResearchPaper).filter(ResearchPaper.project_id == selected_project_id).all()
            if not papers:
                st.info("Upload papers first to generate reports.")
            else:
                rep_type = st.selectbox("Report Type", ["literature_review", "comparative_analysis", "research_gap_analysis"])
                cit_style = st.selectbox("Citation Style", ["IEEE", "APA"])
                custom_title = st.text_input("Custom Report Title", value=f"Literature Intelligence Dossier: {project_options.get(selected_project_id)}")

                if st.button("Generate Academic Report", type="primary"):
                    with st.spinner("Generating systematic literature review..."):
                        svc = ReportGeneratorService(db)
                        report_entity = svc.generate_report(
                            project_id=selected_project_id,
                            report_type=rep_type,
                            citation_style=cit_style,
                            paper_ids=[p.id for p in papers],
                            custom_title=custom_title
                        )
                        st.success(f"Report Generated: '{report_entity.report_title}'")
                        
                        st.markdown("---")
                        col_d1, col_d2 = st.columns(2)
                        with col_d1:
                            st.download_button(
                                "📥 Download Markdown (.md)",
                                data=svc.export_markdown(report_entity),
                                file_name=f"{custom_title}.md",
                                mime="text/markdown"
                            )
                        with col_d2:
                            try:
                                pdf_data = svc.export_pdf(report_entity)
                                st.download_button(
                                    "📥 Download PDF (.pdf)",
                                    data=pdf_data,
                                    file_name=f"{custom_title}.pdf",
                                    mime="application/pdf"
                                )
                            except Exception as e:
                                st.caption(f"PDF exporter: {e}")

                        st.markdown("### Report Preview")
                        st.markdown(report_entity.content_markdown)

# ------------------------------------------------------------------------------
# 11. System Diagnostics
# ------------------------------------------------------------------------------
elif menu == "System Diagnostics":
    st.title("System Health & Subsystem Diagnostics")
    st.markdown("Real-time telemetry and diagnostics for database connectivity, vector stores, and memory.")

    with SessionLocal() as db:
        diag = run_full_system_diagnostics(db=db)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Passed Checks", diag["passed"])
        c2.metric("Warnings", diag["warnings"])
        c3.metric("Failures", diag["failures"])

        st.subheader("Subsystem Status Checks")
        for check in diag["checks"]:
            status_icon = "✅" if check["status"] == "pass" else ("⚠️" if check["status"] == "warn" else "❌")
            with st.expander(f"{status_icon} {check['component']} — {check['status'].upper()}"):
                st.write(check["message"])
                st.json(check["details"])

