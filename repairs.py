import time
from fastapi import APIRouter, HTTPException
from backend.models import ApiResponse, RepairExecutionResponse
from backend.database import (
    get_issue_by_id,
    get_inspection_by_id,
    update_issue_status,
    save_repair,
    get_repair_by_issue_id
)
from backend.services.repair_executor import apply_repair_fix
from backend.services.validation import validate_repair
from backend.services.git_service import create_github_pull_request

router = APIRouter(prefix="/api/repairs", tags=["repairs"])

@router.post("/{issue_id}/execute", response_model=ApiResponse)
async def execute_repair(issue_id: str, project_path: str = None, create_branch: bool = False):
    issue = get_issue_by_id(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")

    inspection = get_inspection_by_id(issue.inspectionId)
    if not inspection:
        raise HTTPException(status_code=404, detail="Associated inspection record not found.")

    repair_id = f"rep-{int(time.time() * 1000)}"

    # 1. Apply code changes safely
    repair_res = apply_repair_fix(
        issue=issue,
        project_path=project_path,
        create_git_branch=create_branch
    )

    if not repair_res.success:
        save_repair(
            repair_id=repair_id,
            issue_id=issue.id,
            inspection_id=inspection.id,
            status="failed",
            project_path=project_path,
            branch_name=None,
            backup_path=None,
            before_shot=None,
            after_shot=None,
            details={"error": repair_res.error}
        )
        raise HTTPException(status_code=400, detail=f"Failed to apply repair: {repair_res.error}")

    # 2. Run automated validation
    repair_status, before_url, after_url, val_details = await validate_repair(
        issue=issue,
        inspection=inspection,
        before_screenshot_rel=issue.screenshotRef
    )

    # 3. Optional GitHub PR if requested
    pr_info = None
    if repair_res.branch_name:
        pr_info = await create_github_pull_request(
            branch_name=repair_res.branch_name,
            title=f"OmniSight Fix: {issue.title}",
            body=f"Automated UI healing for issue `{issue.id}`:\n\n{issue.description}\n\nValidation status: `{repair_status}`."
        )
        val_details["github_pr"] = pr_info

    # 4. Save repair history
    save_repair(
        repair_id=repair_id,
        issue_id=issue.id,
        inspection_id=inspection.id,
        status=repair_status,
        project_path=project_path,
        branch_name=repair_res.branch_name,
        backup_path=repair_res.backup_path,
        before_shot=before_url,
        after_shot=after_url,
        details=val_details
    )

    # 5. Update issue status
    new_issue_status = "resolved" if repair_status == "fixed" else "in-progress"
    update_issue_status(issue.id, status=new_issue_status, repair_status=repair_status)

    response_data = RepairExecutionResponse(
        issue_id=issue.id,
        repair_id=repair_id,
        status=repair_status,
        branch_name=repair_res.branch_name,
        before_screenshot=before_url,
        after_screenshot=after_url,
        validation_summary=val_details,
        message=f"Repair execution completed with status '{repair_status}'."
    )

    return ApiResponse(data=response_data.model_dump(), success=True)

@router.get("/{issue_id}", response_model=ApiResponse)
async def get_repair_details(issue_id: str):
    repair = get_repair_by_issue_id(issue_id)
    if not repair:
        return ApiResponse(data={"status": "pending"}, success=True)
    return ApiResponse(data=repair, success=True)
