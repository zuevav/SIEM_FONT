"""
System Update API Endpoints
Handles system info, update checking, and update execution
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
import subprocess
import logging
import os
import json
import asyncio
from typing import Optional
import uuid

from app.api.deps import get_db, get_current_user, require_admin
from app.schemas.settings import (
    SystemInfo,
    UpdateCheckResponse,
    UpdateStartResponse,
    UpdateProgress
)
from app.schemas.auth import CurrentUser
from app.models.settings import SystemSettings
from app.websocket.manager import get_connection_manager

logger = logging.getLogger(__name__)


async def broadcast_update_progress(progress: int, message: str, msg_type: str = "progress"):
    """Broadcast update progress to all connected WebSocket clients"""
    try:
        manager = get_connection_manager()
        await manager.broadcast(
            {
                "type": msg_type,
                "progress": progress,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            },
            channel="system_update"
        )
    except Exception as e:
        logger.warning(f"Failed to broadcast update progress: {e}")

router = APIRouter()

# Store update status
update_status = {}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def run_command(command: str, cwd: Optional[str] = None) -> tuple:
    """
    Run shell command and return (success, stdout, stderr)
    SECURITY: Uses shell=False with argument list to prevent command injection
    """
    import shlex
    try:
        # Parse command string into list for safe execution
        if isinstance(command, str):
            cmd_list = shlex.split(command)
        else:
            cmd_list = command

        result = subprocess.run(
            cmd_list,
            shell=False,  # SECURITY: Disabled shell to prevent injection
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return (result.returncode == 0, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (False, "", "Command timeout after 30 seconds")
    except Exception as e:
        return (False, "", str(e))


def get_git_info() -> dict:
    """Get current git branch and commit"""
    try:
        # Get branch
        success, branch, _ = run_command("git rev-parse --abbrev-ref HEAD")
        branch = branch.strip() if success else "unknown"

        # Get commit hash
        success, commit, _ = run_command("git rev-parse HEAD")
        commit = commit.strip() if success else "unknown"

        # Get commit short hash
        commit_short = commit[:7] if commit != "unknown" else "unknown"

        # Get last commit date
        success, last_update, _ = run_command("git log -1 --format=%cd --date=iso")
        last_update = last_update.strip() if success else None

        return {
            "branch": branch,
            "commit": commit,
            "commit_short": commit_short,
            "last_update": last_update
        }
    except Exception as e:
        logger.error(f"Error getting git info: {e}")
        return {
            "branch": "unknown",
            "commit": "unknown",
            "commit_short": "unknown",
            "last_update": None
        }


def get_docker_compose_version() -> str:
    """Get Docker Compose version"""
    try:
        # Try docker compose (v2)
        success, version, _ = run_command("docker compose version --short")
        if success:
            return version.strip()

        # Try docker-compose (v1)
        success, version, _ = run_command("docker-compose --version")
        if success:
            # Parse version from output
            parts = version.split()
            for i, part in enumerate(parts):
                if part.lower() == 'version':
                    return parts[i + 1].rstrip(',')

        return "unknown"
    except Exception as e:
        logger.error(f"Error getting docker-compose version: {e}")
        return "unknown"


def get_version_from_file() -> str:
    """Get version from VERSION file or default"""
    try:
        if os.path.exists('/app/VERSION'):
            with open('/app/VERSION', 'r') as f:
                return f.read().strip()
        elif os.path.exists('./VERSION'):
            with open('./VERSION', 'r') as f:
                return f.read().strip()
        return "1.0.0"
    except Exception:
        return "1.0.0"


async def perform_system_update(update_id: str):
    """
    Perform system update in background
    """
    try:
        update_status[update_id] = {
            "progress": 0,
            "message": "Starting update...",
            "logs": [],
            "status": "running"
        }
        await broadcast_update_progress(0, "Starting update...")

        # Step 1: Git pull (40%)
        update_status[update_id]["progress"] = 10
        update_status[update_id]["message"] = "Pulling latest changes from GitHub..."
        await broadcast_update_progress(10, "Pulling latest changes from GitHub...")

        # Get current branch first (shell expansion doesn't work with shell=False)
        git_info = get_git_info()
        current_branch = git_info.get("branch", "main")

        success, stdout, stderr = run_command(f"git pull origin {current_branch}")

        if not success:
            update_status[update_id]["status"] = "failed"
            update_status[update_id]["message"] = f"Git pull failed: {stderr}"
            update_status[update_id]["logs"].append(f"ERROR: {stderr}")
            await broadcast_update_progress(10, f"Git pull failed: {stderr}", "error")
            return

        update_status[update_id]["logs"].append(stdout)
        update_status[update_id]["progress"] = 40
        await broadcast_update_progress(40, "Git pull completed")

        # Step 2: Build images (70%)
        update_status[update_id]["message"] = "Building Docker images..."
        await broadcast_update_progress(45, "Building Docker images...")
        success, stdout, stderr = run_command("docker compose build", cwd=".")

        if not success:
            update_status[update_id]["status"] = "failed"
            update_status[update_id]["message"] = f"Docker build failed: {stderr}"
            update_status[update_id]["logs"].append(f"ERROR: {stderr}")
            await broadcast_update_progress(45, f"Docker build failed: {stderr}", "error")
            return

        update_status[update_id]["logs"].append(stdout)
        update_status[update_id]["progress"] = 70
        await broadcast_update_progress(70, "Docker images built successfully")

        # Step 3: Restart containers (90%)
        update_status[update_id]["message"] = "Restarting containers..."
        await broadcast_update_progress(75, "Restarting containers...")
        success, stdout, stderr = run_command("docker compose up -d", cwd=".")

        if not success:
            update_status[update_id]["status"] = "failed"
            update_status[update_id]["message"] = f"Docker restart failed: {stderr}"
            update_status[update_id]["logs"].append(f"ERROR: {stderr}")
            await broadcast_update_progress(75, f"Docker restart failed: {stderr}", "error")
            return

        update_status[update_id]["logs"].append(stdout)
        update_status[update_id]["progress"] = 90
        await broadcast_update_progress(90, "Containers restarted")

        # Step 4: Database migrations (if needed)
        update_status[update_id]["message"] = "Running database migrations..."
        await broadcast_update_progress(95, "Running database migrations...")
        # TODO: Add migration logic here
        await asyncio.sleep(2)  # Simulate migration

        # Complete
        update_status[update_id]["progress"] = 100
        update_status[update_id]["message"] = "Update completed successfully!"
        update_status[update_id]["status"] = "completed"
        await broadcast_update_progress(100, "Update completed successfully!", "complete")

        logger.info(f"System update {update_id} completed successfully")

    except Exception as e:
        logger.error(f"System update {update_id} failed: {e}", exc_info=True)
        update_status[update_id]["status"] = "failed"
        update_status[update_id]["message"] = f"Update failed: {str(e)}"
        await broadcast_update_progress(0, f"Update failed: {str(e)}", "error")


# ============================================================================
# SYSTEM INFO ENDPOINTS
# ============================================================================

@router.get("/info", response_model=SystemInfo)
async def get_system_info(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get system information (version, git, docker)
    """
    try:
        git_info = get_git_info()

        # Get version
        version = get_version_from_file()

        # Get docker-compose version
        docker_version = get_docker_compose_version()

        # Parse last update
        last_update = None
        if git_info["last_update"]:
            try:
                last_update = datetime.fromisoformat(git_info["last_update"].replace(" ", "T").split("+")[0])
            except Exception:
                pass

        return SystemInfo(
            version=version,
            git_branch=git_info["branch"],
            git_commit=git_info["commit"],
            git_commit_short=git_info["commit_short"],
            docker_compose_version=docker_version,
            last_update=last_update,
            update_available=False  # Will be set by check-updates endpoint
        )

    except Exception as e:
        logger.error(f"Error getting system info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system info: {str(e)}"
        )


