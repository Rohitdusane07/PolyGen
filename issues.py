from fastapi import APIRouter, HTTPException
from backend.models import ApiResponse, Issue, ApproveFixRequest, RejectFixRequest
from backend.database import (
    list_all_issues,
    get_issue_by_id,
    update_issue_status,
    get_repair_by_issue_id
)

router = APIRouter(prefix="/api/issues", tags=["issues"])

@router.get("", response_model=ApiResponse)
async def get_all_issues_endpoint():
    issues = list_all_issues()
    return ApiResponse(data=[i.model_dump() for i in issues], success=True)

@router.get("/{issue_id}", response_model=ApiResponse)
async def get_issue_endpoint(issue_id: str):
    issue = get_issue_by_id(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")
    return ApiResponse(data=issue.model_dump(), success=True)

@router.post("/{issue_id}/approve", response_model=ApiResponse)
async def approve_issue_fix(issue_id: str, req: ApproveFixRequest = None):
    issue = get_issue_by_id(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")

    update_issue_status(issue_id, status="in-progress", repair_status="pending")
    updated = get_issue_by_id(issue_id)
    return ApiResponse(data=updated.model_dump(), success=True, message=f"Fix approved for '{issue.title}'. Repair queued.")

@router.post("/{issue_id}/reject", response_model=ApiResponse)
async def reject_issue_fix(issue_id: str, req: RejectFixRequest = None):
    issue = get_issue_by_id(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")

    update_issue_status(issue_id, status="rejected", repair_status="still-present")
    updated = get_issue_by_id(issue_id)
    return ApiResponse(data=updated.model_dump(), success=True, message=f"Fix rejected for '{issue.title}'.")

@router.get("/{issue_id}/repair-status", response_model=ApiResponse)
async def get_repair_status_endpoint(issue_id: str):
    issue = get_issue_by_id(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")
    
    repair = get_repair_by_issue_id(issue_id)
    status = issue.repairStatus or (repair.get("status") if repair else "pending")
    return ApiResponse(data={"status": status}, success=True)
