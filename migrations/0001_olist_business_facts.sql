CREATE SCHEMA IF NOT EXISTS backintel;

CREATE TABLE IF NOT EXISTS backintel.schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS backintel.source_batches (
    batch_id UUID PRIMARY KEY,
    dataset_ref TEXT NOT NULL,
    source_version INTEGER NOT NULL,
    source_file TEXT NOT NULL,
    file_sha256 CHAR(64) NOT NULL,
    archive_sha256 CHAR(64) NOT NULL,
    schema_sha256 CHAR(64) NOT NULL,
    row_count BIGINT NOT NULL CHECK (row_count >= 0),
    file_bytes BIGINT NOT NULL CHECK (file_bytes >= 0),
    license TEXT NOT NULL,
    approved_use TEXT NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (dataset_ref, source_file, file_sha256),
    UNIQUE (batch_id, source_file)
);

CREATE TABLE IF NOT EXISTS backintel.source_records (
    batch_id UUID NOT NULL REFERENCES backintel.source_batches(batch_id),
    source_row_number BIGINT NOT NULL CHECK (source_row_number > 0),
    source_business_key TEXT,
    payload_sha256 CHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (batch_id, source_row_number)
);

CREATE OR REPLACE FUNCTION backintel.reject_source_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'BackIntel source evidence is append-only: % is not allowed on %.%',
        TG_OP, TG_TABLE_SCHEMA, TG_TABLE_NAME;
END;
$$;

DROP TRIGGER IF EXISTS source_batches_immutable ON backintel.source_batches;
CREATE TRIGGER source_batches_immutable
BEFORE UPDATE OR DELETE ON backintel.source_batches
FOR EACH ROW EXECUTE FUNCTION backintel.reject_source_mutation();

DROP TRIGGER IF EXISTS source_records_immutable ON backintel.source_records;
CREATE TRIGGER source_records_immutable
BEFORE UPDATE OR DELETE ON backintel.source_records
FOR EACH ROW EXECUTE FUNCTION backintel.reject_source_mutation();

CREATE TABLE IF NOT EXISTS backintel.customers (
    customer_id TEXT PRIMARY KEY,
    customer_unique_id TEXT,
    zip_code_prefix TEXT,
    city TEXT,
    state_code TEXT,
    source_batch_id UUID NOT NULL,
    source_row_number BIGINT NOT NULL,
    UNIQUE (source_batch_id, source_row_number),
    FOREIGN KEY (source_batch_id, source_row_number)
        REFERENCES backintel.source_records(batch_id, source_row_number)
);

CREATE TABLE IF NOT EXISTS backintel.sellers (
    seller_id TEXT PRIMARY KEY,
    zip_code_prefix TEXT,
    city TEXT,
    state_code TEXT,
    source_batch_id UUID NOT NULL,
    source_row_number BIGINT NOT NULL,
    UNIQUE (source_batch_id, source_row_number),
    FOREIGN KEY (source_batch_id, source_row_number)
        REFERENCES backintel.source_records(batch_id, source_row_number)
);

CREATE TABLE IF NOT EXISTS backintel.products (
    product_id TEXT PRIMARY KEY,
    category_name TEXT,
    name_length INTEGER,
    description_length INTEGER,
    photos_quantity INTEGER,
    weight_grams INTEGER,
    length_cm INTEGER,
    height_cm INTEGER,
    width_cm INTEGER,
    source_batch_id UUID NOT NULL,
    source_row_number BIGINT NOT NULL,
    UNIQUE (source_batch_id, source_row_number),
    FOREIGN KEY (source_batch_id, source_row_number)
        REFERENCES backintel.source_records(batch_id, source_row_number),
    CHECK (name_length IS NULL OR name_length >= 0),
    CHECK (description_length IS NULL OR description_length >= 0),
    CHECK (photos_quantity IS NULL OR photos_quantity >= 0),
    CHECK (weight_grams IS NULL OR weight_grams >= 0),
    CHECK (length_cm IS NULL OR length_cm >= 0),
    CHECK (height_cm IS NULL OR height_cm >= 0),
    CHECK (width_cm IS NULL OR width_cm >= 0)
);

CREATE TABLE IF NOT EXISTS backintel.orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES backintel.customers(customer_id),
    status TEXT NOT NULL,
    purchased_at TIMESTAMP WITHOUT TIME ZONE,
    approved_at TIMESTAMP WITHOUT TIME ZONE,
    carrier_handoff_at TIMESTAMP WITHOUT TIME ZONE,
    delivered_at TIMESTAMP WITHOUT TIME ZONE,
    estimated_delivery_at TIMESTAMP WITHOUT TIME ZONE,
    source_batch_id UUID NOT NULL,
    source_row_number BIGINT NOT NULL,
    UNIQUE (source_batch_id, source_row_number),
    FOREIGN KEY (source_batch_id, source_row_number)
        REFERENCES backintel.source_records(batch_id, source_row_number)
);

