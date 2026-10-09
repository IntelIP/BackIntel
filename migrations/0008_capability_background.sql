CREATE TABLE IF NOT EXISTS backintel.capability_triggers (
    trigger_id text PRIMARY KEY,
    task_id text NOT NULL,
    kind text NOT NULL CHECK (kind IN ('event','schedule','deadline','staleness','on_demand')),
    payload jsonb NOT NULL,
    due_at timestamptz NOT NULL,
    state text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','fired','cancelled')),
    repeat_seconds integer CHECK (repeat_seconds > 0),
    remaining integer NOT NULL DEFAULT 1 CHECK (remaining BETWEEN 0 AND 100),
    occurrence integer NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS capability_triggers_due ON backintel.capability_triggers (due_at) WHERE state='pending';

CREATE TABLE IF NOT EXISTS backintel.capability_jobs (
    job_id text PRIMARY KEY,
    task_id text NOT NULL,
    trigger_id text REFERENCES backintel.capability_triggers(trigger_id),
    payload jsonb NOT NULL,
    input_sha256 text NOT NULL,
    state text NOT NULL DEFAULT 'queued' CHECK (state IN ('queued','running','retry','completed','failed','cancelled')),
    attempts integer NOT NULL DEFAULT 0,
    max_attempts integer NOT NULL DEFAULT 2 CHECK (max_attempts BETWEEN 1 AND 5),
    due_at timestamptz NOT NULL DEFAULT now(),
    lease_until timestamptz,
    cancel_requested boolean NOT NULL DEFAULT false,
    result_sha256 text REFERENCES backintel.capability_evidence(sha256),
    error text,
    wall_ms double precision,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((state='completed') = (result_sha256 IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS capability_jobs_due ON backintel.capability_jobs (due_at,state);
ALTER TABLE backintel.capability_jobs ADD COLUMN IF NOT EXISTS sequence bigserial;
CREATE UNIQUE INDEX IF NOT EXISTS capability_jobs_sequence ON backintel.capability_jobs(sequence);
