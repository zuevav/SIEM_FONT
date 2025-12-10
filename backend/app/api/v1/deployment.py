"""
Agent Deployment API Endpoints
Handles agent package management, deployment configuration, and distribution
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime
import os
import shutil
import hashlib
import json
import logging

from app.api.deps import get_db, get_current_user, require_admin
from app.schemas.auth import CurrentUser
from app.models.agent import Agent, AgentPackage, AgentDeployment, AgentDeploymentTarget
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Storage path for agent packages
PACKAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "storage", "agent_packages")
os.makedirs(PACKAGES_DIR, exist_ok=True)


# ============================================================================
# AGENT PACKAGES
# ============================================================================

@router.get("/packages")
async def list_packages(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
    active_only: bool = True
):
    """List all agent packages"""
    query = db.query(AgentPackage)
    if active_only:
        query = query.filter(AgentPackage.IsActive == True)

    packages = query.order_by(AgentPackage.UploadedAt.desc()).all()

    return [
        {
            "package_id": p.PackageId,
            "version": p.Version,
            "file_name": p.FileName,
            "file_size": p.FileSize,
            "file_hash": p.FileHash,
            "platform": p.Platform,
            "architecture": p.Architecture,
            "description": p.Description,
            "release_notes": p.ReleaseNotes,
            "is_active": p.IsActive,
            "is_latest": p.IsLatest,
            "uploaded_by": p.UploadedBy,
            "uploaded_at": p.UploadedAt.isoformat() if p.UploadedAt else None,
            "download_url": f"/api/v1/deployment/packages/{p.PackageId}/download"
        }
        for p in packages
    ]


@router.post("/packages/upload")
async def upload_package(
    file: UploadFile = File(...),
    version: str = Form(...),
    platform: str = Form("windows"),
    architecture: str = Form("x64"),
    description: str = Form(None),
    release_notes: str = Form(None),
    set_as_latest: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin)
):
    """Upload a new agent package"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        # Check if version already exists
        existing = db.query(AgentPackage).filter(
            AgentPackage.Version == version,
            AgentPackage.Platform == platform,
            AgentPackage.Architecture == architecture,
            AgentPackage.IsActive == True
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Package version {version} for {platform}/{architecture} already exists"
            )

        # Create version directory
        version_dir = os.path.join(PACKAGES_DIR, version)
        os.makedirs(version_dir, exist_ok=True)

        # Save file
        file_path = os.path.join(version_dir, file.filename)
        file_content = await file.read()

        with open(file_path, "wb") as f:
            f.write(file_content)

        # Calculate hash
        file_hash = hashlib.sha256(file_content).hexdigest()

        # Unset previous latest
        if set_as_latest:
            db.query(AgentPackage).filter(
                AgentPackage.Platform == platform,
                AgentPackage.Architecture == architecture,
                AgentPackage.IsLatest == True
            ).update({"IsLatest": False})

        # Create package record
        package = AgentPackage(
            Version=version,
            FileName=file.filename,
            FileSize=len(file_content),
            FileHash=file_hash,
            Platform=platform,
            Architecture=architecture,
            Description=description,
            ReleaseNotes=release_notes,
            StoragePath=file_path,
            IsActive=True,
            IsLatest=set_as_latest,
            UploadedBy=current_user.username
        )

        db.add(package)
        db.commit()
        db.refresh(package)

        logger.info(f"Agent package {version} uploaded by {current_user.username}")

        return {
            "success": True,
            "package_id": package.PackageId,
            "version": package.Version,
            "file_hash": package.FileHash,
            "message": f"Package {version} uploaded successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading package: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload package: {str(e)}"
        )


@router.get("/packages/{package_id}/download")
async def download_package(
    package_id: int,
    db: Session = Depends(get_db)
):
    """Download agent package file"""
    package = db.query(AgentPackage).filter(AgentPackage.PackageId == package_id).first()

    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    if not package.StoragePath or not os.path.exists(package.StoragePath):
        raise HTTPException(status_code=404, detail="Package file not found")

    return FileResponse(
        path=package.StoragePath,
        filename=package.FileName,
        media_type="application/octet-stream"
    )


