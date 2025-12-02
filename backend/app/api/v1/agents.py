"""
Agents API Endpoints
Handles agent registration, heartbeat, inventory, and management
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text
from typing import List, Optional
from datetime import datetime, timedelta
import json
import logging
from uuid import UUID, uuid4

from app.api.deps import get_db, get_current_user, require_analyst, require_admin, PaginationParams
from app.schemas.agent import (
    AgentRegister,
    AgentUpdate,
    AgentResponse,
    AgentDetail,
    AgentHeartbeat,
    SoftwareInventory,
    ServicesInventory,
    AgentStatistics
)
from app.schemas.auth import CurrentUser
from app.models.agent import Agent, InstalledSoftware, WindowsService, SoftwareRegistry, AssetChange
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# AGENT REGISTRATION AND HEARTBEAT
# ============================================================================

@router.post("/register", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def register_agent(
    agent_data: AgentRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new agent or update existing agent
    This endpoint doesn't require authentication (agent registration only)
    """
    try:
        # Check if agent already exists by hostname
        existing_agent = db.query(Agent).filter(Agent.Hostname == agent_data.hostname).first()

        if existing_agent:
            # Update existing agent
            existing_agent.FQDN = agent_data.fqdn
            existing_agent.IPAddress = agent_data.ip_address
            existing_agent.MACAddress = agent_data.mac_address
            existing_agent.OSVersion = agent_data.os_version
            existing_agent.OSBuild = agent_data.os_build
            existing_agent.OSArchitecture = agent_data.os_architecture
            existing_agent.Domain = agent_data.domain
            existing_agent.OrganizationalUnit = agent_data.organizational_unit
            existing_agent.Manufacturer = agent_data.manufacturer
            existing_agent.Model = agent_data.model
            existing_agent.SerialNumber = agent_data.serial_number
            existing_agent.CPUModel = agent_data.cpu_model
            existing_agent.CPUCores = agent_data.cpu_cores
            existing_agent.TotalRAM_MB = agent_data.total_ram_mb
            existing_agent.TotalDisk_GB = agent_data.total_disk_gb
            existing_agent.AgentVersion = agent_data.agent_version
            existing_agent.Status = 'online'
            existing_agent.LastSeen = datetime.utcnow()

            db.commit()
            db.refresh(existing_agent)

            logger.info(f"Agent re-registered: {existing_agent.Hostname} ({existing_agent.AgentId})")

            return AgentResponse.from_orm(existing_agent)

        # Create new agent
        new_agent = Agent(
            AgentId=str(uuid4()),
            Hostname=agent_data.hostname,
            FQDN=agent_data.fqdn,
            IPAddress=agent_data.ip_address,
            MACAddress=agent_data.mac_address,
            OSVersion=agent_data.os_version,
            OSBuild=agent_data.os_build,
            OSArchitecture=agent_data.os_architecture,
            Domain=agent_data.domain,
            OrganizationalUnit=agent_data.organizational_unit,
            Manufacturer=agent_data.manufacturer,
            Model=agent_data.model,
            SerialNumber=agent_data.serial_number,
            CPUModel=agent_data.cpu_model,
            CPUCores=agent_data.cpu_cores,
            TotalRAM_MB=agent_data.total_ram_mb,
            TotalDisk_GB=agent_data.total_disk_gb,
            AgentVersion=agent_data.agent_version,
            Status='online',
            LastSeen=datetime.utcnow(),
            RegisteredAt=datetime.utcnow(),
            CriticalityLevel=agent_data.criticality_level or 'medium',
            Location=agent_data.location,
            Owner=agent_data.owner,
            Tags=json.dumps(agent_data.tags) if agent_data.tags else None
        )

        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)

        logger.info(f"New agent registered: {new_agent.Hostname} ({new_agent.AgentId})")

        return AgentResponse.from_orm(new_agent)

    except Exception as e:
        db.rollback()
        logger.error(f"Error registering agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register agent: {str(e)}"
        )


