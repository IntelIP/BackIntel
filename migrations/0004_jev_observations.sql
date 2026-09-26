ALTER TABLE backintel.usage_events
  DROP CONSTRAINT usage_events_outcome_check;
ALTER TABLE backintel.usage_events
  ADD CONSTRAINT usage_events_outcome_check
  CHECK (outcome IN ('started', 'success', 'error', 'cancelled'));

CREATE TABLE IF NOT EXISTS backintel.semantic_question_sets (
  version text PRIMARY KEY,
  content_sha256 char(64) NOT NULL,
  definition jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS backintel.jev_observations (
  observation_id uuid PRIMARY KEY,
  partition_id text NOT NULL,
  review_record_id bigint NOT NULL REFERENCES backintel.reviews(review_record_id),
  question_set_version text NOT NULL REFERENCES backintel.semantic_question_sets(version),
  input_text_sha256 char(64) NOT NULL,
  source_language text NOT NULL,
  translation_method text,
  model text NOT NULL,
  request_id text,
  answers jsonb NOT NULL,
  usage_event_id uuid NOT NULL REFERENCES backintel.usage_events(event_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (partition_id, review_record_id, question_set_version)
);
CREATE INDEX IF NOT EXISTS jev_observations_review_idx
  ON backintel.jev_observations (review_record_id, question_set_version);
CREATE INDEX IF NOT EXISTS jev_observations_partition_idx
  ON backintel.jev_observations (partition_id, created_at);

CREATE OR REPLACE FUNCTION backintel.reject_semantic_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'BackIntel semantic evidence is append-only: % is not allowed on %.%',
    TG_OP, TG_TABLE_SCHEMA, TG_TABLE_NAME;
END;
$$;

DROP TRIGGER IF EXISTS semantic_question_sets_immutable ON backintel.semantic_question_sets;
CREATE TRIGGER semantic_question_sets_immutable
BEFORE UPDATE OR DELETE ON backintel.semantic_question_sets
FOR EACH ROW EXECUTE FUNCTION backintel.reject_semantic_mutation();
DROP TRIGGER IF EXISTS jev_observations_immutable ON backintel.jev_observations;
CREATE TRIGGER jev_observations_immutable
BEFORE UPDATE OR DELETE ON backintel.jev_observations
FOR EACH ROW EXECUTE FUNCTION backintel.reject_semantic_mutation();

CREATE TABLE IF NOT EXISTS backintel.jev_observation_corrections (
  correction_id uuid PRIMARY KEY,
  observation_id uuid NOT NULL REFERENCES backintel.jev_observations(observation_id),
  corrected_by text NOT NULL,
  corrected_answers jsonb NOT NULL,
  rationale text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS jev_corrections_observation_idx
  ON backintel.jev_observation_corrections (observation_id, created_at);
DROP TRIGGER IF EXISTS jev_observation_corrections_immutable ON backintel.jev_observation_corrections;
CREATE TRIGGER jev_observation_corrections_immutable
BEFORE UPDATE OR DELETE ON backintel.jev_observation_corrections
FOR EACH ROW EXECUTE FUNCTION backintel.reject_semantic_mutation();