@router.delete("/packages/{package_id}")
async def delete_package(
    package_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin)
):
    """Delete (deactivate) an agent package"""
    package = db.query(AgentPackage).filter(AgentPackage.PackageId == package_id).first()

    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    # Check if package is used in active deployments
    active_deployments = db.query(AgentDeployment).filter(
        AgentDeployment.PackageId == package_id,
        AgentDeployment.Status == 'active'
    ).count()

    if active_deployments > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete package: used in {active_deployments} active deployment(s)"
        )

    package.IsActive = False
    db.commit()

    return {"success": True, "message": "Package deactivated"}


# ============================================================================
# DEPLOYMENTS
# ============================================================================

@router.get("/deployments")
async def list_deployments(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
    status_filter: Optional[str] = None
):
    """List all deployments"""
    query = db.query(AgentDeployment)

    if status_filter:
        query = query.filter(AgentDeployment.Status == status_filter)

    deployments = query.order_by(AgentDeployment.CreatedAt.desc()).all()

    return [
        {
            "deployment_id": d.DeploymentId,
            "name": d.Name,
            "description": d.Description,
            "package_id": d.PackageId,
            "package_version": d.package.Version if d.package else None,
            "deployment_mode": d.DeploymentMode,
            "target_ou": d.TargetOU,
            "server_url": d.ServerUrl,
            "network_path": d.NetworkPath,
            "enable_protection": d.EnableProtection,
            "install_watchdog": d.InstallWatchdog,
            "status": d.Status,
            "created_by": d.CreatedBy,
            "created_at": d.CreatedAt.isoformat() if d.CreatedAt else None,
            "activated_at": d.ActivatedAt.isoformat() if d.ActivatedAt else None,
            "total_targets": d.TotalTargets,
            "deployed_count": d.DeployedCount,
            "failed_count": d.FailedCount
        }
        for d in deployments
    ]


@router.post("/deployments")
async def create_deployment(
    deployment_data: dict,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin)
):
    """Create a new deployment configuration"""
    try:
        # Validate package exists
        package = db.query(AgentPackage).filter(
            AgentPackage.PackageId == deployment_data.get("package_id")
        ).first()

        if not package:
            raise HTTPException(status_code=400, detail="Package not found")

        deployment = AgentDeployment(
            Name=deployment_data.get("name", f"Deployment {datetime.now().strftime('%Y-%m-%d')}"),
            Description=deployment_data.get("description"),
            PackageId=deployment_data.get("package_id"),
            DeploymentMode=deployment_data.get("deployment_mode", "selected"),
            TargetOU=deployment_data.get("target_ou"),
            ServerUrl=deployment_data.get("server_url"),
            NetworkPath=deployment_data.get("network_path"),
            EnableProtection=deployment_data.get("enable_protection", True),
            InstallWatchdog=deployment_data.get("install_watchdog", True),
            Status="draft",
            CreatedBy=current_user.username
        )

        db.add(deployment)
        db.commit()
        db.refresh(deployment)

        # Add target computers if provided
        target_computers = deployment_data.get("target_computers", [])
        for computer in target_computers:
            target = AgentDeploymentTarget(
                DeploymentId=deployment.DeploymentId,
                ComputerName=computer.get("name") or computer,
                ComputerDN=computer.get("dn") if isinstance(computer, dict) else None,
                IPAddress=computer.get("ip") if isinstance(computer, dict) else None,
                Status="pending"
            )
            db.add(target)

        deployment.TotalTargets = len(target_computers)
        db.commit()

        logger.info(f"Deployment '{deployment.Name}' created by {current_user.username}")

        return {
            "success": True,
            "deployment_id": deployment.DeploymentId,
            "message": "Deployment created"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating deployment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deployments/{deployment_id}")
async def get_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin)
):
    """Get deployment details with targets"""
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.DeploymentId == deployment_id
    ).first()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    targets = db.query(AgentDeploymentTarget).filter(
        AgentDeploymentTarget.DeploymentId == deployment_id
    ).all()

    return {
        "deployment_id": deployment.DeploymentId,
        "name": deployment.Name,
        "description": deployment.Description,
        "package_id": deployment.PackageId,
        "package_version": deployment.package.Version if deployment.package else None,
        "deployment_mode": deployment.DeploymentMode,
        "target_ou": deployment.TargetOU,
        "server_url": deployment.ServerUrl,
        "network_path": deployment.NetworkPath,
        "enable_protection": deployment.EnableProtection,
        "install_watchdog": deployment.InstallWatchdog,
        "status": deployment.Status,
        "created_by": deployment.CreatedBy,
        "created_at": deployment.CreatedAt.isoformat() if deployment.CreatedAt else None,
        "activated_at": deployment.ActivatedAt.isoformat() if deployment.ActivatedAt else None,
        "total_targets": deployment.TotalTargets,
        "deployed_count": deployment.DeployedCount,
        "failed_count": deployment.FailedCount,
        "targets": [
            {
                "target_id": t.TargetId,
                "computer_name": t.ComputerName,
                "computer_dn": t.ComputerDN,
                "ip_address": t.IPAddress,
                "status": t.Status,
                "deployed_at": t.DeployedAt.isoformat() if t.DeployedAt else None,
                "deployed_version": t.DeployedVersion,
                "error_message": t.ErrorMessage
            }
            for t in targets
        ]
    }


