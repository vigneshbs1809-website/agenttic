import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.orchestrator_schemas import (
    WorkflowRunRequest,
    WorkflowStatusResponse,
    RunStageRequest,
    StageStatus
)
from backend.app.agents.orchestrator import orchestrator, STAGE_DEFINITIONS

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/orchestrator",
    tags=["Multi-Agent Orchestrator"]
)

@router.get("/stages")
def get_available_stages():
    """Returns the ordered list of workflow stages and their responsible agents."""
    return [
        {
            "stage_id": s_id,
            "stage_name": s_name,
            "agent_name": a_name
        }
        for s_id, s_name, a_name in STAGE_DEFINITIONS
    ]

@router.post("/run", response_model=WorkflowStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_complete_workflow(
    request: WorkflowRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    One-Button Complete Workflow Execution:
    Launches sequential execution of all 8 agents from Topic/PDFs to Final Research Dossier.
    Runs asynchronously in the background and returns tracking handle.
    """
    try:
        # 1. Initialize workflow state
        state = orchestrator.create_workflow(db=db, request=request)
        workflow_id = state["workflow_id"]

        # 2. Launch execution in background task (sequential execution protected by internal lock)
        background_tasks.add_task(orchestrator.run_workflow, workflow_id)

        # 3. Return immediate status response
        status_res = orchestrator.get_workflow_status(workflow_id)
        if not status_res:
            raise HTTPException(status_code=500, detail="Failed to initialize workflow status.")
        return status_res

    except Exception as e:
        logger.error(f"Failed to start workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start multi-agent workflow: {str(e)}"
        )

@router.post("/resume/{workflow_id}", response_model=WorkflowStatusResponse)
async def resume_workflow(
    workflow_id: str,
    background_tasks: BackgroundTasks
):
    """
    Resumes a failed or interrupted workflow without repeating already completed stages.
    """
    status_res = orchestrator.get_workflow_status(workflow_id)
    if not status_res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Workflow '{workflow_id}' not found.")

    background_tasks.add_task(orchestrator.run_workflow, workflow_id, True)
    return status_res

@router.get("/status/{workflow_id}", response_model=WorkflowStatusResponse)
def get_workflow_status(workflow_id: str):
    """
    Polls real-time workflow status, stage progress, execution logs, and final report.
    Guarantees honest progress percentage based strictly on completed stages.
    """
    status_res = orchestrator.get_workflow_status(workflow_id)
    if not status_res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Workflow '{workflow_id}' not found.")
    return status_res

@router.post("/run-stage")
async def run_individual_stage(request: RunStageRequest):
    """
    Executes a single agent stage individually without running the full workflow.
    """
    try:
        return await orchestrator.run_individual_stage(request)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error running individual stage: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/history")
def get_workflow_history():
    """Returns list of recent multi-agent workflow executions."""
    history = []
    for w_id in sorted(orchestrator._active_workflows.keys(), reverse=True):
        st = orchestrator.get_workflow_status(w_id)
        if st:
            history.append({
                "workflow_id": st.workflow_id,
                "project_id": st.project_id,
                "topic": st.topic,
                "status": st.status.value,
                "completed_stages": st.completed_stages,
                "total_stages": st.total_stages,
                "progress_percent": st.progress_percent,
                "created_at": st.created_at,
                "updated_at": st.updated_at
            })
    return history

