"""
Playbook Execution Engine
Executes SOAR playbook actions automatically or with approval
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.playbook import (
    Playbook, PlaybookAction, PlaybookExecution, ActionResult,
    ActionType, ActionStatus, PlaybookStatus
)
from app.models.incident import Alert
from app.services.email_service import send_email
from app.config import settings

logger = logging.getLogger(__name__)


class PlaybookExecutor:
    """Executes SOAR playbooks and their actions"""

    def __init__(self, db: Session):
        self.db = db

    async def trigger_playbooks_for_alert(self, alert_id: int) -> List[int]:
        """
        Find and trigger all playbooks matching the alert criteria

        Returns:
            List of execution IDs
        """
        try:
            # Get alert
            alert = self.db.query(Alert).filter(Alert.alert_id == alert_id).first()
            if not alert:
                logger.error(f"Alert {alert_id} not found")
                return []

            # Find matching playbooks
            playbooks = self.db.query(Playbook).filter(
                Playbook.is_enabled == True
            ).all()

            execution_ids = []
            for playbook in playbooks:
                if self._matches_trigger(playbook, alert):
                    execution_id = await self.execute_playbook(playbook.playbook_id, alert_id)
                    if execution_id:
                        execution_ids.append(execution_id)

            return execution_ids

        except Exception as e:
            logger.error(f"Error triggering playbooks for alert {alert_id}: {e}", exc_info=True)
            return []

    def _matches_trigger(self, playbook: Playbook, alert: Alert) -> bool:
        """Check if playbook trigger conditions match the alert"""
        # Check severity
        if playbook.trigger_on_severity:
            if alert.severity not in playbook.trigger_on_severity:
                return False

        # Check MITRE tactic
        if playbook.trigger_on_mitre_tactic:
            if alert.mitre_attack_tactic not in playbook.trigger_on_mitre_tactic:
                return False

        return True

    async def execute_playbook(
        self,
        playbook_id: int,
        alert_id: Optional[int] = None,
        incident_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Execute a playbook

        Args:
            playbook_id: Playbook to execute
            alert_id: Optional alert that triggered the playbook
            incident_id: Optional incident that triggered the playbook

        Returns:
            Execution ID if successful, None otherwise
        """
        try:
            # Get playbook
            playbook = self.db.query(Playbook).filter(
                Playbook.playbook_id == playbook_id
            ).first()

            if not playbook:
                logger.error(f"Playbook {playbook_id} not found")
                return None

            # Create execution record
            execution = PlaybookExecution(
                playbook_id=playbook_id,
                alert_id=alert_id,
                incident_id=incident_id,
                status=PlaybookStatus.PENDING,
                started_at=datetime.utcnow(),
                execution_log={"actions": []}
            )
            self.db.add(execution)
            self.db.commit()
            self.db.refresh(execution)

            # Check if approval required
            if playbook.requires_approval:
                execution.status = PlaybookStatus.PENDING_APPROVAL
                self.db.commit()
                logger.info(f"Playbook {playbook_id} execution {execution.execution_id} pending approval")
                return execution.execution_id

            # Execute actions
            await self._execute_actions(execution, playbook)

            return execution.execution_id

        except Exception as e:
            logger.error(f"Error executing playbook {playbook_id}: {e}", exc_info=True)
            return None

    async def _execute_actions(self, execution: PlaybookExecution, playbook: Playbook):
        """Execute all actions in the playbook"""
        try:
            execution.status = PlaybookStatus.RUNNING
            self.db.commit()

            # Get actions
            if not playbook.action_ids:
                logger.warning(f"Playbook {playbook.playbook_id} has no actions")
                execution.status = PlaybookStatus.COMPLETED
                execution.completed_at = datetime.utcnow()
                self.db.commit()
                return

            actions = self.db.query(PlaybookAction).filter(
                PlaybookAction.action_id.in_(playbook.action_ids)
            ).order_by(PlaybookAction.action_id).all()

            # Execute each action
            success_count = 0
            failed_count = 0

            for action in actions:
                result = await self._execute_action(execution, action)

                if result.status == ActionStatus.COMPLETED:
                    success_count += 1
                elif result.status == ActionStatus.FAILED:
                    failed_count += 1

                # Update execution log
                execution.execution_log["actions"].append({
                    "action_id": action.action_id,
                    "action_name": action.name,
                    "action_type": action.action_type,
                    "status": result.status,
                    "started_at": result.started_at.isoformat() if result.started_at else None,
                    "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                    "error": result.error_message
                })
                self.db.commit()

            # Update playbook execution status
            if failed_count == 0:
                execution.status = PlaybookStatus.COMPLETED
                playbook.success_count += 1
            elif success_count == 0:
                execution.status = PlaybookStatus.FAILED
                playbook.failure_count += 1
            else:
                execution.status = PlaybookStatus.PARTIAL
                playbook.failure_count += 1

            execution.completed_at = datetime.utcnow()
            playbook.execution_count += 1
            self.db.commit()

            logger.info(
                f"Playbook {playbook.playbook_id} execution {execution.execution_id} "
                f"completed: {success_count} success, {failed_count} failed"
            )

        except Exception as e:
            logger.error(f"Error executing actions for playbook {playbook.playbook_id}: {e}", exc_info=True)
            execution.status = PlaybookStatus.FAILED
            execution.completed_at = datetime.utcnow()
            self.db.commit()

    async def _execute_action(
        self,
        execution: PlaybookExecution,
        action: PlaybookAction
    ) -> ActionResult:
        """Execute a single action"""
        # Create action result
        result = ActionResult(
            execution_id=execution.execution_id,
            action_id=action.action_id,
            status=ActionStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)

        try:
            # Execute action based on type
            if action.action_type == ActionType.BLOCK_IP:
                await self._action_block_ip(action, result)
            elif action.action_type == ActionType.BLOCK_DOMAIN:
                await self._action_block_domain(action, result)
            elif action.action_type == ActionType.ISOLATE_HOST:
                await self._action_isolate_host(action, result)
            elif action.action_type == ActionType.KILL_PROCESS:
                await self._action_kill_process(action, result)
            elif action.action_type == ActionType.QUARANTINE_FILE:
                await self._action_quarantine_file(action, result)
            elif action.action_type == ActionType.SEND_EMAIL:
                await self._action_send_email(action, result)
            elif action.action_type == ActionType.CREATE_TICKET:
                await self._action_create_ticket(action, result)
            elif action.action_type == ActionType.RUN_SCRIPT:
                await self._action_run_script(action, result)
            else:
                raise NotImplementedError(f"Action type {action.action_type} not implemented")

            # Mark as completed
            result.status = ActionStatus.COMPLETED
            result.completed_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Action {action.action_id} ({action.action_type}) completed successfully")

        except Exception as e:
            logger.error(f"Action {action.action_id} failed: {e}", exc_info=True)
            result.status = ActionStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.utcnow()
            self.db.commit()

            # Retry if configured
            if action.retry_count > 0 and (result.retry_count or 0) < action.retry_count:
                logger.info(f"Retrying action {action.action_id} (attempt {(result.retry_count or 0) + 1})")
                await asyncio.sleep(2 ** (result.retry_count or 0))  # Exponential backoff
                result.retry_count = (result.retry_count or 0) + 1
                result.status = ActionStatus.RETRYING
                self.db.commit()
                return await self._execute_action(execution, action)

        return result

    # ========================================================================
    # Action Implementations
    # ========================================================================

    async def _action_block_ip(self, action: PlaybookAction, result: ActionResult):
        """Block IP address in firewall"""
        config = action.config
        ip_address = config.get("ip_address")

        if not ip_address:
            raise ValueError("Missing ip_address in action config")

        # TODO: Integrate with actual firewall API
        # For now, just log the action
        logger.info(f"PLAYBOOK ACTION: Would block IP {ip_address}")

        result.output = {
            "action": "block_ip",
            "ip_address": ip_address,
            "status": "simulated"
        }

    async def _action_block_domain(self, action: PlaybookAction, result: ActionResult):
        """Block domain in DNS/firewall"""
        config = action.config
        domain = config.get("domain")

        if not domain:
            raise ValueError("Missing domain in action config")

        logger.info(f"PLAYBOOK ACTION: Would block domain {domain}")

        result.output = {
            "action": "block_domain",
            "domain": domain,
            "status": "simulated"
        }

    async def _action_isolate_host(self, action: PlaybookAction, result: ActionResult):
        """Isolate host from network"""
        config = action.config
        hostname = config.get("hostname")

        if not hostname:
            raise ValueError("Missing hostname in action config")

        logger.info(f"PLAYBOOK ACTION: Would isolate host {hostname}")

        result.output = {
            "action": "isolate_host",
            "hostname": hostname,
            "status": "simulated"
        }

    async def _action_kill_process(self, action: PlaybookAction, result: ActionResult):
        """Kill process on remote host"""
        config = action.config
        hostname = config.get("hostname")
        process_name = config.get("process_name")

        if not hostname or not process_name:
            raise ValueError("Missing hostname or process_name in action config")

        logger.info(f"PLAYBOOK ACTION: Would kill process {process_name} on {hostname}")

        result.output = {
            "action": "kill_process",
            "hostname": hostname,
            "process_name": process_name,
            "status": "simulated"
        }

    async def _action_quarantine_file(self, action: PlaybookAction, result: ActionResult):
        """Quarantine file on remote host"""
        config = action.config
        hostname = config.get("hostname")
        file_path = config.get("file_path")

        if not hostname or not file_path:
            raise ValueError("Missing hostname or file_path in action config")

        logger.info(f"PLAYBOOK ACTION: Would quarantine file {file_path} on {hostname}")

        result.output = {
            "action": "quarantine_file",
            "hostname": hostname,
            "file_path": file_path,
            "status": "simulated"
        }

    async def _action_send_email(self, action: PlaybookAction, result: ActionResult):
        """Send email notification"""
        config = action.config
        to_addresses = config.get("to_addresses", [])
        subject = config.get("subject", "SIEM Playbook Action")
        body = config.get("body", "")

        if not to_addresses:
            raise ValueError("Missing to_addresses in action config")

        # Send email using existing email service
        try:
            for email in to_addresses:
                await send_email(
                    to_email=email,
                    subject=subject,
                    html_body=body
                )

            result.output = {
                "action": "send_email",
                "to_addresses": to_addresses,
                "subject": subject,
                "status": "sent"
            }
        except Exception as e:
            raise Exception(f"Failed to send email: {e}")

    async def _action_create_ticket(self, action: PlaybookAction, result: ActionResult):
        """Create ticket in helpdesk system"""
        config = action.config
        title = config.get("title")
        description = config.get("description")

        if not title:
            raise ValueError("Missing title in action config")

        logger.info(f"PLAYBOOK ACTION: Would create ticket '{title}'")

        result.output = {
            "action": "create_ticket",
            "title": title,
            "description": description,
            "status": "simulated"
        }

    async def _action_run_script(self, action: PlaybookAction, result: ActionResult):
        """Run custom script"""
        config = action.config
        script_path = config.get("script_path")
        arguments = config.get("arguments", [])

        if not script_path:
            raise ValueError("Missing script_path in action config")

        logger.info(f"PLAYBOOK ACTION: Would run script {script_path} with args {arguments}")

        result.output = {
            "action": "run_script",
            "script_path": script_path,
            "arguments": arguments,
            "status": "simulated"
        }

    async def approve_execution(self, execution_id: int, approved_by: int) -> bool:
        """Approve a pending playbook execution"""
        try:
            execution = self.db.query(PlaybookExecution).filter(
                PlaybookExecution.execution_id == execution_id
            ).first()

            if not execution:
                logger.error(f"Execution {execution_id} not found")
                return False

            if execution.status != PlaybookStatus.PENDING_APPROVAL:
                logger.error(f"Execution {execution_id} is not pending approval")
                return False

            # Get playbook
            playbook = self.db.query(Playbook).filter(
                Playbook.playbook_id == execution.playbook_id
            ).first()

            # Execute actions
            await self._execute_actions(execution, playbook)

            return True

        except Exception as e:
            logger.error(f"Error approving execution {execution_id}: {e}", exc_info=True)
            return False

    async def cancel_execution(self, execution_id: int, cancelled_by: int) -> bool:
        """Cancel a running or pending playbook execution"""
        try:
            execution = self.db.query(PlaybookExecution).filter(
                PlaybookExecution.execution_id == execution_id
            ).first()

            if not execution:
                logger.error(f"Execution {execution_id} not found")
                return False

            if execution.status in [PlaybookStatus.COMPLETED, PlaybookStatus.FAILED, PlaybookStatus.CANCELLED]:
                logger.error(f"Execution {execution_id} cannot be cancelled (status: {execution.status})")
                return False

            execution.status = PlaybookStatus.CANCELLED
            execution.completed_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Execution {execution_id} cancelled by user {cancelled_by}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling execution {execution_id}: {e}", exc_info=True)
            return False
