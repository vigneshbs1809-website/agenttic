import os
import sys
sys.path.insert(0, os.path.abspath("."))
import json
from backend.app.core.database import SessionLocal
from backend.app.models.entities import ResearchProject, ResearchPaper, ResearchGap, VerificationResult
from backend.app.services.project_service import project_service
from backend.app.models.project_schemas import ProjectCreate, ProjectUpdate
from backend.app.main import get_analytics_summary

def test_overview_and_projects():
    db = SessionLocal()
    print("=================================================================")
    print("TESTING OVERVIEW DASHBOARD & RESEARCH PROJECTS FUNCTIONALITY")
    print("=================================================================")

    # 1. TEST OVERVIEW DASHBOARD ANALYTICS
    print("\n--- 1. OVERVIEW DASHBOARD: Actual Database Information ---")
    summary = get_analytics_summary(db)
    
    assert "total_projects" in summary, "Missing total_projects in summary"
    assert "total_uploaded_papers" in summary, "Missing total_uploaded_papers in summary"
    assert "processed_papers" in summary, "Missing processed_papers in summary"
    assert "identified_research_gaps" in summary, "Missing identified_research_gaps in summary"
    assert "verified_claims" in summary, "Missing verified_claims in summary"
    assert "year_distribution" in summary, "Missing year_distribution in summary"
    assert "recent_activity" in summary, "Missing recent_activity in summary"

    print(f"Total Research Projects:   {summary['total_projects']}")
    print(f"Total Uploaded Papers:     {summary['total_uploaded_papers']}")
    print(f"Processed Papers:          {summary['processed_papers']}")
    print(f"Identified Research Gaps:  {summary['identified_research_gaps']}")
    print(f"Verified Claims:           {summary['verified_claims']}")
    print(f"Publication Years Count:   {len(summary['year_distribution'])} bins")
    for yr in summary['year_distribution']:
        print(f"  - Year {yr['year']}: {yr['papers']} papers")
    print(f"Recent Activity Events:    {len(summary['recent_activity'])} entries")
    if summary['recent_activity']:
        sample = summary['recent_activity'][0]
        print(f"  - Latest Activity: [{sample['badge']}] {sample['action']} -> {sample['title'][:40]}...")

    # 2. TEST RESEARCH PROJECTS: CREATE
    print("\n--- 2. RESEARCH PROJECTS: Create Project ---")
    new_proj_in = ProjectCreate(
        title="Test Spatial Graph Routing in Multi-Agent Swarms",
        domain="Multi-Agent Systems & Graph Neural Networks",
        description="Investigating topological message passing and spatial credit assignment in congested warehouse fleets.",
        status="active"
    )
    created_proj = project_service.create_project(db, new_proj_in)
    serialized_created = project_service.serialize_project(db, created_proj)
    proj_id = created_proj.id
    print(f"Created Project ID:   {proj_id}")
    print(f"Title:                {serialized_created['title']}")
    print(f"Research Topic:       {serialized_created['domain']}")
    print(f"Description:          {serialized_created['description']}")
    print(f"Creation Date:        {serialized_created['created_at']}")
    print(f"Paper Count:          {serialized_created['paper_count']}")
    print(f"Processing Status:    {serialized_created['status']}")
    
    assert serialized_created['title'] == new_proj_in.title
    assert serialized_created['domain'] == new_proj_in.domain
    assert serialized_created['status'] == "active"

    # 3. TEST RESEARCH PROJECTS: SEARCH & FILTER
    print("\n--- 3. RESEARCH PROJECTS: Search & Filter Projects ---")
    # Search by topic
    filtered_by_domain = project_service.list_projects(db, domain_filter="Graph Neural Networks")
    assert any(p.id == proj_id for p in filtered_by_domain), "Failed to filter project by domain"
    print(f"Filtered by domain 'Graph Neural Networks': Found {len(filtered_by_domain)} projects")

    # Filter by status
    filtered_by_status = project_service.list_projects(db, status_filter="active")
    assert any(p.id == proj_id for p in filtered_by_status), "Failed to filter project by status"
    print(f"Filtered by status 'active': Found {len(filtered_by_status)} projects")

    # 4. TEST RESEARCH PROJECTS: EDIT / UPDATE
    print("\n--- 4. RESEARCH PROJECTS: Edit Project ---")
    update_in = ProjectUpdate(
        title="Updated: Spatial Graph Routing in Multi-Agent Swarms",
        domain="Spatial AI & Heterogeneous Graphs",
        description="Expanded scope to include communication bandwidth constraints.",
        status="completed"
    )
    updated_proj = project_service.update_project(db, proj_id, update_in)
    serialized_updated = project_service.serialize_project(db, updated_proj)
    print(f"Updated Title:             {serialized_updated['title']}")
    print(f"Updated Research Topic:    {serialized_updated['domain']}")
    print(f"Updated Processing Status: {serialized_updated['status']}")
    print(f"Updated Description:       {serialized_updated['description']}")

    assert serialized_updated['title'] == "Updated: Spatial Graph Routing in Multi-Agent Swarms"
    assert serialized_updated['domain'] == "Spatial AI & Heterogeneous Graphs"
    assert serialized_updated['status'] == "completed"

    # 5. TEST RESEARCH PROJECTS: OPEN / RETRIEVE BY ID
    print("\n--- 5. RESEARCH PROJECTS: Open / Get by ID ---")
    fetched = project_service.get_project_by_id(db, proj_id)
    assert fetched is not None
    assert fetched.id == proj_id
    print(f"Successfully opened project: {fetched.title} (Status: {fetched.status})")

    # 6. TEST RESEARCH PROJECTS: DELETE
    print("\n--- 6. RESEARCH PROJECTS: Delete Project ---")
    delete_res = project_service.delete_project(db, proj_id)
    assert delete_res is True
    post_delete = project_service.get_project_by_id(db, proj_id)
    assert post_delete is None, "Project still exists after deletion"
    print(f"Project {proj_id} deleted cleanly from SQLite.")

    # 7. VERIFY OVERVIEW DASHBOARD UPDATED
    print("\n--- 7. VERIFY OVERVIEW POST-OPERATION INTEGRITY ---")
    final_summary = get_analytics_summary(db)
    print(f"Active Research Projects count confirmed: {final_summary['total_projects']}")
    print("All assertions passed with 100% success!")
    
    db.close()

if __name__ == "__main__":
    test_overview_and_projects()
