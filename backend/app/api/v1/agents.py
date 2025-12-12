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
        # Check if agent already exists by hostname (Agent model uses snake_case)
        existing_agent = db.query(Agent).filter(Agent.hostname == agent_data.hostname).first()

        if existing_agent:
            # Update existing agent (use snake_case attributes)
            existing_agent.fqdn = agent_data.fqdn
            existing_agent.ip_address = agent_data.ip_address
            existing_agent.mac_address = agent_data.mac_address
            existing_agent.os_version = agent_data.os_version
            existing_agent.os_build = agent_data.os_build
            existing_agent.os_architecture = agent_data.os_architecture
            existing_agent.domain = agent_data.domain
            existing_agent.organizational_unit = agent_data.organizational_unit
            existing_agent.manufacturer = agent_data.manufacturer
            existing_agent.model = agent_data.model
            existing_agent.serial_number = agent_data.serial_number
            existing_agent.cpu_model = agent_data.cpu_model
            existing_agent.cpu_cores = agent_data.cpu_cores
            existing_agent.total_ram_mb = agent_data.total_ram_mb
            existing_agent.total_disk_gb = agent_data.total_disk_gb
            existing_agent.agent_version = agent_data.agent_version
            existing_agent.status = 'online'
            existing_agent.last_seen = datetime.utcnow()

            db.commit()
            db.refresh(existing_agent)

            logger.info(f"Agent re-registered: {existing_agent.hostname} ({existing_agent.agent_id})")

            return AgentResponse.from_orm(existing_agent)

        # Create new agent (use snake_case for model attributes)
        new_agent = Agent(
            agent_id=str(uuid4()),
            hostname=agent_data.hostname,
            fqdn=agent_data.fqdn,
            ip_address=agent_data.ip_address,
            mac_address=agent_data.mac_address,
            os_version=agent_data.os_version,
            os_build=agent_data.os_build,
            os_architecture=agent_data.os_architecture,
            domain=agent_data.domain,
            organizational_unit=agent_data.organizational_unit,
            manufacturer=agent_data.manufacturer,
            model=agent_data.model,
            serial_number=agent_data.serial_number,
            cpu_model=agent_data.cpu_model,
            cpu_cores=agent_data.cpu_cores,
            total_ram_mb=agent_data.total_ram_mb,
            total_disk_gb=agent_data.total_disk_gb,
            agent_version=agent_data.agent_version,
            status='online',
            last_seen=datetime.utcnow(),
            registered_at=datetime.utcnow(),
            criticality_level=agent_data.criticality_level or 'medium',
            location=agent_data.location,
            owner=agent_data.owner,
            tags=json.dumps(agent_data.tags) if agent_data.tags else None
        )

        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)

        logger.info(f"New agent registered: {new_agent.hostname} ({new_agent.agent_id})")

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
        agent = db.query(Agent).filter(Agent.agent_id == str(heartbeat.agent_id)).first()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {heartbeat.agent_id} not found"
            )

        # Update agent status (use snake_case)
        agent.status = heartbeat.status
        agent.last_seen = datetime.utcnow()

        if heartbeat.ip_address:
            agent.ip_address = heartbeat.ip_address

        if heartbeat.agent_version:
            agent.agent_version = heartbeat.agent_version

        if heartbeat.last_reboot:
            agent.last_reboot = heartbeat.last_reboot

        db.commit()

        return {
            "success": True,
            "agent_id": str(agent.agent_id),
            "status": agent.status,
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


@router.post("/tampering-alert")
async def report_tampering_alert(
    alert_data: dict,
    db: Session = Depends(get_db)
):
    """
    Report agent tampering or protection alert
    Called by agent/watchdog when tampering is detected
    No authentication required (agent self-reporting)
    """
    try:
        agent_id = alert_data.get("agent_id")
        alert_type = alert_data.get("alert_type", "unknown")
        message = alert_data.get("message", "")
        details = alert_data.get("details", {})

        # Find agent
        agent = None
        if agent_id:
            agent = db.query(Agent).filter(Agent.agent_id == str(agent_id)).first()

        # Log critical alert
        logger.critical(
            f"AGENT TAMPERING ALERT [{alert_type}]: "
            f"Agent={agent_id or 'unknown'}, "
            f"Hostname={agent.hostname if agent else 'unknown'}, "
            f"Message={message}"
        )

        # Create high-severity event (Event model uses snake_case)
        from app.models.event import Event

        event = Event(
            agent_id=agent_id,
            event_time=datetime.utcnow(),
            source_type="agent_protection",
            event_code=9999,  # Special code for tampering alerts
            severity=4,  # critical = 4
            computer=agent.hostname if agent else details.get("computer", "unknown"),
            message=f"Agent Protection Alert: {alert_type} - {message}",
            raw_event=json.dumps({
                "alert_type": alert_type,
                "message": message,
                "details": details,
                "agent_id": agent_id
            })
        )
        db.add(event)

        # Update agent status if found
        if agent:
            agent.status = "alert"
            # Note: 'notes' field might not exist in Agent model, check if needed

        db.commit()

        return {
            "success": True,
            "alert_id": event.event_id if hasattr(event, 'event_id') else None,
            "message": "Tampering alert recorded"
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error recording tampering alert: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record alert: {str(e)}"
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
        agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )

        # Mark all current software as inactive first
        # FIX BUG-001: Use snake_case attributes (model uses snake_case)
        db.query(InstalledSoftware).filter(
            and_(
                InstalledSoftware.agent_id == agent_id,
                InstalledSoftware.is_active == True
            )
        ).update({
            "is_active": False,
            "removed_at": datetime.utcnow()
        })

        # Process each software item
        added_count = 0
        updated_count = 0

        for software in inventory.software_list:
            # Check if software exists in registry
            # FIX BUG-001: Use snake_case for SoftwareRegistry (has @property alias but column is snake_case)
            registry_entry = db.query(SoftwareRegistry).filter(
                SoftwareRegistry.name == software.name
            ).first()

            # Find or create installed software entry
            # FIX BUG-001: Use snake_case for InstalledSoftware model attributes
            existing = db.query(InstalledSoftware).filter(
                and_(
                    InstalledSoftware.agent_id == agent_id,
                    InstalledSoftware.name == software.name,
                    InstalledSoftware.version == software.version
                )
            ).first()

            if existing:
                # Reactivate if was previously removed
                existing.is_active = True
                existing.last_seen_at = datetime.utcnow()
                existing.removed_at = None
                updated_count += 1
            else:
                # Create new entry with snake_case attributes
                new_software = InstalledSoftware(
                    agent_id=agent_id,
                    software_id=registry_entry.software_id if registry_entry else None,
                    name=software.name,
                    version=software.version,
                    publisher=software.publisher,
                    install_date=software.install_date,
                    install_location=software.install_location,
                    uninstall_string=software.uninstall_string,
                    estimated_size_kb=software.estimated_size_kb,
                    is_active=True,
                    first_seen_at=datetime.utcnow(),
                    last_seen_at=datetime.utcnow()
                )
                db.add(new_software)
                added_count += 1

        # Update agent last inventory time
        # FIX BUG-002: Use snake_case - Agent model has last_inventory, not LastInventory
        agent.last_inventory = datetime.utcnow()

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
        agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )

        # Mark all current services as inactive
        # FIX BUG-003: Use snake_case for WindowsService model attributes
        db.query(WindowsService).filter(
            and_(
                WindowsService.agent_id == agent_id,
                WindowsService.is_active == True
            )
        ).update({
            "is_active": False
        })

        # Process each service
        added_count = 0
        updated_count = 0

        for service in inventory.services_list:
            # FIX BUG-003: Use snake_case for WindowsService queries
            existing = db.query(WindowsService).filter(
                and_(
                    WindowsService.agent_id == agent_id,
                    WindowsService.service_name == service.service_name
                )
            ).first()

            if existing:
                # Update existing service with snake_case attributes
                existing.display_name = service.display_name
                existing.status = service.status
                existing.start_type = service.start_type
                existing.service_account = service.service_account
                existing.executable_path = service.executable_path
                existing.is_active = True
                existing.last_seen_at = datetime.utcnow()
                updated_count += 1
            else:
                # Create new service entry with snake_case attributes
                new_service = WindowsService(
                    agent_id=agent_id,
                    service_name=service.service_name,
                    display_name=service.display_name,
                    status=service.status,
                    start_type=service.start_type,
                    service_account=service.service_account,
                    executable_path=service.executable_path,
                    is_active=True,
                    first_seen_at=datetime.utcnow(),
                    last_seen_at=datetime.utcnow()
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
    agent_status: Optional[str] = Query(None, description="Filter by status (online, offline, error)"),
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
        if agent_status:
            query = query.filter(Agent.status == agent_status)
        if domain:
            query = query.filter(Agent.domain == domain)
        if criticality:
            query = query.filter(Agent.criticality_level == criticality)

        if search:
            query = query.filter(
                or_(
                    Agent.hostname.ilike(f"%{search}%"),
                    Agent.fqdn.ilike(f"%{search}%"),
                    Agent.ip_address.ilike(f"%{search}%")
                )
            )

        # Get total count
        total = query.count()

        # Apply pagination
        agents = query.order_by(Agent.last_seen.desc()).offset(offset).limit(limit).all()

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
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()

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
        agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )

        # Update fields
        # FIX BUG-001: Use snake_case for Agent model attributes
        if update_data.tags is not None:
            agent.tags = json.dumps(update_data.tags)
        if update_data.location is not None:
            agent.location = update_data.location
        if update_data.owner is not None:
            agent.owner = update_data.owner
        if update_data.criticality_level is not None:
            agent.criticality_level = update_data.criticality_level

        db.commit()
        db.refresh(agent)

        logger.info(f"Agent {agent.hostname} updated by {current_user.username}")

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
        agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )

        # FIX BUG-001: Use snake_case - Agent model has hostname, not Hostname
        hostname = agent.hostname

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
        total_agents = db.query(func.count(Agent.agent_id)).scalar()

        # Agents by status
        online_agents = db.query(func.count(Agent.agent_id)).filter(Agent.status == 'online').scalar()
        offline_agents = db.query(func.count(Agent.agent_id)).filter(Agent.status == 'offline').scalar()
        error_agents = db.query(func.count(Agent.agent_id)).filter(Agent.status == 'error').scalar()

        # Agents by criticality
        critical_agents = db.query(func.count(Agent.agent_id)).filter(Agent.criticality_level == 'critical').scalar()

        # Agents by domain (top 10)
        agents_by_domain = {}
        domain_stats = db.query(
            Agent.domain,
            func.count(Agent.agent_id).label('count')
        ).group_by(Agent.domain).order_by(func.count(Agent.agent_id).desc()).limit(10).all()

        for domain, count in domain_stats:
            agents_by_domain[domain or 'No Domain'] = count

        # Agents by OS version (top 10)
        agents_by_os = {}
        os_stats = db.query(
            Agent.os_version,
            func.count(Agent.agent_id).label('count')
        ).group_by(Agent.os_version).order_by(func.count(Agent.agent_id).desc()).limit(10).all()

        for os_version, count in os_stats:
            agents_by_os[os_version or 'Unknown'] = count

        # Recently registered (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_agents = db.query(func.count(Agent.agent_id)).filter(
            Agent.registered_at >= week_ago
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
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    # Query software
    # FIX BUG-001: Use snake_case for InstalledSoftware model attributes
    query = db.query(InstalledSoftware).filter(InstalledSoftware.agent_id == agent_id)

    if not include_inactive:
        query = query.filter(InstalledSoftware.is_active == True)

    software_list = query.order_by(InstalledSoftware.name).all()

    return [
        {
            "install_id": sw.install_id,
            "name": sw.name,
            "version": sw.version,
            "publisher": sw.publisher,
            "install_date": sw.install_date,
            "is_active": sw.is_active,
            "first_seen": sw.first_seen_at,
            "last_seen": sw.last_seen_at
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
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    # Query services
    # FIX BUG-003: Use snake_case for WindowsService model attributes
    query = db.query(WindowsService).filter(WindowsService.agent_id == agent_id)

    if not include_inactive:
        query = query.filter(WindowsService.is_active == True)

    services_list = query.order_by(WindowsService.display_name).all()

    return [
        {
            "service_id": svc.service_id,
            "service_name": svc.service_name,
            "display_name": svc.display_name,
            "status": svc.status,
            "start_type": svc.start_type,
            "service_account": svc.service_account,
            "executable_path": svc.executable_path,
            "is_active": svc.is_active
        }
        for svc in services_list
    ]
