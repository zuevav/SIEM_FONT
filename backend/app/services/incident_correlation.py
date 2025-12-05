"""
Incident Correlation Service
Automatically correlates related alerts into incidents based on:
- Time windows
- Affected hosts/users
- MITRE ATT&CK chains
- Alert patterns
"""

import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import json

from app.models.incident import Alert, Incident
from app.models.detection import DetectionRule
from app.services.ai_service import get_ai_service

logger = logging.getLogger(__name__)


class IncidentCorrelationService:
    """
    Service for automatic alert correlation and incident creation
    """

    # Correlation parameters
    TIME_WINDOW_HOURS = 4  # Correlate alerts within 4 hours
    MIN_ALERTS_FOR_INCIDENT = 3  # Minimum alerts to auto-create incident

    # MITRE ATT&CK kill chain phases (in order)
    MITRE_KILL_CHAIN = [
        'Initial Access',
        'Execution',
        'Persistence',
        'Privilege Escalation',
        'Defense Evasion',
        'Credential Access',
        'Discovery',
        'Lateral Movement',
        'Collection',
        'Command and Control',
        'Exfiltration',
        'Impact'
    ]

    def __init__(self, db: Session):
        self.db = db

    async def correlate_new_alert(self, alert: Alert) -> Optional[Incident]:
        """
        Correlate a new alert with existing alerts and potentially create an incident

        Args:
            alert: Newly created alert

        Returns:
            Created incident if correlation succeeded, None otherwise
        """
        try:
            # Skip if alert already assigned to incident
            if alert.IncidentId:
                return None

            # Find related alerts
            related_alerts = self._find_related_alerts(alert)

            if not related_alerts:
                # Check auto-escalate rules
                return await self._check_auto_escalate(alert)

            # Check if any related alert is already part of an incident
            existing_incident = self._find_existing_incident(related_alerts)
            if existing_incident:
                # Add this alert to existing incident
                alert.IncidentId = existing_incident.IncidentId
                existing_incident.AlertCount += 1
                existing_incident.EventCount += alert.EventCount
                existing_incident.UpdatedAt = datetime.utcnow()

                # Update affected assets
                self._update_incident_assets(existing_incident, [alert])

                # Add work log entry
                work_log = json.loads(existing_incident.WorkLog) if existing_incident.WorkLog else []
                work_log.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "user": "system",
                    "entry": f"Correlated new alert: {alert.Title}",
                    "type": "correlation"
                })
                existing_incident.WorkLog = json.dumps(work_log)

                self.db.commit()
                logger.info(f"Alert {alert.AlertId} added to existing incident {existing_incident.IncidentId}")
                return existing_incident

            # Check if we should create new incident
            all_alerts = related_alerts + [alert]

            if self._should_create_incident(all_alerts):
                incident = await self._create_correlated_incident(all_alerts)
                logger.info(f"Created new incident {incident.IncidentId} from {len(all_alerts)} correlated alerts")
                return incident

            return None

        except Exception as e:
            logger.error(f"Error correlating alert {alert.AlertId}: {e}", exc_info=True)
            return None

    def _find_related_alerts(self, alert: Alert) -> List[Alert]:
        """
        Find alerts related to the given alert
        """
        time_window_start = alert.FirstSeenAt - timedelta(hours=self.TIME_WINDOW_HOURS)
        time_window_end = alert.FirstSeenAt + timedelta(hours=self.TIME_WINDOW_HOURS)

        # Build query for related alerts
        query = self.db.query(Alert).filter(
            and_(
                Alert.AlertId != alert.AlertId,  # Exclude the alert itself
                Alert.IncidentId.is_(None),  # Only unassigned alerts
                Alert.FirstSeenAt >= time_window_start,
                Alert.FirstSeenAt <= time_window_end,
                Alert.Status != 'false_positive'  # Exclude false positives
            )
        )

        # Correlation conditions (any of these)
        conditions = []

        # Same computer
        if alert.Computer:
            conditions.append(Alert.Computer == alert.Computer)

        # Same username
        if alert.Username:
            conditions.append(Alert.Username == alert.Username)

        # Same source IP
        if alert.SourceIP:
            conditions.append(Alert.SourceIP == alert.SourceIP)

        if conditions:
            query = query.filter(or_(*conditions))
        else:
            # No correlation criteria, return empty
            return []

        related_alerts = query.all()

        # Filter by MITRE ATT&CK chain
        related_alerts = self._filter_by_mitre_chain([alert] + related_alerts)

        return [a for a in related_alerts if a.AlertId != alert.AlertId]

    def _filter_by_mitre_chain(self, alerts: List[Alert]) -> List[Alert]:
        """
        Filter alerts that form a logical MITRE ATT&CK kill chain
        """
        if len(alerts) < 2:
            return alerts

        # Extract MITRE tactics from alerts
        alert_tactics = []
        for alert in alerts:
            if alert.MitreAttackTactic:
                alert_tactics.append((alert, alert.MitreAttackTactic))

        if len(alert_tactics) < 2:
            return alerts  # Not enough MITRE data

        # Check if tactics form a progression in kill chain
        tactic_positions = []
        for alert, tactic in alert_tactics:
            if tactic in self.MITRE_KILL_CHAIN:
                pos = self.MITRE_KILL_CHAIN.index(tactic)
                tactic_positions.append((alert, pos))

        if len(tactic_positions) < 2:
            return alerts

        # Sort by position
        tactic_positions.sort(key=lambda x: x[1])

        # Check if positions are progressive (not random)
        positions = [pos for _, pos in tactic_positions]
        is_progressive = all(positions[i] <= positions[i+1] for i in range(len(positions)-1))

        if is_progressive:
            logger.info(f"Detected MITRE ATT&CK kill chain: {[self.MITRE_KILL_CHAIN[p] for p in positions]}")
            return alerts

        return alerts

    def _find_existing_incident(self, alerts: List[Alert]) -> Optional[Incident]:
        """
        Check if any of the related alerts is already part of an incident
        """
        for alert in alerts:
            if alert.IncidentId:
                incident = self.db.query(Incident).filter(
                    Incident.IncidentId == alert.IncidentId
                ).first()
                if incident and incident.Status not in ['closed', 'resolved']:
                    return incident
        return None

    def _should_create_incident(self, alerts: List[Alert]) -> bool:
        """
        Determine if we should create an incident from these alerts
        """
        # Minimum number of alerts
        if len(alerts) < self.MIN_ALERTS_FOR_INCIDENT:
            return False

        # At least one high/critical severity alert
        has_critical = any(alert.Severity >= 3 for alert in alerts)
        if not has_critical:
            return False

        # Check for MITRE kill chain
        mitre_tactics = set()
        for alert in alerts:
            if alert.MitreAttackTactic:
                mitre_tactics.add(alert.MitreAttackTactic)

        # If we have 3+ different tactics, it's likely a multi-stage attack
        if len(mitre_tactics) >= 3:
            logger.info(f"Detected multi-stage attack with tactics: {mitre_tactics}")
            return True

        # If we have 5+ alerts of same type on same host
        if len(alerts) >= 5:
            return True

        return False

    async def _create_correlated_incident(self, alerts: List[Alert]) -> Incident:
        """
        Create a new incident from correlated alerts
        """
        # Calculate incident properties
        max_severity = max(alert.Severity for alert in alerts)
        total_events = sum(alert.EventCount for alert in alerts)

        # Get unique MITRE tactics and techniques
        mitre_tactics = set()
        mitre_techniques = set()
        for alert in alerts:
            if alert.MitreAttackTactic:
                mitre_tactics.add(alert.MitreAttackTactic)
            if alert.MitreAttackTechnique:
                mitre_techniques.add(alert.MitreAttackTechnique)

        # Generate title
        if len(mitre_tactics) >= 3:
            title = f"Multi-stage attack detected: {', '.join(list(mitre_tactics)[:3])}"
        else:
            title = f"Security incident: {alerts[0].Title}"

        # Get affected hosts and users
        affected_hosts = set()
        affected_users = set()
        for alert in alerts:
            if alert.Computer:
                affected_hosts.add(alert.Computer)
            if alert.Username:
                affected_users.add(alert.Username)

        # Determine category
        category = self._determine_incident_category(mitre_tactics)

        # Create incident
        incident = Incident(
            Title=title[:500],  # Limit to 500 chars
            Description=f"Automatically correlated from {len(alerts)} related alerts",
            Severity=max_severity,
            Category=category,
            AlertCount=len(alerts),
            EventCount=total_events,
            AffectedAgents=json.dumps(list(affected_hosts)),
            AffectedUsers=json.dumps(list(affected_users)),
            AffectedAssets=len(affected_hosts),
            StartTime=min(alert.FirstSeenAt for alert in alerts),
            DetectedAt=datetime.utcnow(),
            Status='open',
            Priority=2 if max_severity >= 4 else 1,
            MitreAttackTactics=json.dumps(list(mitre_tactics)),
            MitreAttackTechniques=json.dumps(list(mitre_techniques)),
            IsAutoCorrelated=True,
            CreatedAt=datetime.utcnow(),
            WorkLog=json.dumps([{
                "timestamp": datetime.utcnow().isoformat(),
                "user": "system",
                "entry": f"Incident auto-created from {len(alerts)} correlated alerts",
                "type": "milestone"
            }])
        )

        self.db.add(incident)
        self.db.flush()

        # Link alerts to incident
        for alert in alerts:
            alert.IncidentId = incident.IncidentId

        # Run AI analysis if available
        try:
            ai_service = get_ai_service()
            if ai_service.is_enabled():
                ai_analysis = await self._analyze_incident_with_ai(incident, alerts)
                if ai_analysis:
                    incident.AIAnalysis = json.dumps(ai_analysis)
                    incident.AIProcessed = True
        except Exception as e:
            logger.warning(f"AI analysis failed for incident: {e}")

        self.db.commit()
        self.db.refresh(incident)

        return incident

    async def _check_auto_escalate(self, alert: Alert) -> Optional[Incident]:
        """
        Check if this alert should be auto-escalated to an incident
        """
        # Get the detection rule
        if not alert.DetectionRuleId:
            return None

        rule = self.db.query(DetectionRule).filter(
            DetectionRule.RuleId == alert.DetectionRuleId
        ).first()

        if not rule or not rule.AutoEscalate:
            return None

        # Auto-escalate only critical/high severity alerts
        if alert.Severity < 3:
            return None

        logger.info(f"Auto-escalating alert {alert.AlertId} to incident (rule: {rule.RuleName})")

        # Create incident from single alert
        incident = Incident(
            Title=f"[AUTO-ESCALATED] {alert.Title}",
            Description=f"Automatically escalated from detection rule: {rule.RuleName}",
            Severity=alert.Severity,
            Category=self._determine_incident_category([alert.MitreAttackTactic]) if alert.MitreAttackTactic else 'Suspicious Activity',
            AlertCount=1,
            EventCount=alert.EventCount,
            AffectedAgents=json.dumps([alert.Computer]) if alert.Computer else None,
            AffectedUsers=json.dumps([alert.Username]) if alert.Username else None,
            AffectedAssets=1 if alert.Computer else 0,
            StartTime=alert.FirstSeenAt,
            DetectedAt=datetime.utcnow(),
            Status='open',
            Priority=2,
            MitreAttackTactics=json.dumps([alert.MitreAttackTactic]) if alert.MitreAttackTactic else None,
            MitreAttackTechniques=json.dumps([alert.MitreAttackTechnique]) if alert.MitreAttackTechnique else None,
            IsAutoCorrelated=False,
            CreatedAt=datetime.utcnow(),
            WorkLog=json.dumps([{
                "timestamp": datetime.utcnow().isoformat(),
                "user": "system",
                "entry": f"Incident auto-escalated from detection rule '{rule.RuleName}'",
                "type": "milestone"
            }])
        )

        self.db.add(incident)
        self.db.flush()

        # Link alert
        alert.IncidentId = incident.IncidentId

        self.db.commit()
        self.db.refresh(incident)

        return incident

    def _determine_incident_category(self, mitre_tactics: Set[str]) -> str:
        """
        Determine incident category based on MITRE tactics
        """
        tactics_lower = {t.lower() for t in mitre_tactics if t}

        if 'impact' in tactics_lower:
            return 'Ransomware/Data Destruction'
        elif 'exfiltration' in tactics_lower:
            return 'Data Exfiltration'
        elif 'credential access' in tactics_lower or 'lateral movement' in tactics_lower:
            return 'Credential Theft / Lateral Movement'
        elif 'command and control' in tactics_lower:
            return 'Command & Control'
        elif 'persistence' in tactics_lower or 'privilege escalation' in tactics_lower:
            return 'Persistence / Privilege Escalation'
        elif 'initial access' in tactics_lower or 'execution' in tactics_lower:
            return 'Initial Access / Execution'
        else:
            return 'Suspicious Activity'

    def _update_incident_assets(self, incident: Incident, new_alerts: List[Alert]):
        """
        Update incident's affected hosts and users
        """
        # Load existing
        affected_hosts = set(json.loads(incident.AffectedAgents)) if incident.AffectedAgents else set()
        affected_users = set(json.loads(incident.AffectedUsers)) if incident.AffectedUsers else set()

        # Add new
        for alert in new_alerts:
            if alert.Computer:
                affected_hosts.add(alert.Computer)
            if alert.Username:
                affected_users.add(alert.Username)

        # Save
        incident.AffectedAgents = json.dumps(list(affected_hosts))
        incident.AffectedUsers = json.dumps(list(affected_users))
        incident.AffectedAssets = len(affected_hosts)

    async def _analyze_incident_with_ai(self, incident: Incident, alerts: List[Alert]) -> Dict[str, Any]:
        """
        Analyze incident using AI service
        """
        try:
            ai_service = get_ai_service()

            # Prepare incident data
            incident_data = {
                "incident_id": incident.IncidentId,
                "title": incident.Title,
                "severity": incident.Severity,
                "category": incident.Category,
                "start_time": incident.StartTime.isoformat() if incident.StartTime else None,
                "mitre_tactics": json.loads(incident.MitreAttackTactics) if incident.MitreAttackTactics else [],
                "mitre_techniques": json.loads(incident.MitreAttackTechniques) if incident.MitreAttackTechniques else [],
                "affected_hosts": json.loads(incident.AffectedAgents) if incident.AffectedAgents else [],
                "affected_users": json.loads(incident.AffectedUsers) if incident.AffectedUsers else []
            }

            # Prepare alerts data
            alerts_data = []
            for alert in alerts:
                alerts_data.append({
                    "alert_id": alert.AlertId,
                    "title": alert.Title,
                    "severity": alert.Severity,
                    "first_seen": alert.FirstSeenAt.isoformat(),
                    "computer": alert.Computer,
                    "username": alert.Username,
                    "mitre_tactic": alert.MitreAttackTactic,
                    "mitre_technique": alert.MitreAttackTechnique
                })

            # Call AI analysis
            ai_result = await ai_service.analyze_incident(incident_data, alerts_data)

            return ai_result

        except Exception as e:
            logger.error(f"Error in AI analysis: {e}", exc_info=True)
            return None


def get_correlation_service(db: Session) -> IncidentCorrelationService:
    """
    Get incident correlation service instance
    """
    return IncidentCorrelationService(db)
