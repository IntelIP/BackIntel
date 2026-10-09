-- Commit request admission before a paid call. An uncertain request is never retried automatically.
CREATE TABLE IF NOT EXISTS backintel.capability_model_requests (
    request_key text PRIMARY KEY,
    task_id text NOT NULL,
    source_sha256 text NOT NULL REFERENCES backintel.capability_evidence(sha256),
    model text NOT NULL,
    request jsonb NOT NULL,
    state text NOT NULL CHECK (state IN ('admitted','completed','blocked')),
    response jsonb,
    metadata jsonb,
    error text,
    created_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    CHECK ((state='completed') = (response IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS backintel.capability_provider_authorizations (
    authorization_id text PRIMARY KEY,
    provider text NOT NULL CHECK (provider='openrouter'),
    model text NOT NULL,
    max_requests integer NOT NULL CHECK (max_requests BETWEEN 1 AND 100),
    max_input_characters integer NOT NULL CHECK (max_input_characters BETWEEN 1 AND 5000),
    max_measured_usd numeric CHECK (max_measured_usd > 0),
    price_ceiling_known boolean NOT NULL DEFAULT false,
    approved boolean NOT NULL DEFAULT false,
    scope_sha256 text NOT NULL,
    scope jsonb NOT NULL,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE backintel.capability_model_requests ADD COLUMN IF NOT EXISTS authorization_id text
    REFERENCES backintel.capability_provider_authorizations(authorization_id);