@router.post("/heartbeat")
async def agent_heartbeat(
    heartbeat: AgentHeartbeat,
    db: Session = Depends(get_db)
):
    """
    Agent heartbeat - updates agent status and last seen time
    No authentication required (agent heartbeat only)
    """
    try:
        agent = db.query(Agent).filter(Agent.AgentId == str(heartbeat.agent_id)).first()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {heartbeat.agent_id} not found"
            )

        # Update agent status
        agent.Status = heartbeat.status
        agent.LastSeen = datetime.utcnow()

        if heartbeat.ip_address:
            agent.IPAddress = heartbeat.ip_address

        if heartbeat.agent_version:
            agent.AgentVersion = heartbeat.agent_version

        if heartbeat.last_reboot:
            agent.LastReboot = heartbeat.last_reboot

        db.commit()

        return {
            "success": True,
            "agent_id": str(agent.AgentId),
            "status": agent.Status,
            "message": "Heartbeat received"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing heartbeat: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process heartbeat: {str(e)}"
        )


# ============================================================================
# AGENT INVENTORY
# ============================================================================

@router.post("/{agent_id}/software")
async def update_software_inventory(
    agent_id: str,
    inventory: SoftwareInventory,
    db: Session = Depends(get_db)
):
    """
    Update software inventory for an agent
    Called by agent during inventory scan
    """
    try:
        # Verify agent exists
        agent = db.query(Agent).filter(Agent.AgentId == agent_id).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )

        # Mark all current software as inactive first
        db.query(InstalledSoftware).filter(
            and_(
                InstalledSoftware.AgentId == agent_id,
                InstalledSoftware.IsActive == True
            )
        ).update({
            "IsActive": False,
            "RemovedAt": datetime.utcnow()
        })

        # Process each software item
        added_count = 0
        updated_count = 0

        for software in inventory.software_list:
            # Check if software exists in registry
            registry_entry = db.query(SoftwareRegistry).filter(
                SoftwareRegistry.Name == software.name
            ).first()

            # Find or create installed software entry
            existing = db.query(InstalledSoftware).filter(
                and_(
                    InstalledSoftware.AgentId == agent_id,
                    InstalledSoftware.Name == software.name,
                    InstalledSoftware.Version == software.version
                )
            ).first()

            if existing:
                # Reactivate if was previously removed
                existing.IsActive = True
                existing.LastSeenAt = datetime.utcnow()
                existing.RemovedAt = None
                updated_count += 1
            else:
                # Create new entry
                new_software = InstalledSoftware(
                    AgentId=agent_id,
                    SoftwareId=registry_entry.SoftwareId if registry_entry else None,
                    Name=software.name,
                    Version=software.version,
                    Publisher=software.publisher,
                    InstallDate=software.install_date,
                    InstallLocation=software.install_location,
                    UninstallString=software.uninstall_string,
                    EstimatedSize_KB=software.estimated_size_kb,
                    IsActive=True,
                    FirstSeenAt=datetime.utcnow(),
                    LastSeenAt=datetime.utcnow()
                )
                db.add(new_software)
                added_count += 1

        # Update agent last inventory time
        agent.LastInventory = datetime.utcnow()

        db.commit()

        logger.info(f"Updated software inventory for {agent.Hostname}: {added_count} added, {updated_count} updated")

        return {
            "success": True,
            "agent_id": agent_id,
            "added": added_count,
            "updated": updated_count,
            "total": len(inventory.software_list)
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating software inventory: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update software inventory: {str(e)}"
        )


