import psycopg2
from sentence_transformers import SentenceTransformer

DB_CONFIG = {
    "dbname": "ankanePgVector",
    "user": "postgres", 
    "password": "bazepodataka",
    "host": "localhost",
    "port": "55432"
}

def create_both_vectors():    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("SELECT id, text_to_embed FROM articles_vectors WHERE text_to_embed IS NOT NULL")
    rows = cur.fetchall()
    
    print(f"Pronađeno {len(rows)} zapisa za obradu")
    
    model_384 = SentenceTransformer('all-MiniLM-L6-v2')
    model_768 = SentenceTransformer('all-mpnet-base-v2')
    
    batch_size = 200
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        texts = [row[1] for row in batch]
        ids = [row[0] for row in batch]
        
        vectors_384 = model_384.encode(texts, show_progress_bar=False)
        vectors_768 = model_768.encode(texts, show_progress_bar=False)
        
        for id_val, vec_384, vec_768 in zip(ids, vectors_384, vectors_768):
            cur.execute("""
                UPDATE articles_vectors 
                SET vector_384 = %s, vector_768 = %s
                WHERE id = %s
            """, (vec_384.tolist(), vec_768.tolist(), id_val))
        
        conn.commit()
        print(f"Obrađeno {i+len(batch)}/{len(rows)} zapisa")
    
    cur.close()
    conn.close()
    print("Oba vektora kreirana!")

if __name__ == "__main__":
    create_both_vectors()