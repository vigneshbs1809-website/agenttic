import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status

from backend.app.models.entities import ResearchProject, ResearchPaper, ResearchGap, GeneratedReport
from backend.app.models.project_schemas import ProjectCreate, ProjectUpdate

logger = logging.getLogger(__name__)

class ProjectService:
    @staticmethod
    def create_project(db: Session, project_in: ProjectCreate) -> ResearchProject:
        """Creates a new Research Project with unique UUID and timestamps."""
        try:
            db_project = ResearchProject(
                title=project_in.title.strip(),
                description=project_in.description.strip() if project_in.description else None,
                domain=project_in.domain.strip() if project_in.domain else None,
                status=project_in.status or "active"
            )
            db.add(db_project)
            db.commit()
            db.refresh(db_project)
            return db_project
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error creating project: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while creating project: {str(e)}"
            )

    @staticmethod
    def get_project_by_id(db: Session, project_id: str) -> Optional[ResearchProject]:
        """Fetches a project by its primary key UUID."""
        return db.query(ResearchProject).filter(ResearchProject.id == project_id).first()

    @staticmethod
    def list_projects(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        status_filter: Optional[str] = None,
        domain_filter: Optional[str] = None
    ) -> List[ResearchProject]:
        """Lists projects with optional status/domain filtering and pagination."""
        query = db.query(ResearchProject)
        if status_filter:
            query = query.filter(ResearchProject.status == status_filter)
        if domain_filter:
            query = query.filter(ResearchProject.domain.ilike(f"%{domain_filter}%"))
        
        return query.order_by(ResearchProject.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def update_project(db: Session, project_id: str, project_in: ProjectUpdate) -> ResearchProject:
        """Updates project fields and triggers updated_at refresh."""
        db_project = ProjectService.get_project_by_id(db, project_id)
        if not db_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found."
            )

        try:
            if project_in.title is not None:
                db_project.title = project_in.title.strip()
            if project_in.description is not None:
                db_project.description = project_in.description.strip() if project_in.description else None
            if project_in.domain is not None:
                db_project.domain = project_in.domain.strip() if project_in.domain else None
            if project_in.status is not None:
                db_project.status = project_in.status

            db.commit()
            db.refresh(db_project)
            return db_project
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error updating project {project_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while updating project: {str(e)}"
            )

    @staticmethod
    def delete_project(db: Session, project_id: str) -> bool:
        """Deletes a project with cascade deletion of related papers, gaps, reports, and agent logs."""
        db_project = ProjectService.get_project_by_id(db, project_id)
        if not db_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found."
            )

        try:
            db.delete(db_project)
            db.commit()
            return True
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error deleting project {project_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while deleting project: {str(e)}"
            )

    @staticmethod
    def serialize_project(db: Session, project: ResearchProject) -> Dict[str, Any]:
        """Enriches project with live child relation counts."""
        paper_count = db.query(ResearchPaper).filter(ResearchPaper.project_id == project.id).count()
        gap_count = db.query(ResearchGap).filter(ResearchGap.project_id == project.id).count()
        report_count = db.query(GeneratedReport).filter(GeneratedReport.project_id == project.id).count()

        return {
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "domain": project.domain,
            "status": project.status,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "paper_count": paper_count,
            "gap_count": gap_count,
            "report_count": report_count
        }

project_service = ProjectService()

