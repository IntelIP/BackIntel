-- Preserve old snapshots; corrected attribution creates a new derivation version.
ALTER TABLE backintel.semantic_signal_snapshots
  ADD COLUMN IF NOT EXISTS signal_version text NOT NULL DEFAULT 'review-signals-v1';
DO $$
DECLARE old_constraint record;
BEGIN
  FOR old_constraint IN
    SELECT conname FROM pg_constraint
    WHERE conrelid = 'backintel.semantic_signal_snapshots'::regclass
      AND contype = 'u'
      AND NOT EXISTS (
        SELECT 1 FROM pg_attribute
        WHERE attrelid = conrelid AND attnum = ANY(conkey) AND attname = 'signal_version'
      )
  LOOP
    EXECUTE format('ALTER TABLE backintel.semantic_signal_snapshots DROP CONSTRAINT %I', old_constraint.conname);
  END LOOP;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conrelid = 'backintel.semantic_signal_snapshots'::regclass
                   AND conname = 'semantic_signal_snapshot_version_key') THEN
    ALTER TABLE backintel.semantic_signal_snapshots
      ADD CONSTRAINT semantic_signal_snapshot_version_key
      UNIQUE (partition_id, question_set_version, signal_version, entity_type, entity_key);
  END IF;
END $$;
