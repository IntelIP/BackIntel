-- Immutable connector responses. Preparation stores references, never rewrites these bytes.
CREATE TABLE IF NOT EXISTS backintel.analysis_raw_inputs (
    id text PRIMARY KEY CHECK (id ~ '^[0-9a-f]{64}$'),
    goal_id text NOT NULL REFERENCES backintel.analysis_goals(id),
    goal_version integer NOT NULL,
    source_id text NOT NULL REFERENCES backintel.analysis_source_connections(id),
    source_version text NOT NULL,
    schema_name text NOT NULL,
    table_name text NOT NULL,
    payload bytea NOT NULL,
    body jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