CREATE TABLE IF NOT EXISTS backintel.product_category_translations (
    category_name TEXT PRIMARY KEY,
    category_name_english TEXT NOT NULL,
    source_batch_id UUID NOT NULL,
    source_row_number BIGINT NOT NULL,
    UNIQUE (source_batch_id, source_row_number),
    FOREIGN KEY (source_batch_id, source_row_number)
        REFERENCES backintel.source_records(batch_id, source_row_number)
);

CREATE TABLE IF NOT EXISTS backintel.order_items (
    order_id TEXT NOT NULL REFERENCES backintel.orders(order_id),
    order_item_id INTEGER NOT NULL CHECK (order_item_id > 0),
    product_id TEXT NOT NULL REFERENCES backintel.products(product_id),
    seller_id TEXT NOT NULL REFERENCES backintel.sellers(seller_id),
    shipping_limit_at TIMESTAMP WITHOUT TIME ZONE,
    price NUMERIC(12, 2) NOT NULL CHECK (price >= 0),
    freight_value NUMERIC(12, 2) NOT NULL CHECK (freight_value >= 0),
    source_batch_id UUID NOT NULL,
    source_row_number BIGINT NOT NULL,
    PRIMARY KEY (order_id, order_item_id),
    UNIQUE (source_batch_id, source_row_number),
    FOREIGN KEY (source_batch_id, source_row_number)
        REFERENCES backintel.source_records(batch_id, source_row_number)
);

CREATE TABLE IF NOT EXISTS backintel.payments (
    order_id TEXT NOT NULL REFERENCES backintel.orders(order_id),
    payment_sequential INTEGER NOT NULL CHECK (payment_sequential > 0),
    payment_type TEXT NOT NULL,
    payment_installments INTEGER NOT NULL CHECK (payment_installments >= 0),
    payment_value NUMERIC(12, 2) NOT NULL CHECK (payment_value >= 0),
    source_batch_id UUID NOT NULL,
    source_row_number BIGINT NOT NULL,
    PRIMARY KEY (order_id, payment_sequential),
    UNIQUE (source_batch_id, source_row_number),
    FOREIGN KEY (source_batch_id, source_row_number)
        REFERENCES backintel.source_records(batch_id, source_row_number)
);

CREATE TABLE IF NOT EXISTS backintel.reviews (
    review_record_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_review_id TEXT NOT NULL,
    order_id TEXT NOT NULL REFERENCES backintel.orders(order_id),
    score SMALLINT,
    title TEXT,
    message TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE,
    answered_at TIMESTAMP WITHOUT TIME ZONE,
    source_batch_id UUID NOT NULL,
    source_row_number BIGINT NOT NULL,
    UNIQUE (source_batch_id, source_row_number),
    FOREIGN KEY (source_batch_id, source_row_number)
        REFERENCES backintel.source_records(batch_id, source_row_number),
    CHECK (score IS NULL OR score BETWEEN 1 AND 5)
);

CREATE INDEX IF NOT EXISTS orders_customer_idx ON backintel.orders(customer_id);
CREATE INDEX IF NOT EXISTS order_items_seller_idx ON backintel.order_items(seller_id, order_id);
CREATE INDEX IF NOT EXISTS order_items_product_idx ON backintel.order_items(product_id);
CREATE INDEX IF NOT EXISTS payments_order_idx ON backintel.payments(order_id);
CREATE INDEX IF NOT EXISTS reviews_order_idx ON backintel.reviews(order_id);

CREATE OR REPLACE VIEW backintel.order_summary AS
WITH item_totals AS (
    SELECT order_id,
           count(*)::BIGINT AS item_count,
           count(DISTINCT seller_id)::BIGINT AS seller_count,
           sum(price) AS item_value_total,
           sum(freight_value) AS freight_total
    FROM backintel.order_items
    GROUP BY order_id
), payment_totals AS (
    SELECT order_id,
           count(*)::BIGINT AS payment_row_count,
           sum(payment_value) AS payment_total
    FROM backintel.payments
    GROUP BY order_id
), review_totals AS (
    SELECT order_id,
           count(*)::BIGINT AS review_row_count,
           avg(score)::NUMERIC AS average_review_score
    FROM backintel.reviews
    GROUP BY order_id
)
SELECT o.order_id, o.customer_id, o.status, o.purchased_at, o.approved_at,
       o.carrier_handoff_at, o.delivered_at, o.estimated_delivery_at,
       COALESCE(i.item_count, 0) AS item_count,
       COALESCE(i.seller_count, 0) AS seller_count,
       COALESCE(i.item_value_total, 0::NUMERIC) AS item_value_total,
       COALESCE(i.freight_total, 0::NUMERIC) AS freight_total,
       COALESCE(p.payment_row_count, 0) AS payment_row_count,
       COALESCE(p.payment_total, 0::NUMERIC) AS payment_total,
       COALESCE(r.review_row_count, 0) AS review_row_count,
       r.average_review_score
FROM backintel.orders AS o
LEFT JOIN item_totals AS i USING (order_id)
LEFT JOIN payment_totals AS p USING (order_id)
LEFT JOIN review_totals AS r USING (order_id);

INSERT INTO backintel.schema_migrations(version)
VALUES (1)
ON CONFLICT (version) DO NOTHING;
