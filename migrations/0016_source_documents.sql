CREATE TABLE IF NOT EXISTS backintel.analysis_documents (
    id text PRIMARY KEY CHECK (id ~ '^[a-f0-9]{64}$'),
    goal_id text NOT NULL REFERENCES backintel.analysis_goals(id),
    payload bytea NOT NULL,
    body jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS analysis_documents_goal ON backintel.analysis_documents(goal_id);
