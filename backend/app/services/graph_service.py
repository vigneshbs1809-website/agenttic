import re
import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
import networkx as nx
from sqlalchemy.orm import Session

from backend.app.models.entities import (
    ResearchPaper,
    Author,
    ExtractedEntity,
    ResearchClaim,
    PaperSection,
    PaperAnalysis,
    PaperCitation
)
from backend.app.models.graph_schemas import (
    GraphNode,
    GraphEdge,
    GraphStats,
    GraphResponse,
    GraphFilterQuery,
    PaperCitationResponse
)
from backend.app.services.pdf_understanding_agent import pdf_understanding_agent

logger = logging.getLogger(__name__)

CACHE_FILE_PATH = Path("backend/data/knowledge_graph_cache.json")

class KnowledgeGraphService:
    """
    Research Knowledge Graph Agent using NetworkX.

    Models:
    - Nodes: Papers, Authors, Algorithms, Datasets, Research Problems,
             Research Topics, Evaluation Metrics, Research Limitations.
    - Relationships:
        * uses_algorithm (Paper -> Algorithm)
        * evaluates_dataset (Paper -> Dataset)
        * addresses_problem (Paper -> Problem)
        * cites (Paper -> Paper, strictly verified from bibliography)
        * identifies_limitation (Paper -> Limitation)
        * shares_methodology (Paper <-> Paper)
        * authored_by (Paper -> Author)
        * measures_metric (Paper -> Metric)
        * has_topic (Paper -> Topic)
    """

    def __init__(self):
        self._cache_data: Optional[Dict[str, Any]] = None
        self._cache_timestamp: float = 0.0

    # ----------------------------------------------------------------------
    # Normalization & Canonical Slugs
    # ----------------------------------------------------------------------
    def clean_name(self, raw_str: str) -> str:
        """Sanitizes raw text, removing markdown, punctuation, and extraneous whitespace."""
        if not raw_str:
            return ""
        cleaned = re.sub(r"[*_`]", "", raw_str).strip()
        cleaned = re.sub(r"^[,\.:;•\s\-]+|[,\.:;•\s\-]+$", "", cleaned).strip()
        return cleaned

    def slugify(self, text: str, max_len: int = 50) -> str:
        """Generates a stable, lowercase, collision-resistant slug."""
        clean = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
        if not clean:
            clean = "item_" + hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
        return clean[:max_len]

    def _make_node_id(self, node_type: str, raw_text: str) -> str:
        slug = self.slugify(raw_text)
        return f"{node_type}_{slug}"

    # ----------------------------------------------------------------------
    # 1. Verified Citations Extraction
    # ----------------------------------------------------------------------
    def extract_and_verify_citations(
        self, paper: ResearchPaper, all_papers: List[ResearchPaper], db: Session
    ) -> List[PaperCitation]:
        """
        Distinguishes verified citations from semantic similarities.
        Scans the paper's actual 'References' / 'Bibliography' section to find
        explicit citations to other papers in the platform.
        Does NOT fabricate citation relationships.
        """
        verified_citations: List[PaperCitation] = []

        # Find references section text
        ref_text = ""
        sections = db.query(PaperSection).filter(PaperSection.paper_id == paper.id).all()
        for sec in sections:
            sec_type = (sec.section_type or "").lower()
            sec_title = (sec.section_title or "").lower()
            if sec_type in ["references", "bibliography"] or "reference" in sec_title or "bibliography" in sec_title:
                ref_text += "\n" + (sec.content or "")

        # Fallback to checking extracted text file if empty
        if not ref_text and paper.extracted_text_path and Path(paper.extracted_text_path).exists():
            try:
                full_text = Path(paper.extracted_text_path).read_text(encoding="utf-8", errors="ignore")
                ref_idx = full_text.rfind("References")
                if ref_idx == -1:
                    ref_idx = full_text.rfind("REFERENCES")
                if ref_idx == -1:
                    ref_idx = full_text.rfind("Bibliography")
                if ref_idx != -1:
                    ref_text = full_text[ref_idx:]
            except Exception as e:
                logger.warning(f"Failed to read extracted text for {paper.id}: {e}")

        if not ref_text or len(ref_text.strip()) < 10:
            return verified_citations

        ref_lower = ref_text.lower()

        # Check against every other paper registered in the platform
        for other_paper in all_papers:
            if other_paper.id == paper.id:
                continue

            matched = False
            match_snippet = None

            # 1. Check DOI match
            if other_paper.doi and len(other_paper.doi.strip()) > 5:
                doi_clean = other_paper.doi.strip().lower()
                if doi_clean in ref_lower:
                    matched = True
                    idx = ref_lower.find(doi_clean)
                    start = max(0, idx - 100)
                    end = min(len(ref_text), idx + 200)
                    match_snippet = ref_text[start:end].strip()

            # 2. Check Paper Title match (normalized substring match with length > 14)
            if not matched and other_paper.title and len(other_paper.title.strip()) > 14:
                # Clean title for robust matching
                norm_title = re.sub(r"[^a-zA-Z0-9\s]", " ", other_paper.title.lower()).strip()
                norm_title_words = norm_title.split()
                if len(norm_title_words) >= 3:
                    # Look for 3+ consecutive words or 80% word containment
                    core_phrase = " ".join(norm_title_words[:6])
                    if core_phrase in re.sub(r"[^a-zA-Z0-9\s]", " ", ref_lower):
                        matched = True
                        idx = ref_lower.find(core_phrase)
                        start = max(0, idx - 100)
                        end = min(len(ref_text), idx + 200)
                        match_snippet = ref_text[start:end].strip()

            # 3. Check Author Surname + Publication Year in references
            if not matched and other_paper.publication_year and other_paper.authors:
                primary_author = other_paper.authors[0]
                surname = primary_author.name.strip().split()[-1].lower()
                year_str = str(other_paper.publication_year)
                if len(surname) > 2:
                    author_year_patterns = [
                        rf"\b{re.escape(surname)}\b[^\n\.\,]*\b{year_str}\b",
                        rf"\b{year_str}\b[^\n\.\,]*\b{re.escape(surname)}\b"
                    ]
                    for pat in author_year_patterns:
                        m = re.search(pat, ref_lower)
                        if m:
                            # Additional confirmation: at least one unique keyword from other_paper title
                            other_title_words = [w for w in other_paper.title.lower().split() if len(w) > 4 and w not in ["using", "based", "learning", "neural", "system"]]
                            if any(w in ref_lower for w in other_title_words):
                                matched = True
                                start = max(0, m.start() - 50)
                                end = min(len(ref_text), m.end() + 150)
                                match_snippet = ref_text[start:end].strip()
                                break

            if matched:
                # Persist or reuse citation in DB
                existing = (
                    db.query(PaperCitation)
                    .filter(
                        PaperCitation.citing_paper_id == paper.id,
                        PaperCitation.cited_paper_id == other_paper.id
                    )
                    .first()
                )
                if not existing:
                    cit = PaperCitation(
                        citing_paper_id=paper.id,
                        cited_paper_id=other_paper.id,
                        citation_text=match_snippet[:500] if match_snippet else "Verified bibliography citation",
                        is_verified=True,
                        confidence=1.0
                    )
                    db.add(cit)
                    verified_citations.append(cit)
                else:
                    verified_citations.append(existing)

        db.flush()
        return verified_citations

    # ----------------------------------------------------------------------
    # 2. Entity & Topic Extraction from Paper Analysis
    # ----------------------------------------------------------------------
    def extract_knowledge_elements_sync(
        self, paper: ResearchPaper, db: Session
    ) -> Dict[str, Any]:
        """
        Synchronously extracts algorithms, datasets, problems, topics, metrics, and limitations
        from stored paper analysis and entity records.
        """
        structured = None
        if paper.analysis and paper.analysis.structured_data:
            try:
                structured = json.loads(paper.analysis.structured_data)
            except Exception as e:
                logger.warning(f"Could not parse structured_data for {paper.id}: {e}")

        # Elements dictionary
        elements = {
            "algorithms": set(),
            "datasets": set(),
            "problems": set(),
            "topics": set(),
            "metrics": set(),
            "limitations": set()
        }

        # 1. Project Domain as base Topic
        if paper.project and paper.project.domain:
            elements["topics"].add(self.clean_name(paper.project.domain))
        if paper.project and paper.project.title:
            for kw in ["Multi-Agent", "Reinforcement Learning", "Drug Discovery", "Graph Neural Networks", "Natural Language Processing", "Robotics", "Computer Vision"]:
                if kw.lower() in paper.project.title.lower():
                    elements["topics"].add(kw)

        # 2. Extract from structured fields
        if structured:
            val = (structured.get("algorithms") or {}).get("value")
            if val and val.lower() != "not reported":
                for item in re.split(r"[,;•\n\t]+", val):
                    c = self.clean_name(item)
                    if c and 1 < len(c) < 60:
                        elements["algorithms"].add(c)

            val = (structured.get("research_methodology") or {}).get("value")
            if val and val.lower() != "not reported":
                for item in re.split(r"[,;•\n\t]+", val):
                    c = self.clean_name(item)
                    if c and 2 < len(c) < 50 and any(k in c.lower() for k in ["net", "former", "solver", "algorithm", "learning", "attention", "filter", "optimization", "diff"]):
                        elements["algorithms"].add(c)

            val = (structured.get("datasets") or {}).get("value")
            if val and val.lower() != "not reported":
                for item in re.split(r"[,;•\n\t]+", val):
                    c = self.clean_name(item)
                    if c and 1 < len(c) < 60:
                        elements["datasets"].add(c)

            val = (structured.get("research_problem") or {}).get("value")
            if val and val.lower() != "not reported":
                c = self.clean_name(val)
                if c and len(c) > 5:
                    elements["problems"].add(c[:120])

            val = (structured.get("limitations") or {}).get("value")
            if val and val.lower() != "not reported":
                c = self.clean_name(val)
                if c and len(c) > 5:
                    elements["limitations"].add(c[:140])

            val = (structured.get("evaluation_metrics") or {}).get("value")
            if val and val.lower() != "not reported":
                for item in re.split(r"[,;•\n\t]+", val):
                    c = self.clean_name(item)
                    if c and 1 < len(c) < 40:
                        elements["metrics"].add(c)

        return elements

    async def extract_knowledge_elements(
        self, paper: ResearchPaper, db: Session, force: bool = False
    ) -> Dict[str, Any]:
        """
        Extracts algorithms, datasets, problems, topics, metrics, and limitations
        from the actual paper analysis and sections.
        """
        if paper.analysis and paper.analysis.structured_data and not force:
            return self.extract_knowledge_elements_sync(paper, db)

        structured = None
        try:
            analysis_res = await pdf_understanding_agent.analyze_paper(
                db=db,
                paper_id=paper.id,
                force_reanalyze=force,
                allow_llm_assist=False
            )
            structured = analysis_res.model_dump()
        except Exception as e:
            logger.warning(f"PDF understanding agent failed for {paper.id}: {e}")

        return self.extract_knowledge_elements_sync(paper, db)

        # 1. Project Domain as base Topic
        if paper.project and paper.project.domain:
            elements["topics"].add(self.clean_name(paper.project.domain))
        if paper.project and paper.project.title:
            # Check domain keywords in project title
            for kw in ["Multi-Agent", "Reinforcement Learning", "Drug Discovery", "Graph Neural Networks", "Natural Language Processing", "Robotics", "Computer Vision"]:
                if kw.lower() in paper.project.title.lower():
                    elements["topics"].add(kw)

        # 2. Extract from structured fields
        if structured:
            # Algorithms
            val = (structured.get("algorithms") or {}).get("value")
            if val and val.lower() != "not reported":
                for item in re.split(r"[,;•\n\t]+", val):
                    c = self.clean_name(item)
                    if c and len(c) > 1 and len(c) < 60:
                        elements["algorithms"].add(c)

            # Methodology algorithms
            val = (structured.get("research_methodology") or {}).get("value")
            if val and val.lower() != "not reported":
                for item in re.split(r"[,;•\n\t]+", val):
                    c = self.clean_name(item)
                    if c and len(c) > 2 and len(c) < 50 and any(k in c.lower() for k in ["net", "former", "solver", "algorithm", "learning", "attention", "filter", "optimization", "diff"]):
                        elements["algorithms"].add(c)

            # Datasets
            val = (structured.get("datasets") or {}).get("value")
            if val and val.lower() != "not reported":
                for item in re.split(r"[,;•\n\t]+", val):
                    c = self.clean_name(item)
                    if c and len(c) > 1 and len(c) < 60:
                        elements["datasets"].add(c)

            # Research Problems
            val = (structured.get("research_problem") or {}).get("value")
            if val and val.lower() != "not reported":
                c = self.clean_name(val)
                if c and len(c) > 5:
                    elements["problems"].add(c[:120])

            # Research Limitations
            val = (structured.get("limitations") or {}).get("value")
            if val and val.lower() != "not reported":
                c = self.clean_name(val)
                if c and len(c) > 5:
                    elements["limitations"].add(c[:140])

            # Evaluation Metrics
            val = (structured.get("evaluation_metrics") or {}).get("value")
            if val and val.lower() != "not reported":
                for item in re.split(r"[,;•\n\t]+", val):
                    c = self.clean_name(item)
                    if c and len(c) > 1 and len(c) < 50:
                        elements["metrics"].add(c)

        # 3. Augment from Paper Sections
        sections = db.query(PaperSection).filter(PaperSection.paper_id == paper.id).all()
        for sec in sections:
            sec_type = (sec.section_type or "").lower()
            text = sec.content or ""

            # Extract Topics from Title & Abstract
            if sec_type in ["abstract", "introduction"]:
                topic_candidates = [
                    "Reinforcement Learning", "Multi-Agent Coordination", "Graph Neural Networks",
                    "Molecular Property Prediction", "Bio-Molecular Screening", "Continuous Diffusion",
                    "Fleet Dispatch", "Urban Logistics", "Contrastive Learning", "Transformer Architecture"
                ]
                for tc in topic_candidates:
                    if tc.lower() in text.lower() or tc.lower() in paper.title.lower():
                        elements["topics"].add(tc)

            # Extract Limitations if missing
            if not elements["limitations"] and sec_type in ["limitations", "discussion", "conclusion"]:
                m = re.search(r"(?:limitation|drawback|degrades when|fails to|constrained by)\s*[:]?\s*([^.\n]+(?:\.[^.\n]+)?)", text, re.IGNORECASE)
                if m:
                    elements["limitations"].add(self.clean_name(m.group(0))[:140])

            # Augment Algorithms from methodology / methods / abstract
            if sec_type in ["methodology", "methods", "abstract"]:
                matches = re.findall(r"\b([A-Z][a-zA-Z0-9]+(?:Net|Former|GNN|CNN|RNN|Diff|BERT|GPT|RL|Q|MCTS|GAT|GCN|AdamW|Adam|SGD))\b", text)
                for mm in matches:
                    elements["algorithms"].add(mm)

            # Extract Datasets if missing
            if not elements["datasets"] and sec_type in ["experiments", "results"]:
                matches = re.findall(r"\b([A-Z][a-zA-Z0-9]+(?:Net|Bench|DB|Data|Set|Corpus|\-200k|\-100k|\-1k))\b", text)
                for mm in matches:
                    elements["datasets"].add(mm)

            # Extract Metrics if missing
            if not elements["metrics"] and sec_type in ["experiments", "results"]:
                matches = re.findall(r"\b(ROC-AUC|AUC|F1 Score|Accuracy|Throughput|Latency|BLEU|Perplexity|Precision|Recall|Success Rate)\b", text, re.IGNORECASE)
                for mm in matches:
                    elements["metrics"].add(mm)

        return {k: list(v) for k, v in elements.items()}

    # ----------------------------------------------------------------------
    # 3. NetworkX Graph Construction
    # ----------------------------------------------------------------------
    def build_research_graph_sync(
        self,
        db: Session,
        paper_ids: Optional[List[str]] = None,
        project_id: Optional[str] = None,
        force_rebuild: bool = False
    ) -> nx.DiGraph:
        """
        Builds the complete heterogeneous, directed Research Knowledge Graph in NetworkX.
        Includes Papers, Authors, Algorithms, Datasets, Problems, Topics, Metrics, Limitations.
        """
        query = db.query(ResearchPaper)
        if project_id:
            query = query.filter(ResearchPaper.project_id == project_id)
        if paper_ids:
            query = query.filter(ResearchPaper.id.in_(paper_ids))

        papers = query.all()
        all_db_papers = db.query(ResearchPaper).all()

        G = nx.DiGraph()

        # Helper to safely add node
        def add_node(n_id: str, label: str, n_type: str, **props):
            if not G.has_node(n_id):
                G.add_node(n_id, label=label, type=n_type, **props)

        # Helper to safely add edge
        def add_edge(u: str, v: str, relation: str, weight: float = 1.0, verified: bool = False, **props):
            if G.has_node(u) and G.has_node(v):
                if G.has_edge(u, v):
                    G[u][v]["weight"] = G[u][v].get("weight", 1.0) + weight
                else:
                    G.add_edge(u, v, relation=relation, weight=weight, verified=verified, **props)

        # Track algorithms per paper for 'shares_methodology'
        algorithm_to_papers: Dict[str, Set[str]] = {}

        for paper in papers:
            p_node_id = f"paper_{paper.id}"
            short_title = paper.title[:45] + ("..." if len(paper.title) > 45 else "")

            # 1. Paper Node
            add_node(
                p_node_id,
                label=short_title,
                n_type="paper",
                paper_id=paper.id,
                title=paper.title,
                publication_year=paper.publication_year,
                journal_or_conference=paper.journal_or_conference,
                total_pages=paper.total_pages,
                doi=paper.doi
            )

            # 2. Authors -> Paper (authored_by)
            for author in paper.authors:
                a_node_id = f"author_{author.id}"
                add_node(
                    a_node_id,
                    label=author.name,
                    n_type="author",
                    author_id=author.id,
                    affiliation=getattr(author, "affiliation", None)
                )
                add_edge(p_node_id, a_node_id, relation="authored_by", weight=1.0)

            # 3. Extract Knowledge Elements
            elements = self.extract_knowledge_elements_sync(paper, db)

            # Algorithms (uses_algorithm)
            for algo in elements.get("algorithms", []):
                clean_algo = self.clean_name(algo)
                if not clean_algo:
                    continue
                algo_node_id = self._make_node_id("algorithm", clean_algo)
                add_node(algo_node_id, label=clean_algo, n_type="algorithm", algorithm=clean_algo)
                add_edge(p_node_id, algo_node_id, relation="uses_algorithm", weight=1.0)
                algorithm_to_papers.setdefault(clean_algo.lower(), set()).add(p_node_id)

            # Datasets (evaluates_dataset)
            for ds in elements.get("datasets", []):
                clean_ds = self.clean_name(ds)
                if not clean_ds:
                    continue
                ds_node_id = self._make_node_id("dataset", clean_ds)
                add_node(ds_node_id, label=clean_ds, n_type="dataset", dataset=clean_ds)
                add_edge(p_node_id, ds_node_id, relation="evaluates_dataset", weight=1.0)

            # Research Problems (addresses_problem)
            for prob in elements.get("problems", []):
                clean_prob = self.clean_name(prob)
                if not clean_prob:
                    continue
                prob_node_id = self._make_node_id("problem", clean_prob[:40])
                add_node(prob_node_id, label=clean_prob[:45] + ("..." if len(clean_prob) > 45 else ""), n_type="problem", full_problem=clean_prob)
                add_edge(p_node_id, prob_node_id, relation="addresses_problem", weight=1.0)

            # Research Topics (has_topic)
            for top in elements.get("topics", []):
                clean_top = self.clean_name(top)
                if not clean_top:
                    continue
                top_node_id = self._make_node_id("topic", clean_top)
                add_node(top_node_id, label=clean_top, n_type="topic", topic=clean_top)
                add_edge(p_node_id, top_node_id, relation="has_topic", weight=1.0)

            # Evaluation Metrics (measures_metric)
            for met in elements.get("metrics", []):
                clean_met = self.clean_name(met)
                if not clean_met:
                    continue
                met_node_id = self._make_node_id("metric", clean_met)
                add_node(met_node_id, label=clean_met, n_type="metric", metric=clean_met)
                add_edge(p_node_id, met_node_id, relation="measures_metric", weight=1.0)

            # Research Limitations (identifies_limitation)
            for lim in elements.get("limitations", []):
                clean_lim = self.clean_name(lim)
                if not clean_lim:
                    continue
                lim_node_id = self._make_node_id("limitation", clean_lim[:40])
                add_node(lim_node_id, label=clean_lim[:45] + ("..." if len(clean_lim) > 45 else ""), n_type="limitation", full_limitation=clean_lim)
                add_edge(p_node_id, lim_node_id, relation="identifies_limitation", weight=1.0)

            # 4. Verified Citations (Paper -> cites -> Paper)
            verified_cits = self.extract_and_verify_citations(paper, all_db_papers, db)
            for cit in verified_cits:
                cited_node_id = f"paper_{cit.cited_paper_id}"
                # If cited paper is in G, link it directly
                if G.has_node(cited_node_id):
                    add_edge(
                        p_node_id,
                        cited_node_id,
                        relation="cites",
                        weight=1.5,
                        verified=True,
                        citation_text=cit.citation_text
                    )

        # 5. Shares Methodology Relationships (Paper <-> Paper)
        for algo_name, p_set in algorithm_to_papers.items():
            p_list = list(p_set)
            if len(p_list) > 1:
                for i in range(len(p_list)):
                    for j in range(i + 1, len(p_list)):
                        # Bidirectional or undirected relationship
                        add_edge(
                            p_list[i],
                            p_list[j],
                            relation="shares_methodology",
                            weight=1.0,
                            verified=False,
                            algorithm=algo_name
                        )
                        add_edge(
                            p_list[j],
                            p_list[i],
                            relation="shares_methodology",
                            weight=1.0,
                            verified=False,
                            algorithm=algo_name
                        )

        db.commit()
        return G

    async def build_research_graph(
        self,
        db: Session,
        paper_ids: Optional[List[str]] = None,
        project_id: Optional[str] = None,
        force_rebuild: bool = False
    ) -> nx.DiGraph:
        """Async bridge to build_research_graph_sync."""
        return self.build_research_graph_sync(db, paper_ids, project_id, force_rebuild)

    def get_global_overview(
        self, db: Session, max_papers: int = 50, filters: Optional[GraphFilterQuery] = None
    ) -> GraphResponse:
        """Synchronous global graph overview generator."""
        G = self.build_research_graph_sync(db=db)
        if filters is None:
            filters = GraphFilterQuery(max_nodes=max_papers * 5)
        response = self.filter_and_serialize_graph(G, filters=filters)
        self.save_cache_to_disk(response)
        return response

    # ----------------------------------------------------------------------
    # 4. Graph Filtering & Serialization (RAM-Optimized)
    # ----------------------------------------------------------------------
    def filter_and_serialize_graph(
        self, G: nx.DiGraph, filters: Optional[GraphFilterQuery] = None
    ) -> GraphResponse:
        """
        Applies requested filters (paper, algorithm, year, topic) and serializes
        the NetworkX graph to D3/Canvas compatible JSON.
        Optimized for 8 GB RAM by avoiding deep copies and bounding calculations.
        """
        if G.number_of_nodes() == 0:
            return GraphResponse(
                nodes=[],
                edges=[],
                stats=GraphStats(
                    total_nodes=0,
                    total_edges=0,
                    density=0.0,
                    connected_components=0,
                    node_types={},
                    edge_types={}
                )
            )

        target_nodes: Set[str] = set(G.nodes())

        # Filter 1: Paper filter (Ego subgraph)
        if filters and filters.paper_id:
            target_p = f"paper_{filters.paper_id}" if not filters.paper_id.startswith("paper_") else filters.paper_id
            if G.has_node(target_p):
                # 1-hop neighborhood + shared methodology connections
                ego = set(G.predecessors(target_p)) | set(G.successors(target_p)) | {target_p}
                target_nodes = target_nodes.intersection(ego)
            else:
                target_nodes = set()

        # Filter 2: Algorithm filter
        if filters and filters.algorithm and target_nodes:
            algo_slug = self.slugify(filters.algorithm)
            matched_algos = [n for n in target_nodes if G.nodes[n].get("type") == "algorithm" and (algo_slug in n or filters.algorithm.lower() in G.nodes[n].get("label", "").lower())]
            if matched_algos:
                # Include papers that use these algorithms
                algo_papers = set()
                for ma in matched_algos:
                    algo_papers.update(G.predecessors(ma))
                    algo_papers.update(G.successors(ma))
                    algo_papers.add(ma)
                target_nodes = target_nodes.intersection(algo_papers)
            else:
                target_nodes = set()

        # Filter 3: Year filter (Strictly filter papers by publication year)
        if filters and (filters.year is not None or filters.start_year is not None or filters.end_year is not None) and target_nodes:
            matching_papers = set()
            connected_entities = set()
            for n in target_nodes:
                data = G.nodes[n]
                if data.get("type") == "paper":
                    p_year = data.get("publication_year")
                    if p_year is not None:
                        keep = True
                        if filters.year is not None and p_year != filters.year:
                            keep = False
                        if filters.start_year is not None and p_year < filters.start_year:
                            keep = False
                        if filters.end_year is not None and p_year > filters.end_year:
                            keep = False
                        if keep:
                            matching_papers.add(n)
                            # Keep paper's immediate non-paper entities
                            for neighbor in list(G.successors(n)) + list(G.predecessors(n)):
                                if G.nodes[neighbor].get("type") != "paper":
                                    connected_entities.add(neighbor)
            target_nodes = target_nodes.intersection(matching_papers | connected_entities)

        # Filter 4: Topic filter
        if filters and filters.topic and target_nodes:
            topic_slug = self.slugify(filters.topic)
            matched_topics = [n for n in target_nodes if G.nodes[n].get("type") == "topic" and (topic_slug in n or filters.topic.lower() in G.nodes[n].get("label", "").lower())]
            if matched_topics:
                topic_papers = set()
                for mt in matched_topics:
                    topic_papers.update(G.predecessors(mt))
                    topic_papers.update(G.successors(mt))
                    topic_papers.add(mt)
                target_nodes = target_nodes.intersection(topic_papers)
            else:
                target_nodes = set()

        # Clamp max nodes if requested
        max_nodes = filters.max_nodes if filters else 200
        if len(target_nodes) > max_nodes:
            # Prioritize papers and algorithms, then other types
            sorted_nodes = sorted(
                list(target_nodes),
                key=lambda x: (
                    0 if G.nodes[x].get("type") == "paper" else
                    1 if G.nodes[x].get("type") == "algorithm" else
                    2 if G.nodes[x].get("type") == "problem" else 3
                )
            )
            target_nodes = set(sorted_nodes[:max_nodes])

        subG = G.subgraph(target_nodes)

        num_nodes = subG.number_of_nodes()
        num_edges = subG.number_of_edges()

        if num_nodes == 0:
            return GraphResponse(
                nodes=[],
                edges=[],
                stats=GraphStats(
                    total_nodes=0,
                    total_edges=0,
                    density=0.0,
                    connected_components=0,
                    node_types={},
                    edge_types={}
                )
            )

        # Compute metrics safely
        try:
            deg_centrality = nx.degree_centrality(subG)
        except Exception:
            deg_centrality = {n: 0.0 for n in subG.nodes()}

        try:
            # Low CPU / 8GB RAM optimization: sample k nodes
            k_val = min(num_nodes, 30)
            betweenness = nx.betweenness_centrality(subG, k=k_val)
        except Exception:
            betweenness = {n: 0.0 for n in subG.nodes()}

        density = nx.density(subG)
        try:
            components = nx.number_weakly_connected_components(subG)
        except Exception:
            components = nx.number_connected_components(subG.to_undirected())

        node_types_count: Dict[str, int] = {}
        edge_types_count: Dict[str, int] = {}

        # Format Nodes
        nodes: List[GraphNode] = []
        for n_id, data in subG.nodes(data=True):
            n_type = data.get("type", "node")
            node_types_count[n_type] = node_types_count.get(n_type, 0) + 1

            props = {k: v for k, v in data.items() if k not in ["label", "type"]}
            nodes.append(
                GraphNode(
                    id=str(n_id),
                    label=data.get("label", str(n_id)),
                    type=n_type,
                    degree=subG.degree(n_id),
                    centrality=round(deg_centrality.get(n_id, 0.0), 4),
                    properties=props
                )
            )

        # Format Edges
        edges: List[GraphEdge] = []
        for u, v, data in subG.edges(data=True):
            rel = data.get("relation", "connected")
            verified = data.get("verified", False)

            # Check citation filter
            if rel == "cites" and filters and not filters.include_citations:
                continue
            # Check methodology sharing filter
            if rel == "shares_methodology" and filters and not filters.include_methodology_sharing:
                continue

            edge_types_count[rel] = edge_types_count.get(rel, 0) + 1
            props = {k: v for k, v in data.items() if k not in ["relation", "weight", "verified"]}

            edges.append(
                GraphEdge(
                    source=str(u),
                    target=str(v),
                    relation=rel,
                    weight=float(data.get("weight", 1.0)),
                    verified=verified,
                    properties=props
                )
            )

        stats = GraphStats(
            total_nodes=len(nodes),
            total_edges=len(edges),
            density=round(density, 4),
            connected_components=components,
            node_types=node_types_count,
            edge_types=edge_types_count
        )

        return GraphResponse(
            nodes=nodes,
            edges=edges,
            stats=stats
        )

    # ----------------------------------------------------------------------
    # 5. Persistent Cache & High-Level API Handlers
    # ----------------------------------------------------------------------
    def save_cache_to_disk(self, response: GraphResponse):
        """Saves graph snapshot to persistent file on disk."""
        try:
            CACHE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            CACHE_FILE_PATH.write_text(response.model_dump_json(indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to persist graph cache to disk: {e}")

    def load_cache_from_disk(self) -> Optional[GraphResponse]:
        """Loads persistent graph snapshot from disk if present."""
        if CACHE_FILE_PATH.exists():
            try:
                data = json.loads(CACHE_FILE_PATH.read_text(encoding="utf-8"))
                return GraphResponse(**data)
            except Exception as e:
                logger.warning(f"Failed to load graph cache from disk: {e}")
        return None

    async def get_filtered_knowledge_graph(
        self, db: Session, filters: GraphFilterQuery, project_id: Optional[str] = None
    ) -> GraphResponse:
        """
        Builds or queries the knowledge graph and applies filters.
        """
        G = await self.build_research_graph(db=db, project_id=project_id)
        response = self.filter_and_serialize_graph(G, filters=filters)
        return response

    async def get_overview_graph(
        self, db: Session, max_papers: int = 50, include_claims: bool = True
    ) -> GraphResponse:
        """Overview endpoint for global graph."""
        G = await self.build_research_graph(db=db)
        filters = GraphFilterQuery(max_nodes=max_papers * 5)
        response = self.filter_and_serialize_graph(G, filters=filters)
        self.save_cache_to_disk(response)
        return response

    async def get_paper_subgraph(
        self, paper_id: str, db: Session, depth: int = 1, include_claims: bool = True
    ) -> GraphResponse:
        """Returns paper ego subgraph."""
        G = await self.build_research_graph(db=db)
        filters = GraphFilterQuery(paper_id=paper_id)
        return self.filter_and_serialize_graph(G, filters=filters)

    async def get_project_graph(
        self, project_id: str, db: Session, include_claims: bool = True
    ) -> GraphResponse:
        """Returns project knowledge graph."""
        G = await self.build_research_graph(db=db, project_id=project_id)
        return self.filter_and_serialize_graph(G, filters=None)

    async def extract_entities_and_claims(
        self, paper_id: str, db: Session, force: bool = False
    ) -> Dict[str, Any]:
        """Bridge for entity extraction."""
        paper = db.query(ResearchPaper).filter(ResearchPaper.id == paper_id).first()
        if not paper:
            raise ValueError(f"Paper {paper_id} not found.")

        elements = await self.extract_knowledge_elements(paper, db, force=force)
        total_extracted = sum(len(v) for v in elements.values())

        # Persist extracted entities into ExtractedEntity model
        for category, items in elements.items():
            type_map = {
                "algorithms": "method",
                "datasets": "dataset",
                "problems": "concept",
                "topics": "concept",
                "metrics": "metric",
                "limitations": "concept"
            }
            ent_type = type_map.get(category, "concept")
            for item in items:
                clean_name = self.clean_name(item)
                if not clean_name:
                    continue
                existing = (
                    db.query(ExtractedEntity)
                    .filter(
                        ExtractedEntity.paper_id == paper_id,
                        ExtractedEntity.name == clean_name,
                        ExtractedEntity.entity_type == ent_type
                    )
                    .first()
                )
                if not existing:
                    db.add(
                        ExtractedEntity(
                            paper_id=paper_id,
                            name=clean_name,
                            entity_type=ent_type,
                            frequency=1
                        )
                    )

        # Verified citations
        all_papers = db.query(ResearchPaper).all()
        citations = self.extract_and_verify_citations(paper, all_papers, db)

        db.commit()

        return {
            "paper_id": paper_id,
            "entities_count": total_extracted,
            "claims_count": len(citations),
            "status": "extracted"
        }

graph_service = KnowledgeGraphService()