@router.post("/{agent_id}/services")
async def update_services_inventory(
    agent_id: str,
    inventory: ServicesInventory,
    db: Session = Depends(get_db)
):
    """
    Update Windows services inventory for an agent
    """
    try:
        # Verify agent exists
        agent = db.query(Agent).filter(Agent.AgentId == agent_id).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )

        # Mark all current services as inactive
        db.query(WindowsService).filter(
            and_(
                WindowsService.AgentId == agent_id,
                WindowsService.IsActive == True
            )
        ).update({
            "IsActive": False
        })

        # Process each service
        added_count = 0
        updated_count = 0

        for service in inventory.services_list:
            existing = db.query(WindowsService).filter(
                and_(
                    WindowsService.AgentId == agent_id,
                    WindowsService.ServiceName == service.service_name
                )
            ).first()

            if existing:
                # Update existing service
                existing.DisplayName = service.display_name
                existing.Status = service.status
                existing.StartType = service.start_type
                existing.ServiceAccount = service.service_account
                existing.ExecutablePath = service.executable_path
                existing.IsActive = True
                existing.LastSeenAt = datetime.utcnow()
                updated_count += 1
            else:
                # Create new service entry
                new_service = WindowsService(
                    AgentId=agent_id,
                    ServiceName=service.service_name,
                    DisplayName=service.display_name,
                    Status=service.status,
                    StartType=service.start_type,
                    ServiceAccount=service.service_account,
                    ExecutablePath=service.executable_path,
                    IsActive=True,
                    FirstSeenAt=datetime.utcnow(),
                    LastSeenAt=datetime.utcnow()
                )
                db.add(new_service)
                added_count += 1

        db.commit()

        logger.info(f"Updated services inventory for {agent.Hostname}: {added_count} added, {updated_count} updated")

        return {
            "success": True,
            "agent_id": agent_id,
            "added": added_count,
            "updated": updated_count,
            "total": len(inventory.services_list)
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating services inventory: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update services inventory: {str(e)}"
        )


# ============================================================================
# AGENT MANAGEMENT (AUTHENTICATED)
# ============================================================================

@router.get("", response_model=dict)
async def get_agents(
    status: Optional[str] = Query(None, description="Filter by status (online, offline, error)"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    criticality: Optional[str] = Query(None, description="Filter by criticality level"),
    search: Optional[str] = Query(None, description="Search in hostname, FQDN, IP"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get list of agents with filtering and pagination
    """
    try:
        query = db.query(Agent)

        # Filters
        if status:
            query = query.filter(Agent.Status == status)
        if domain:
            query = query.filter(Agent.Domain == domain)
        if criticality:
            query = query.filter(Agent.CriticalityLevel == criticality)

        if search:
            query = query.filter(
                or_(
                    Agent.Hostname.ilike(f"%{search}%"),
                    Agent.FQDN.ilike(f"%{search}%"),
                    Agent.IPAddress.ilike(f"%{search}%")
                )
            )

        # Get total count
        total = query.count()

        # Apply pagination
        agents = query.order_by(Agent.LastSeen.desc()).offset(offset).limit(limit).all()

        return {
            "agents": [AgentResponse.from_orm(agent) for agent in agents],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total
        }

    except Exception as e:
        logger.error(f"Error retrieving agents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve agents: {str(e)}"
        )


@router.get("/{agent_id}", response_model=AgentDetail)
async def get_agent_detail(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get detailed agent information
    """
    agent = db.query(Agent).filter(Agent.AgentId == agent_id).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    return AgentDetail.from_orm(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    update_data: AgentUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst)
):
    """
    Update agent metadata (tags, location, owner, criticality)
    Requires analyst role
    """
    try:
        agent = db.query(Agent).filter(Agent.AgentId == agent_id).first()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )

        # Update fields
        if update_data.tags is not None:
            agent.Tags = json.dumps(update_data.tags)
        if update_data.location is not None:
            agent.Location = update_data.location
        if update_data.owner is not None:
            agent.Owner = update_data.owner
        if update_data.criticality_level is not None:
            agent.CriticalityLevel = update_data.criticality_level

        db.commit()
        db.refresh(agent)

        logger.info(f"Agent {agent.Hostname} updated by {current_user.username}")

        return AgentResponse.from_orm(agent)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent: {str(e)}"
        )


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin)
):
    """
    Delete an agent (admin only)
    NOTE: This will also cascade delete all related events, software, services
    """
    try:
        agent = db.query(Agent).filter(Agent.AgentId == agent_id).first()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )

        hostname = agent.Hostname

        # Delete agent (cascade will handle related records)
        db.delete(agent)
        db.commit()

        logger.warning(f"Agent {hostname} ({agent_id}) deleted by {current_user.username}")

        return {
            "success": True,
            "message": f"Agent {hostname} deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete agent: {str(e)}"
        )


