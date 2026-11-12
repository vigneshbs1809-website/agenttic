import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import io
import time
import uuid
import asyncio
import pymupdf
import httpx
from httpx import ASGITransport

from backend.app.main import app
from backend.app.core.database import SessionLocal, init_db
from backend.app.models.entities import ResearchProject, ResearchPaper, ExtractedEntity, ResearchClaim, PaperCitation
from backend.app.services.document_processing import document_processor

def build_pdf(title: str, sections_data: list) -> bytes:
    doc = pymupdf.open()
    current_page = doc.new_page(width=595, height=842)
    y = 50
    current_page.insert_text((50, y), title, fontsize=15, fontname="helv", color=(0, 0, 0))
    y += 35
    current_page.insert_text((50, y), "Research Knowledge Graph Test Series", fontsize=10, fontname="helv", color=(0.3, 0.3, 0.3))
    y += 35

    for sec_heading, sec_body in sections_data:
        if y > 680:
            current_page = doc.new_page(width=595, height=842)
            y = 50

        current_page.insert_text((50, y), sec_heading.upper(), fontsize=12, fontname="helv", color=(0, 0.2, 0.6))
        y += 20
        rect = pymupdf.Rect(50, y, 545, y + 140)
        current_page.insert_textbox(rect, sec_body, fontsize=9.5, fontname="helv", color=(0.1, 0.1, 0.1))
        y += 120

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