@router.put("/deployments/{deployment_id}/targets")
async def update_deployment_targets(
    deployment_id: int,
    targets_data: dict,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin)
):
    """Update target computers for a deployment"""
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.DeploymentId == deployment_id
    ).first()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if deployment.Status == "active":
        raise HTTPException(status_code=400, detail="Cannot modify active deployment targets")

    # Remove existing targets
    db.query(AgentDeploymentTarget).filter(
        AgentDeploymentTarget.DeploymentId == deployment_id
    ).delete()

    # Add new targets
    target_computers = targets_data.get("computers", [])
    for computer in target_computers:
        target = AgentDeploymentTarget(
            DeploymentId=deployment_id,
            ComputerName=computer.get("name") if isinstance(computer, dict) else computer,
            ComputerDN=computer.get("dn") if isinstance(computer, dict) else None,
            IPAddress=computer.get("ip") if isinstance(computer, dict) else None,
            Status="pending"
        )
        db.add(target)

    deployment.TotalTargets = len(target_computers)
    deployment.DeploymentMode = targets_data.get("mode", "selected")
    db.commit()

    return {"success": True, "total_targets": len(target_computers)}


@router.post("/deployments/{deployment_id}/activate")
async def activate_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin)
):
    """Activate deployment - copy files to network share and generate GPO script"""
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.DeploymentId == deployment_id
    ).first()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if not deployment.NetworkPath:
        raise HTTPException(status_code=400, detail="Network path not configured")

    if not deployment.package:
        raise HTTPException(status_code=400, detail="Package not found")

    try:
        # Generate deployment script
        script_content = generate_deployment_script(deployment, db)

        deployment.Status = "active"
        deployment.ActivatedAt = datetime.utcnow()
        db.commit()

        logger.info(f"Deployment {deployment_id} activated by {current_user.username}")

        return {
            "success": True,
            "message": "Deployment activated",
            "script": script_content,
            "instructions": {
                "step1": f"Copy agent files to: {deployment.NetworkPath}",
                "step2": "Create GPO with the generated startup script",
                "step3": "Link GPO to target OUs or computers"
            }
        }

    except Exception as e:
        logger.error(f"Error activating deployment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deployments/{deployment_id}/pause")
async def pause_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin)
):
    """Pause an active deployment"""
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.DeploymentId == deployment_id
    ).first()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    deployment.Status = "paused"
    db.commit()

    return {"success": True, "message": "Deployment paused"}


@router.delete("/deployments/{deployment_id}")
async def delete_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin)
):
    """Delete a deployment"""
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.DeploymentId == deployment_id
    ).first()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    # Delete targets first
    db.query(AgentDeploymentTarget).filter(
        AgentDeploymentTarget.DeploymentId == deployment_id
    ).delete()

    db.delete(deployment)
    db.commit()

    return {"success": True, "message": "Deployment deleted"}


# ============================================================================
# DEPLOYMENT SCRIPT GENERATION
# ============================================================================

