-- Uključi mjerenje vremena
\timing on

-- Kreiraj indekse
CREATE INDEX CONCURRENTLY idx_hnsw_384_l2 ON tablica_hnsw USING hnsw (vector_384 vector_l2_ops);
CREATE INDEX CONCURRENTLY idx_hnsw_384_ip ON tablica_hnsw USING hnsw (vector_384 vector_ip_ops);
CREATE INDEX CONCURRENTLY idx_hnsw_384_cosine ON tablica_hnsw USING hnsw (vector_384 vector_cosine_ops);

CREATE INDEX CONCURRENTLY idx_hnsw_768_l2 ON tablica_hnsw USING hnsw (vector_768 vector_l2_ops);
CREATE INDEX CONCURRENTLY idx_hnsw_768_ip ON tablica_hnsw USING hnsw (vector_768 vector_ip_ops);
CREATE INDEX CONCURRENTLY idx_hnsw_768_cosine ON tablica_hnsw USING hnsw (vector_768 vector_cosine_ops);

CREATE INDEX CONCURRENTLY idx_ivfflat_384_l2 ON tablica_ivfflat USING ivfflat (vector_384 vector_l2_ops) WITH (lists = 100);
CREATE INDEX CONCURRENTLY idx_ivfflat_384_ip ON tablica_ivfflat USING ivfflat (vector_384 vector_ip_ops) WITH (lists = 100);
CREATE INDEX CONCURRENTLY idx_ivfflat_384_cosine ON tablica_ivfflat USING ivfflat (vector_384 vector_cosine_ops) WITH (lists = 100);

CREATE INDEX CONCURRENTLY idx_ivfflat_768_l2 ON tablica_ivfflat USING ivfflat (vector_768 vector_l2_ops) WITH (lists = 100);
CREATE INDEX CONCURRENTLY idx_ivfflat_768_ip ON tablica_ivfflat USING ivfflat (vector_768 vector_ip_ops) WITH (lists = 100);
CREATE INDEX CONCURRENTLY idx_ivfflat_768_cosine ON tablica_ivfflat USING ivfflat (vector_768 vector_cosine_ops) WITH (lists = 100);

-- Isključi mjerenje vremena
\timing off