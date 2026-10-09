CREATE SCHEMA IF NOT EXISTS backintel;

CREATE TABLE IF NOT EXISTS backintel.capability_evidence (
    sha256 text PRIMARY KEY CHECK (length(sha256) = 64),
    task_id text NOT NULL,
    kind text NOT NULL,
    identity text NOT NULL,
    available_at bigint NOT NULL CHECK (available_at >= 0),
    body jsonb NOT NULL,
    parents text[] NOT NULL DEFAULT '{}',
    UNIQUE (task_id, kind, identity)
);
CREATE INDEX IF NOT EXISTS capability_evidence_lookup
    ON backintel.capability_evidence (task_id, kind, available_at);

-- Accepted evidence is append-only, including for the application table owner.
CREATE OR REPLACE FUNCTION backintel.reject_evidence_change() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN
    RAISE EXCEPTION 'Accepted capability evidence is immutable';
END $$;
DROP TRIGGER IF EXISTS capability_evidence_immutable ON backintel.capability_evidence;
CREATE TRIGGER capability_evidence_immutable BEFORE UPDATE OR DELETE
    ON backintel.capability_evidence FOR EACH ROW
    EXECUTE FUNCTION backintel.reject_evidence_change();
