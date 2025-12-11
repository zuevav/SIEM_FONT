-- ============================================================================
-- Migration: 003_create_soar_playbooks.sql
-- Description: Create SOAR Playbooks tables for automated response
-- Date: 2024-12-07
-- Phase: Phase 2 - SOAR & Automation
-- ============================================================================

-- Create automation schema
CREATE SCHEMA IF NOT EXISTS automation;

-- ============================================================================
-- Playbooks - Automated response workflows
-- ============================================================================

CREATE TABLE automation.playbooks (
    playbook_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Trigger conditions
    trigger_on_severity INTEGER[], -- [3, 4] = trigger on High and Critical
    trigger_on_mitre_tactic VARCHAR(100)[], -- ['TA0001', 'TA0002']
    trigger_on_rule_name VARCHAR(255)[], -- specific rule names
    trigger_conditions JSONB, -- Advanced JSON conditions

    -- Actions (array of action IDs in execution order)
    action_ids INTEGER[], -- [1, 2, 3] = execute actions in order

    -- Approval workflow
    requires_approval BOOLEAN DEFAULT FALSE,
    auto_approve_for_severity INTEGER[], -- Auto-approve for Critical (4)

    -- Status
    is_enabled BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,

    -- Metadata
    created_by INTEGER REFERENCES config.users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    last_executed_at TIMESTAMP,
    execution_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,

    -- Tags for organization
    tags VARCHAR(50)[]
);

CREATE INDEX idx_playbooks_enabled ON automation.playbooks(is_enabled, is_deleted);
CREATE INDEX idx_playbooks_severity ON automation.playbooks USING GIN(trigger_on_severity);
CREATE INDEX idx_playbooks_mitre ON automation.playbooks USING GIN(trigger_on_mitre_tactic);
CREATE INDEX idx_playbooks_created_at ON automation.playbooks(created_at DESC);

COMMENT ON TABLE automation.playbooks IS 'SOAR Playbooks - Automated response workflows';

-- ============================================================================
-- Playbook Actions - Individual steps in a playbook
-- ============================================================================

CREATE TABLE automation.playbook_actions (
    action_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Action type
    action_type VARCHAR(50) NOT NULL, -- block_ip, isolate_host, send_email, run_script, etc.

    -- Action configuration (JSON with type-specific params)
    config JSONB NOT NULL,
    /*
    Examples:
    block_ip: {"ip": "${alert.source_ip}", "firewall": "main", "duration_hours": 24}
    isolate_host: {"agent_id": "${alert.agent_id}", "network_isolation": true}
    send_email: {"to": "soc@company.com", "subject": "Critical Alert", "template": "alert_notification"}
    run_script: {"script": "quarantine.ps1", "agent_id": "${alert.agent_id}", "timeout": 60}
    */

    -- Execution settings
    timeout_seconds INTEGER DEFAULT 300,
    retry_count INTEGER DEFAULT 0,
    retry_delay_seconds INTEGER DEFAULT 60,
    continue_on_failure BOOLEAN DEFAULT FALSE,

    -- Rollback action (if this action needs to be undone)
    rollback_action_id INTEGER REFERENCES automation.playbook_actions(action_id),

    -- Status
    is_enabled BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,

    -- Metadata
    created_by INTEGER REFERENCES config.users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,

    CONSTRAINT ck_playbook_actions_type CHECK (action_type IN (
        'block_ip', 'block_domain', 'isolate_host', 'kill_process',
        'send_email', 'create_ticket', 'run_script', 'update_alert',
        'escalate_incident', 'add_to_blacklist', 'quarantine_file',
        'disable_user_account', 'reset_password', 'collect_forensics',
        'snapshot_vm', 'backup_logs', 'notify_slack', 'notify_telegram',
        'wait', 'conditional', 'loop', 'parallel'
    ))
);

CREATE INDEX idx_playbook_actions_type ON automation.playbook_actions(action_type);
CREATE INDEX idx_playbook_actions_enabled ON automation.playbook_actions(is_enabled, is_deleted);

COMMENT ON TABLE automation.playbook_actions IS 'Individual actions that can be executed in playbooks';

-- ============================================================================
-- Playbook Executions - History of playbook runs
-- ============================================================================

