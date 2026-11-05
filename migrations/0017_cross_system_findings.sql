CREATE TABLE IF NOT EXISTS backintel.analysis_service_grants (
    id text PRIMARY KEY,
    domain text NOT NULL,
    principals text[] NOT NULL,
    base_url text NOT NULL,
    actions text[] NOT NULL CHECK (actions <@ ARRAY['read_targets','deliver_findings']::text[]),
    enabled boolean NOT NULL DEFAULT true,
    expires_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS backintel.analysis_cross_findings (
    id text PRIMARY KEY,
    run_id text NOT NULL REFERENCES backintel.analysis_runs(id),
    target_ref text NOT NULL REFERENCES backintel.analysis_service_grants(id),
    body jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS backintel.analysis_finding_deliveries (
    id text PRIMARY KEY,
    finding_id text NOT NULL REFERENCES backintel.analysis_cross_findings(id),
    destination_ref text NOT NULL REFERENCES backintel.analysis_service_grants(id),
    receipt jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(finding_id, destination_ref)
);
