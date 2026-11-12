import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.project_schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from backend.app.services.project_service import project_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["Research Projects"])

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db)
):
    """
    Requirement: POST /api/projects
    Creates a new research project and returns persistent entity with UUID.
    """
    project = project_service.create_project(db, project_in)
    return project_service.serialize_project(db, project)

@router.get("", response_model=List[ProjectResponse])
def list_projects(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    status: Optional[str] = Query(None, description="Filter by status (e.g. active, completed, archived)"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    db: Session = Depends(get_db)
):
    """
    Requirement: GET /api/projects
    Lists all research projects with optional status/domain filtering and relation counts.
    """
    projects = project_service.list_projects(
        db,
        skip=skip,
        limit=limit,
        status_filter=status,
        domain_filter=domain
    )
    return [project_service.serialize_project(db, p) for p in projects]

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Requirement: GET /api/projects/{project_id}
    Retrieves project details by unique UUID.
    """
    project = project_service.get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found."
        )
    return project_service.serialize_project(db, project)

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db)
):
    """
    Requirement: PUT /api/projects/{project_id}
    Updates project metadata and refreshes timestamps.
    """
    updated_project = project_service.update_project(db, project_id, project_in)
    return project_service.serialize_project(db, updated_project)

@router.delete("/{project_id}", status_code=status.HTTP_200_OK)
def delete_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Requirement: DELETE /api/projects/{project_id}
    Deletes project with cascade deletion of papers, gaps, reports, and agent history.
    """
    project_service.delete_project(db, project_id)
    return {
        "status": "success",
        "message": f"Project '{project_id}' and all associated entities were deleted successfully."
    }