def generate_deployment_script(deployment: AgentDeployment, db: Session) -> str:
    """Generate PowerShell deployment script for GPO"""

    # Get target computers filter if in selected mode
    target_filter = ""
    if deployment.DeploymentMode == "selected":
        targets = db.query(AgentDeploymentTarget).filter(
            AgentDeploymentTarget.DeploymentId == deployment.DeploymentId
        ).all()

        if targets:
            computer_names = [t.ComputerName.upper() for t in targets]
            target_filter = f"""
# Список целевых компьютеров
$TargetComputers = @(
    {chr(10).join([f'    "{name}"' for name in computer_names])}
)

# Проверка, входит ли текущий компьютер в список целевых
if ($env:COMPUTERNAME.ToUpper() -notin $TargetComputers) {{
    Write-Log "Компьютер $env:COMPUTERNAME не в списке целевых - пропуск установки"
    exit 0
}}
"""

    script = f'''<#
.SYNOPSIS
    SIEM Agent Deployment Script (Auto-generated)
    Deployment: {deployment.Name}
    Version: {deployment.package.Version}
    Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

.DESCRIPTION
    Этот скрипт автоматически сгенерирован системой развертывания SIEM.
    Режим развертывания: {deployment.DeploymentMode}
    Защита агента: {"Включена" if deployment.EnableProtection else "Отключена"}
    Watchdog: {"Включен" if deployment.InstallWatchdog else "Отключен"}
#>

param(
    [string]$AgentPath = "{deployment.NetworkPath}",
    [string]$ServerUrl = "{deployment.ServerUrl}",
    [string]$InstallDir = "C:\\Program Files\\SIEM Agent",
    [bool]$EnableProtection = ${str(deployment.EnableProtection).lower()},
    [bool]$InstallWatchdog = ${str(deployment.InstallWatchdog).lower()}
)

$LogPath = "C:\\Windows\\Temp\\SIEMAgent_Deploy_{deployment.DeploymentId}.log"

function Write-Log {{
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Add-Content -Path $LogPath -Value $LogMessage
    Write-Host $LogMessage
}}

Write-Log "=========================================="
Write-Log "SIEM Agent Deployment Script"
Write-Log "Deployment ID: {deployment.DeploymentId}"
Write-Log "Target Version: {deployment.package.Version}"
Write-Log "Computer: $env:COMPUTERNAME"
Write-Log "=========================================="
{target_filter}
# Проверка прав администратора
$IsAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $IsAdmin) {{
    Write-Log "Требуются права администратора!" "ERROR"
    exit 1
}}

# Проверка доступности сетевого пути
if (-not (Test-Path $AgentPath)) {{
    Write-Log "Путь к агенту недоступен: $AgentPath" "ERROR"
    exit 1
}}

# Запуск основного скрипта развертывания
$DeployScript = Join-Path $AgentPath "Deploy-AgentGPO.ps1"
if (Test-Path $DeployScript) {{
    Write-Log "Запуск скрипта развертывания..."
    & $DeployScript -AgentPath $AgentPath -ServerUrl $ServerUrl -InstallDir $InstallDir -EnableProtection $EnableProtection -InstallWatchdog $InstallWatchdog
}} else {{
    Write-Log "Скрипт развертывания не найден: $DeployScript" "ERROR"
    exit 1
}}

Write-Log "Развертывание завершено"
'''

    return script


@router.get("/deployments/{deployment_id}/script")
async def get_deployment_script(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin)
):
    """Get deployment script for download/copy"""
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.DeploymentId == deployment_id
    ).first()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    script = generate_deployment_script(deployment, db)

    return {
        "script": script,
        "filename": f"Deploy-SIEM-{deployment.DeploymentId}.ps1"
    }


# ============================================================================
# DEPLOYMENT STATUS REPORTING (called by agents)
# ============================================================================

@router.post("/report-status")
async def report_deployment_status(
    status_data: dict,
    db: Session = Depends(get_db)
):
    """Report deployment status from agent (no auth required)"""
    try:
        deployment_id = status_data.get("deployment_id")
        computer_name = status_data.get("computer_name")
        status = status_data.get("status")  # success, failed
        version = status_data.get("version")
        error_message = status_data.get("error")

        if not deployment_id or not computer_name:
            raise HTTPException(status_code=400, detail="Missing required fields")

        # Find target
        target = db.query(AgentDeploymentTarget).filter(
            AgentDeploymentTarget.DeploymentId == deployment_id,
            AgentDeploymentTarget.ComputerName == computer_name.upper()
        ).first()

        if target:
            target.Status = status
            target.DeployedAt = datetime.utcnow()
            target.DeployedVersion = version
            target.ErrorMessage = error_message

            # Update deployment counters
            deployment = db.query(AgentDeployment).filter(
                AgentDeployment.DeploymentId == deployment_id
            ).first()

            if deployment:
                if status == "success":
                    deployment.DeployedCount = (deployment.DeployedCount or 0) + 1
                elif status == "failed":
                    deployment.FailedCount = (deployment.FailedCount or 0) + 1

            db.commit()

        return {"success": True}

    except Exception as e:
        logger.error(f"Error reporting deployment status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