# ============================================================================
# AGENT STATISTICS
# ============================================================================

@router.get("/stats/overview", response_model=AgentStatistics)
async def get_agent_statistics(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get agent statistics for dashboard
    """
    try:
        # Total agents
        total_agents = db.query(func.count(Agent.AgentId)).scalar()

        # Agents by status
        online_agents = db.query(func.count(Agent.AgentId)).filter(Agent.Status == 'online').scalar()
        offline_agents = db.query(func.count(Agent.AgentId)).filter(Agent.Status == 'offline').scalar()
        error_agents = db.query(func.count(Agent.AgentId)).filter(Agent.Status == 'error').scalar()

        # Agents by criticality
        critical_agents = db.query(func.count(Agent.AgentId)).filter(Agent.CriticalityLevel == 'critical').scalar()

        # Agents by domain (top 10)
        agents_by_domain = {}
        domain_stats = db.query(
            Agent.Domain,
            func.count(Agent.AgentId).label('count')
        ).group_by(Agent.Domain).order_by(func.count(Agent.AgentId).desc()).limit(10).all()

        for domain, count in domain_stats:
            agents_by_domain[domain or 'No Domain'] = count

        # Agents by OS version (top 10)
        agents_by_os = {}
        os_stats = db.query(
            Agent.OSVersion,
            func.count(Agent.AgentId).label('count')
        ).group_by(Agent.OSVersion).order_by(func.count(Agent.AgentId).desc()).limit(10).all()

        for os_version, count in os_stats:
            agents_by_os[os_version or 'Unknown'] = count

        # Recently registered (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_agents = db.query(func.count(Agent.AgentId)).filter(
            Agent.RegisteredAt >= week_ago
        ).scalar()

        return AgentStatistics(
            total_agents=total_agents or 0,
            online_agents=online_agents or 0,
            offline_agents=offline_agents or 0,
            error_agents=error_agents or 0,
            critical_agents=critical_agents or 0,
            agents_by_domain=agents_by_domain,
            agents_by_os=agents_by_os,
            recent_registrations=recent_agents or 0
        )

    except Exception as e:
        logger.error(f"Error getting agent statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent statistics: {str(e)}"
        )


# ============================================================================
# SOFTWARE INVENTORY QUERIES
# ============================================================================

@router.get("/{agent_id}/software", response_model=List[dict])
async def get_agent_software(
    agent_id: str,
    include_inactive: bool = Query(False, description="Include removed software"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get software inventory for specific agent
    """
    # Verify agent exists
    agent = db.query(Agent).filter(Agent.AgentId == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    # Query software
    query = db.query(InstalledSoftware).filter(InstalledSoftware.AgentId == agent_id)

    if not include_inactive:
        query = query.filter(InstalledSoftware.IsActive == True)

    software_list = query.order_by(InstalledSoftware.Name).all()

    return [
        {
            "install_id": sw.InstallId,
            "name": sw.Name,
            "version": sw.Version,
            "publisher": sw.Publisher,
            "install_date": sw.InstallDate,
            "is_active": sw.IsActive,
            "first_seen": sw.FirstSeenAt,
            "last_seen": sw.LastSeenAt
        }
        for sw in software_list
    ]


@router.get("/{agent_id}/services", response_model=List[dict])
async def get_agent_services(
    agent_id: str,
    include_inactive: bool = Query(False, description="Include stopped services"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get Windows services for specific agent
    """
    # Verify agent exists
    agent = db.query(Agent).filter(Agent.AgentId == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    # Query services
    query = db.query(WindowsService).filter(WindowsService.AgentId == agent_id)

    if not include_inactive:
        query = query.filter(WindowsService.IsActive == True)

    services_list = query.order_by(WindowsService.DisplayName).all()

    return [
        {
            "service_id": svc.ServiceId,
            "service_name": svc.ServiceName,
            "display_name": svc.DisplayName,
            "status": svc.Status,
            "start_type": svc.StartType,
            "service_account": svc.ServiceAccount,
            "executable_path": svc.ExecutablePath,
            "is_active": svc.IsActive
        }
        for svc in services_list
    ]
