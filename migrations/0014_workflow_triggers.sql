CREATE TABLE IF NOT EXISTS backintel.analysis_workflow_triggers (
    id text PRIMARY KEY,
    goal_id text NOT NULL REFERENCES backintel.analysis_goals(id),
    owner text NOT NULL REFERENCES backintel.analysis_principals(id),
    workflow_version text NOT NULL,
    body jsonb NOT NULL,
    state text NOT NULL CHECK (state IN ('active','paused','expired','exhausted','removed')),
    next_due timestamptz,
    expires_at timestamptz NOT NULL,
    accepted_count integer NOT NULL DEFAULT 0 CHECK (accepted_count >= 0),
    cron_id text,
    timer_error text,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS backintel.analysis_trigger_receipts (
    trigger_id text NOT NULL REFERENCES backintel.analysis_workflow_triggers(id),
    occurrence text NOT NULL,
    request_sha256 text NOT NULL,
    run_id text NOT NULL REFERENCES backintel.analysis_runs(id),
    PRIMARY KEY (trigger_id, occurrence)
);
CREATE TABLE IF NOT EXISTS backintel.analysis_trigger_attempts (
    sequence bigserial PRIMARY KEY,
    trigger_id text NOT NULL REFERENCES backintel.analysis_workflow_triggers(id),
    occurrence text NOT NULL,
    status text NOT NULL CHECK (status IN ('accepted','reused','denied','skipped')),
    reason text NOT NULL,
    run_id text REFERENCES backintel.analysis_runs(id),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS analysis_trigger_owner ON backintel.analysis_workflow_triggers(owner,goal_id);