CREATE TABLE automation.playbook_executions (
    execution_id SERIAL PRIMARY KEY,
    playbook_id INTEGER NOT NULL REFERENCES automation.playbooks(playbook_id),

    -- What triggered this execution
    alert_id INTEGER REFERENCES incidents.alerts(alert_id) ON DELETE SET NULL,
    incident_id INTEGER REFERENCES incidents.incidents(incident_id) ON DELETE SET NULL,
    triggered_by_user_id INTEGER REFERENCES config.users(user_id), -- NULL if auto-triggered

    -- Execution status
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, running, success, failed, cancelled, awaiting_approval

    -- Timeline
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,

    -- Approval workflow
    requires_approval BOOLEAN DEFAULT FALSE,
    approved_by_user_id INTEGER REFERENCES config.users(user_id),
    approved_at TIMESTAMP,
    approval_comment TEXT,

    -- Results
    success BOOLEAN,
    error_message TEXT,
    execution_log JSONB, -- Detailed log of each action execution
    /*
    Example:
    {
        "actions": [
            {
                "action_id": 1,
                "action_name": "Block IP",
                "status": "success",
                "started_at": "2024-12-07T10:00:00Z",
                "completed_at": "2024-12-07T10:00:02Z",
                "duration_seconds": 2,
                "result": {"blocked_ip": "192.168.1.100", "firewall": "main"}
            },
            {
                "action_id": 2,
                "action_name": "Send Email",
                "status": "success",
                "started_at": "2024-12-07T10:00:02Z",
                "completed_at": "2024-12-07T10:00:03Z",
                "duration_seconds": 1,
                "result": {"email_sent": true, "recipients": ["soc@company.com"]}
            }
        ]
    }
    */

    -- Rollback
    rolled_back BOOLEAN DEFAULT FALSE,
    rollback_execution_id INTEGER REFERENCES automation.playbook_executions(execution_id),
    rollback_reason TEXT,

    CONSTRAINT ck_playbook_executions_status CHECK (status IN (
        'pending', 'running', 'success', 'failed', 'cancelled',
        'awaiting_approval', 'approved', 'rejected', 'rolled_back'
    ))
);

CREATE INDEX idx_playbook_executions_playbook ON automation.playbook_executions(playbook_id, started_at DESC);
CREATE INDEX idx_playbook_executions_alert ON automation.playbook_executions(alert_id);
CREATE INDEX idx_playbook_executions_incident ON automation.playbook_executions(incident_id);
CREATE INDEX idx_playbook_executions_status ON automation.playbook_executions(status);
CREATE INDEX idx_playbook_executions_started_at ON automation.playbook_executions(started_at DESC);

COMMENT ON TABLE automation.playbook_executions IS 'History of playbook executions with detailed logs';

-- ============================================================================
-- Action Results - Store results of each action execution
-- ============================================================================

CREATE TABLE automation.action_results (
    result_id SERIAL PRIMARY KEY,
    execution_id INTEGER NOT NULL REFERENCES automation.playbook_executions(execution_id) ON DELETE CASCADE,
    action_id INTEGER NOT NULL REFERENCES automation.playbook_actions(action_id),

    -- Execution order
    sequence_number INTEGER NOT NULL,

    -- Status
    status VARCHAR(20) NOT NULL, -- pending, running, success, failed, skipped

    -- Timeline
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,

    -- Results
    result JSONB, -- Action-specific result data
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Output that can be used in subsequent actions
    output_variables JSONB, -- {"blocked_ip": "192.168.1.100", "ticket_id": 123}

    CONSTRAINT ck_action_results_status CHECK (status IN (
        'pending', 'running', 'success', 'failed', 'skipped', 'timeout'
    ))
);

CREATE INDEX idx_action_results_execution ON automation.action_results(execution_id, sequence_number);
CREATE INDEX idx_action_results_action ON automation.action_results(action_id);
CREATE INDEX idx_action_results_status ON automation.action_results(status);

COMMENT ON TABLE automation.action_results IS 'Results of individual action executions within playbooks';

-- ============================================================================
-- Triggers for updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION automation.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW() AT TIME ZONE 'UTC';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_playbooks_updated_at
BEFORE UPDATE ON automation.playbooks
FOR EACH ROW
EXECUTE FUNCTION automation.update_updated_at_column();

CREATE TRIGGER tr_playbook_actions_updated_at
BEFORE UPDATE ON automation.playbook_actions
FOR EACH ROW
EXECUTE FUNCTION automation.update_updated_at_column();

-- ============================================================================
-- Success!
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Migration 003_create_soar_playbooks.sql completed successfully';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Created:';
    RAISE NOTICE '  - automation schema';
    RAISE NOTICE '  - automation.playbooks table';
    RAISE NOTICE '  - automation.playbook_actions table';
    RAISE NOTICE '  - automation.playbook_executions table';
    RAISE NOTICE '  - automation.action_results table';
    RAISE NOTICE '============================================================================';
END $$;
