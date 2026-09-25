import psycopg2
import time

DB_CONFIG = {
    "dbname": "ankanePgVector",
    "user": "postgres", 
    "password": "bazepodataka",
    "host": "localhost",
    "port": "55432"
}

def create_indexes_with_timing():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    indexes = [
        ("HNSW 384D L2", "CREATE INDEX idx_hnsw_384_l2 ON tablica_hnsw USING hnsw (vector_384 vector_l2_ops) WITH (m = 16, ef_construction = 200)"),
        ("HNSW 384D IP", "CREATE INDEX idx_hnsw_384_ip ON tablica_hnsw USING hnsw (vector_384 vector_ip_ops) WITH (m = 16, ef_construction = 200)"),
        ("HNSW 384D Cosine", "CREATE INDEX idx_hnsw_384_cosine ON tablica_hnsw USING hnsw (vector_384 vector_cosine_ops) WITH (m = 16, ef_construction = 200)"),
        ("HNSW 768D L2", "CREATE INDEX idx_hnsw_768_l2 ON tablica_hnsw USING hnsw (vector_768 vector_l2_ops) WITH (m = 16, ef_construction = 200)"),
        ("HNSW 768D IP", "CREATE INDEX idx_hnsw_768_ip ON tablica_hnsw USING hnsw (vector_768 vector_ip_ops) WITH (m = 16, ef_construction = 200)"),
        ("HNSW 768D Cosine", "CREATE INDEX idx_hnsw_768_cosine ON tablica_hnsw USING hnsw (vector_768 vector_cosine_ops) WITH (m = 16, ef_construction = 200)"),
        ("IVFFlat 384D L2", "CREATE INDEX idx_ivfflat_384_l2 ON tablica_ivfflat USING ivfflat (vector_384 vector_l2_ops) WITH (lists = 200)"),
        ("IVFFlat 384D IP", "CREATE INDEX idx_ivfflat_384_ip ON tablica_ivfflat USING ivfflat (vector_384 vector_ip_ops) WITH (lists = 200)"),
        ("IVFFlat 384D Cosine", "CREATE INDEX idx_ivfflat_384_cosine ON tablica_ivfflat USING ivfflat (vector_384 vector_cosine_ops) WITH (lists = 200)"),
        ("IVFFlat 768D L2", "CREATE INDEX idx_ivfflat_768_l2 ON tablica_ivfflat USING ivfflat (vector_768 vector_l2_ops) WITH (lists = 200)"),
        ("IVFFlat 768D IP", "CREATE INDEX idx_ivfflat_768_ip ON tablica_ivfflat USING ivfflat (vector_768 vector_ip_ops) WITH (lists = 200)"),
        ("IVFFlat 768D Cosine", "CREATE INDEX idx_ivfflat_768_cosine ON tablica_ivfflat USING ivfflat (vector_768 vector_cosine_ops) WITH (lists = 200)")
    ]
        
    for _, (name, sql) in enumerate(indexes, 1):
        start_time = time.perf_counter()
        cur.execute(sql)
        conn.commit()
        end_time = time.perf_counter()
        print(f"{name}: {end_time - start_time:.2f}s")
    
    cur.close()
    conn.close()
        
if __name__ == "__main__":
    create_indexes_with_timing()