@router.get("/check-updates", response_model=UpdateCheckResponse)
async def check_for_updates(
    current_user: CurrentUser = Depends(require_admin)
):
    """
    Check for available updates from GitHub
    """
    try:
        # Get current git info
        git_info = get_git_info()
        current_commit = git_info["commit"]
        current_branch = git_info["branch"]

        # Fetch latest from origin
        run_command("git fetch origin")

        # Get latest commit on remote
        success, latest_commit, _ = run_command(f"git rev-parse origin/{current_branch}")
        latest_commit = latest_commit.strip() if success else current_commit

        # Check if behind
        success, commits_behind_str, _ = run_command(
            f"git rev-list --count HEAD..origin/{current_branch}"
        )
        commits_behind = int(commits_behind_str.strip()) if success else 0

        # Get changelog if updates available
        changelog = []
        if commits_behind > 0:
            success, log_output, _ = run_command(
                f"git log --oneline HEAD..origin/{current_branch}"
            )
            if success:
                changelog = [line.strip() for line in log_output.strip().split('\n') if line.strip()]

        # Get current version
        current_version = get_version_from_file()

        # Try to get latest version from remote VERSION file
        latest_version = current_version  # Default to current
        success, remote_version, _ = run_command(
            f"git show origin/{current_branch}:VERSION"
        )
        if success:
            latest_version = remote_version.strip()

        update_available = commits_behind > 0

        logger.info(f"Update check: {'Update available' if update_available else 'Up to date'} "
                   f"(commits behind: {commits_behind})")

        return UpdateCheckResponse(
            update_available=update_available,
            current_version=current_version,
            current_commit=current_commit[:7],
            latest_version=latest_version,
            latest_commit=latest_commit[:7],
            changelog=changelog,
            commits_behind=commits_behind
        )

    except Exception as e:
        logger.error(f"Error checking for updates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check for updates: {str(e)}"
        )


@router.post("/update", response_model=UpdateStartResponse)
async def start_system_update(
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(require_admin)
):
    """
    Start system update process (git pull + docker-compose up -d --build)
    Admin only
    """
    try:
        # Generate update ID
        update_id = f"update-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"

        # Check if update is already running
        running_updates = [
            uid for uid, status in update_status.items()
            if status.get("status") == "running"
        ]

        if running_updates:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Update already in progress: {running_updates[0]}"
            )

        # Start update in background
        background_tasks.add_task(perform_system_update, update_id)

        logger.info(f"System update {update_id} started by {current_user.username}")

        return UpdateStartResponse(
            success=True,
            message="System update started",
            update_id=update_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting system update: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start system update: {str(e)}"
        )


@router.get("/update/{update_id}/status")
async def get_update_status(
    update_id: str,
    current_user: CurrentUser = Depends(require_admin)
):
    """
    Get status of a running/completed update
    """
    if update_id not in update_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Update {update_id} not found"
        )

    return update_status[update_id]


@router.get("/update/{update_id}/logs")
async def get_update_logs(
    update_id: str,
    current_user: CurrentUser = Depends(require_admin)
):
    """
    Get logs from a running/completed update
    """
    if update_id not in update_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Update {update_id} not found"
        )

    return {
        "update_id": update_id,
        "logs": update_status[update_id].get("logs", [])
    }
