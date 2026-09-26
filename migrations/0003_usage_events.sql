-- One row per processing attempt or external call, never per logical accepted partition.
-- Excludes source text, customer IDs, credentials, and raw prompts.
CREATE TABLE IF NOT EXISTS backintel.usage_events (
  event_id uuid PRIMARY KEY,
  partition_id text NOT NULL,
  stage text NOT NULL CHECK (stage IN ('runtime', 'jev', 'prediction', 'artifact')),
  provider text NOT NULL,
  model text,
  request_id text,
  outcome text NOT NULL CHECK (outcome IN ('success', 'error', 'cancelled')),
  record_count integer NOT NULL CHECK (record_count >= 0),
  wall_ms bigint NOT NULL CHECK (wall_ms >= 0),
  input_tokens integer CHECK (input_tokens >= 0),
  output_tokens integer CHECK (output_tokens >= 0),
  charge_status text NOT NULL CHECK (charge_status IN ('measured', 'estimated', 'unknown', 'not_applicable')),
  charge_usd numeric(18, 9) CHECK (charge_usd >= 0),
  price_ref text,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  CHECK ((charge_status IN ('measured', 'estimated')) = (charge_usd IS NOT NULL)),
  CHECK (charge_status <> 'estimated' OR price_ref IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS usage_events_partition_idx ON backintel.usage_events (partition_id, occurred_at);
