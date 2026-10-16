-- Operator-managed grants are separate from objectives and untrusted source rows.
CREATE TABLE IF NOT EXISTS backintel.analysis_source_connections (
 id text PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9_-]{0,63}$'),
 domain text NOT NULL REFERENCES backintel.analysis_sources(id),
 secret_ref text NOT NULL CHECK (secret_ref ~ '^BACKINTEL_SOURCE_[A-Z0-9_]+$'),
 schemas text[] NOT NULL CHECK (cardinality(schemas) > 0),
 principals text[] NOT NULL CHECK (cardinality(principals) > 0),
 enabled boolean NOT NULL DEFAULT true,
 expires_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now()
);
