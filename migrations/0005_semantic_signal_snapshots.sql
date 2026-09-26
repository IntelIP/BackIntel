CREATE TABLE IF NOT EXISTS backintel.semantic_signal_snapshots (
  snapshot_id uuid PRIMARY KEY,
  partition_id text NOT NULL REFERENCES backintel.partition_results(partition_id),
  question_set_version text NOT NULL REFERENCES backintel.semantic_question_sets(version),
  entity_type text NOT NULL CHECK (entity_type IN ('marketplace', 'seller', 'category')),
  entity_key text NOT NULL,
  review_count integer NOT NULL CHECK (review_count > 0),
  metrics jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (partition_id, question_set_version, entity_type, entity_key)
);
CREATE INDEX IF NOT EXISTS semantic_signal_entity_idx
  ON backintel.semantic_signal_snapshots (entity_type, entity_key, created_at);
DROP TRIGGER IF EXISTS semantic_signal_snapshots_immutable ON backintel.semantic_signal_snapshots;
CREATE TRIGGER semantic_signal_snapshots_immutable
BEFORE UPDATE OR DELETE ON backintel.semantic_signal_snapshots
FOR EACH ROW EXECUTE FUNCTION backintel.reject_semantic_mutation();
