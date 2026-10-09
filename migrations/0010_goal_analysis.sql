CREATE SCHEMA IF NOT EXISTS backintel;
CREATE TABLE IF NOT EXISTS backintel.analysis_principals (
 id text PRIMARY KEY, token_hash text UNIQUE NOT NULL, role text NOT NULL CHECK(role IN ('manager','analyst','viewer','worker')),
 domains text[] NOT NULL, enabled boolean NOT NULL DEFAULT true
);
CREATE TABLE IF NOT EXISTS backintel.analysis_sources (
 id text PRIMARY KEY, domain text UNIQUE NOT NULL, body jsonb NOT NULL, latest_snapshot text,
 updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS backintel.analysis_snapshots (
 id text PRIMARY KEY, source_id text NOT NULL REFERENCES backintel.analysis_sources(id), body jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS backintel.analysis_records (
 snapshot_id text NOT NULL REFERENCES backintel.analysis_snapshots(id), id text NOT NULL,
 body jsonb NOT NULL, PRIMARY KEY(snapshot_id,id)
);
CREATE TABLE IF NOT EXISTS backintel.analysis_goals (
 id text PRIMARY KEY, owner text NOT NULL REFERENCES backintel.analysis_principals(id), domain text NOT NULL,
 version integer NOT NULL, body jsonb NOT NULL, confirmed boolean NOT NULL DEFAULT false,
 paused boolean NOT NULL DEFAULT false, last_success text, active_model text, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS backintel.analysis_goal_versions (
 goal_id text NOT NULL REFERENCES backintel.analysis_goals(id), version integer NOT NULL, body jsonb NOT NULL,
 actor text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(goal_id,version)
);
CREATE TABLE IF NOT EXISTS backintel.analysis_runs (
 id text PRIMARY KEY, goal_id text NOT NULL REFERENCES backintel.analysis_goals(id), owner text NOT NULL,
 snapshot_id text NOT NULL REFERENCES backintel.analysis_snapshots(id), goal_version integer NOT NULL,
 body jsonb NOT NULL, status text NOT NULL DEFAULT 'queued', result jsonb, error text,
 job_id text UNIQUE, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE backintel.analysis_runs ALTER COLUMN goal_id DROP NOT NULL;
ALTER TABLE backintel.analysis_runs ALTER COLUMN snapshot_id DROP NOT NULL;
ALTER TABLE backintel.analysis_runs ALTER COLUMN goal_version DROP NOT NULL;

CREATE TABLE IF NOT EXISTS backintel.analysis_events (
 sequence bigserial PRIMARY KEY, run_id text NOT NULL REFERENCES backintel.analysis_runs(id),
 kind text NOT NULL, body jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS backintel.analysis_steps (
 run_id text NOT NULL REFERENCES backintel.analysis_runs(id), id text NOT NULL, kind text NOT NULL,
 body jsonb NOT NULL, PRIMARY KEY(run_id,id)
);
CREATE TABLE IF NOT EXISTS backintel.analysis_requests (
 id text PRIMARY KEY, run_id text NOT NULL REFERENCES backintel.analysis_runs(id), domain text NOT NULL,
 reserved numeric NOT NULL CHECK(reserved>=0), charge numeric CHECK(charge>=0),
 status text NOT NULL CHECK(status IN ('reserved','sent','complete','uncertain')), response jsonb,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS backintel.analysis_models (
 id text PRIMARY KEY, goal_id text NOT NULL REFERENCES backintel.analysis_goals(id), snapshot_id text NOT NULL,
 body jsonb NOT NULL, promoted boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS backintel.analysis_reviews (
 id bigserial PRIMARY KEY, goal_id text NOT NULL REFERENCES backintel.analysis_goals(id), run_id text,
 actor text NOT NULL, body jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS analysis_runs_goal ON backintel.analysis_runs(goal_id,created_at DESC);
CREATE INDEX IF NOT EXISTS analysis_events_run ON backintel.analysis_events(run_id,sequence);
CREATE INDEX IF NOT EXISTS analysis_models_goal ON backintel.analysis_models(goal_id,created_at DESC);