async def run_knowledge_graph_tests():
    print("=" * 80)
    print("STARTING RESEARCH KNOWLEDGE GRAPH AGENT INTEGRATION TESTS (NetworkX)")
    print("=" * 80)
    init_db()

    pdf_dir = Path("backend/data/PDFs")
    pdf_dir.mkdir(parents=True, exist_ok=True)

    # 1. Paper 1: Foundational Architecture (Cited Paper)
    p1_title = "Centralized Value Factorization for Autonomous Multi-Agent Dispatch"
    p1_sections = [
        ("Abstract",
         "Decentralized coordination in dense fleets suffers from credit assignment failure. "
         "In this work, our objective is to propose CentralQ, a value-factorized multi-agent reinforcement learning algorithm. "
         "CentralQ achieves an 89.2% success rate and 28.4% latency reduction on the Fleet-Dispatch-Bench."),
        ("Introduction",
         "The fundamental research problem is credit assignment failure during dense multi-agent fleet dispatch. "
         "We address this limitation by factorizing joint state-action value functions into monotonic agent utilities."),
        ("Methodology",
         "Our methodology employs CentralQ with hypernetwork value mixing and AdamW gradient descent. "
         "We formulate decentralized observation histories into permutation-invariant agent embeddings."),
        ("Experiments",
         "Evaluated on Fleet-Dispatch-Bench across 500 stochastic scenarios. "
         "Evaluation metrics comprise Success Rate, Latency, and Throughput."),
        ("Limitations",
         "A major limitation is that joint value monotonicity restricts expressiveness in asymmetric non-monotonic payoff games."),
        ("Conclusion",
         "CentralQ demonstrates scalable coordination in large-scale vehicle fleets with verified convergence.")
    ]

    # 2. Paper 2: Derivative Architecture that cites Paper 1 explicitly in References
    p2_title = "Hierarchical Multi-Agent Graph Dispatch for Megacity Logistics"
    p2_sections = [
        ("Abstract",
         "Megacity logistics involves thousands of heterogeneous delivery robots. "
         "We propose HierarchicalQ, which builds upon the centralized factorization of CentralQ. "
         "HierarchicalQ attains 93.6% success rate on the Fleet-Dispatch-Bench with 3.4x faster convergence."),
        ("Introduction",
         "Scaling coordination to thousands of delivery agents introduces severe communication bottlenecks. "
         "Our research problem is communication overhead in dense multi-agent dispatch."),
        ("Methodology",
         "Our methodology introduces HierarchicalQ, using CentralQ as the underlying base agent and AdamW optimization. "
         "Spatial clustering groups agents into topological subgraphs."),
        ("Experiments",
         "We benchmark on Fleet-Dispatch-Bench and Urban-Grid-50k. "
         "Metrics include Success Rate, Convergence Speed, and Latency."),
        ("Limitations",
         "High latency occurs when sub-cluster partitions experience severe topological reconfigurations."),
        ("Conclusion",
         "HierarchicalQ sets a new standard for hierarchical multi-agent dispatch."),
        ("References",
         "[1] Centralized Value Factorization for Autonomous Multi-Agent Dispatch. Fleet AI Journal, 2024.\n"
         "[2] Sutton, R. S., & Barto, A. G. Reinforcement Learning: An Introduction. MIT Press, 2018.")
    ]

    # 3. Paper 3: Different domain / year paper (shares AdamW methodology but no citations to Paper 1 or 2)
    p3_title = "Graph Neural Diffusion for Molecular Target Affinity Prediction"
    p3_sections = [
        ("Abstract",
         "Predicting molecular affinity requires scalable graph representation learning. "
         "Our objective is to present MolDiffNet, a continuous graph neural diffusion algorithm. "
         "MolDiffNet achieves a 91.4% ROC-AUC score on the MoleculeNet benchmark."),
        ("Introduction",
         "Target affinity estimation suffers from oversmoothing in deep Graph Neural Networks. "
         "We tackle the research problem of graph oversmoothing in molecular property prediction."),
        ("Methodology",
         "Our methodology uses MolDiffNet with continuous ODE solvers and AdamW optimization."),
        ("Experiments",
         "We evaluate on the MoleculeNet benchmark. Evaluation metrics include ROC-AUC and F1 Score."),
        ("Limitations",
         "Continuous ODE integration exhibits high inference latency on large macromolecules."),
        ("Conclusion",
         "MolDiffNet resolves oversmoothing in biochemical property modeling.")
    ]

    p1_path = pdf_dir / "test_kg_paper1.pdf"
    p2_path = pdf_dir / "test_kg_paper2.pdf"
    p3_path = pdf_dir / "test_kg_paper3.pdf"

    p1_bytes = build_pdf(p1_title, p1_sections)
    p2_bytes = build_pdf(p2_title, p2_sections)
    p3_bytes = build_pdf(p3_title, p3_sections)

    p1_path.write_bytes(p1_bytes)
    p2_path.write_bytes(p2_bytes)
    p3_path.write_bytes(p3_bytes)

    db = SessionLocal()
    project = None
    try:
        # Create Project
        project = ResearchProject(
            title=f"Knowledge Graph Benchmark Study {uuid.uuid4().hex[:6]}",
            description="Testing NetworkX Research Knowledge Graph Agent",
            domain="Multi-Agent Systems"
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        print(f"[1/8] Created Project: '{project.title}' (ID: {project.id})")

        # Ingest Paper 1 (2024)
        doc1_id = f"test-p1-{uuid.uuid4().hex[:8]}"
        paper1 = await document_processor.process_pdf_document(
            db=db,
            doc_id=doc1_id,
            file_path=p1_path,
            original_filename="test_kg_paper1.pdf",
            file_size=len(p1_bytes),
            project_id=project.id
        )
        paper1.publication_year = 2024
        db.commit()

        # Ingest Paper 2 (2025, cites Paper 1)
        doc2_id = f"test-p2-{uuid.uuid4().hex[:8]}"
        paper2 = await document_processor.process_pdf_document(
            db=db,
            doc_id=doc2_id,
            file_path=p2_path,
            original_filename="test_kg_paper2.pdf",
            file_size=len(p2_bytes),
            project_id=project.id
        )
        paper2.publication_year = 2025
        db.commit()

        # Ingest Paper 3 (2023, Bio domain)
        doc3_id = f"test-p3-{uuid.uuid4().hex[:8]}"
        paper3 = await document_processor.process_pdf_document(
            db=db,
            doc_id=doc3_id,
            file_path=p3_path,
            original_filename="test_kg_paper3.pdf",
            file_size=len(p3_bytes),
            project_id=project.id
        )
        paper3.publication_year = 2023
        db.commit()
        print(f"[2/8] Ingested 3 test papers: P1 ({paper1.id}), P2 ({paper2.id}), P3 ({paper3.id})")

        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 3. Test Full Project Graph Generation
            print("\n[3/8] Testing Project Knowledge Graph (GET /api/graph/project/{project_id})...")
            res_proj = await client.get(f"/api/graph/project/{project.id}")
            assert res_proj.status_code == 200, f"Project graph failed: {res_proj.text}"
            graph_data = res_proj.json()
            nodes = graph_data["nodes"]
            edges = graph_data["edges"]
            stats = graph_data["stats"]

            print(f"-> Total Nodes: {stats['total_nodes']}, Total Edges: {stats['total_edges']}")
            print(f"-> Node Types: {stats['node_types']}")
            print(f"-> Edge Types: {stats['edge_types']}")

            # Verify Required Node Types
            required_node_types = {"paper", "author", "algorithm", "dataset", "problem", "topic", "metric", "limitation"}
            found_node_types = set(stats["node_types"].keys())
            missing_node_types = required_node_types - found_node_types
            print(f"-> Found Node Types: {found_node_types}")
            assert not missing_node_types, f"Missing required node types: {missing_node_types}"

            # Verify Required Relationships
            required_relations = {
                "uses_algorithm",
                "evaluates_dataset",
                "addresses_problem",
                "identifies_limitation",
                "shares_methodology",
                "cites"
            }
            found_relations = set(stats["edge_types"].keys())
            print(f"-> Found Edge Relations: {found_relations}")
            for req_rel in required_relations:
                assert req_rel in found_relations, f"Missing required relationship: '{req_rel}' in {found_relations}"

            # 4. Verify Distinction: Verified Citation vs Semantic / Shared Methodology
            print("\n[4/8] Testing Citation Verification vs Shared Methodology...")
            # P2 explicitly cited P1 in references
            citation_edges = [e for e in edges if e["relation"] == "cites"]
            print(f"-> Verified Citation Edges count: {len(citation_edges)}")
            assert len(citation_edges) >= 1, "Expected at least 1 verified citation edge"
            cit_edge = citation_edges[0]
            assert cit_edge["source"] == f"paper_{paper2.id}"
            assert cit_edge["target"] == f"paper_{paper1.id}"
            assert cit_edge["verified"] is True
            print(f"-> Confirmed Verified Citation: {cit_edge['source']} -> {cit_edge['target']} (verified={cit_edge['verified']})")

            # Check /api/graph/citations endpoint
            res_cits = await client.get(f"/api/graph/citations?paper_id={paper2.id}")
            assert res_cits.status_code == 200
            cit_records = res_cits.json()
            assert len(cit_records) >= 1
            print(f"-> Citations API returned verified citation: Citing '{cit_records[0]['citing_paper_title']}' -> Cited '{cit_records[0]['cited_paper_title']}'")

            # Verify shares_methodology is distinct
            shares_algo_edges = [e for e in edges if e["relation"] == "shares_methodology"]
            assert len(shares_algo_edges) >= 1, "Expected shares_methodology edges"
            print(f"-> Found {len(shares_algo_edges)} 'shares_methodology' edges (verified={shares_algo_edges[0]['verified']})")

            # 5. Test Filtering by Paper (Ego Graph)
            print("\n[5/8] Testing Graph Filtering by Paper (GET /api/graph/paper/{id})...")
            res_p1 = await client.get(f"/api/graph/paper/{paper1.id}")
            assert res_p1.status_code == 200
            p1_subgraph = res_p1.json()
            p1_node_ids = set(n["id"] for n in p1_subgraph["nodes"])
            assert f"paper_{paper1.id}" in p1_node_ids
            # Should have algorithms, datasets, problems of Paper 1
            p1_types = set(n["type"] for n in p1_subgraph["nodes"])
            print(f"-> Paper 1 Ego Subgraph nodes: {len(p1_node_ids)}, types: {p1_types}")
            assert "algorithm" in p1_types
            assert "dataset" in p1_types

            # 6. Test Filtering by Algorithm
            print("\n[6/8] Testing Graph Filtering by Algorithm (POST /api/graph/query?algorithm=CentralQ)...")
            filter_query = {
                "algorithm": "CentralQ",
                "include_citations": True,
                "include_methodology_sharing": True
            }
            res_filter_algo = await client.post(f"/api/graph/query?project_id={project.id}", json=filter_query)
            assert res_filter_algo.status_code == 200
            algo_subgraph = res_filter_algo.json()
            algo_node_ids = [n["id"] for n in algo_subgraph["nodes"]]
            print(f"-> Algorithm 'CentralQ' filtered nodes: {len(algo_node_ids)}")
            assert any("centralq" in nid.lower() for nid in algo_node_ids)
            assert f"paper_{paper1.id}" in algo_node_ids or f"paper_{paper2.id}" in algo_node_ids

            # 7. Test Filtering by Year
            print("\n[7/8] Testing Graph Filtering by Year (GET /api/graph/overview?year=2024)...")
            res_year = await client.get("/api/graph/overview?year=2024")
            assert res_year.status_code == 200
            year_subgraph = res_year.json()
            year_papers = [n for n in year_subgraph["nodes"] if n["type"] == "paper"]
            for yp in year_papers:
                assert yp["properties"]["publication_year"] == 2024, f"Expected 2024, got {yp['properties']['publication_year']}"
            print(f"-> Year 2024 filtered papers: {[yp['label'] for yp in year_papers]}")

            # 8. Test Filtering by Topic
            print("\n[8/8] Testing Graph Filtering by Topic (GET /api/graph/overview?topic=Multi-Agent)...")
            res_topic = await client.get("/api/graph/overview?topic=Multi-Agent")
            assert res_topic.status_code == 200
            topic_subgraph = res_topic.json()
            print(f"-> Topic 'Multi-Agent' nodes returned: {topic_subgraph['stats']['total_nodes']}")
            assert topic_subgraph["stats"]["total_nodes"] > 0

        print("\n" + "=" * 80)
        print("ALL RESEARCH KNOWLEDGE GRAPH AGENT TESTS PASSED SUCCESSFULLY!")
        print("=" * 80)

    finally:
        # Cleanup
        try:
            if project:
                p = db.query(ResearchProject).filter(ResearchProject.id == project.id).first()
                if p:
                    db.delete(p)
                    db.commit()
            if p1_path.exists():
                p1_path.unlink()
            if p2_path.exists():
                p2_path.unlink()
            if p3_path.exists():
                p3_path.unlink()
        except Exception as e:
            print(f"Cleanup error: {e}")
        db.close()

if __name__ == "__main__":
    asyncio.run(run_knowledge_graph_tests())
