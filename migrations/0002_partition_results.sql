CREATE SCHEMA IF NOT EXISTS backintel;
CREATE TABLE IF NOT EXISTS backintel.partition_results (
  partition_id text PRIMARY KEY,
  input_sha256 text NOT NULL,
  record_count integer NOT NULL CHECK (record_count BETWEEN 1 AND 100),
  disposition text NOT NULL CHECK (disposition IN ('partial', 'failed', 'blocked', 'accepted', 'published')),
  result_sha256 text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK ((disposition IN ('accepted', 'published')) = (result_sha256 IS NOT NULL))
);
