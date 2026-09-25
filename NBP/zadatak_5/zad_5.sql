CREATE TABLE tablica_hnsw (
    id INTEGER PRIMARY KEY REFERENCES articles_vectors(id),
    vector_384 VECTOR(384),
    vector_768 VECTOR(768)
);

CREATE TABLE tablica_ivfflat (
    id INTEGER PRIMARY KEY REFERENCES articles_vectors(id),
    vector_384 VECTOR(384),
    vector_768 VECTOR(768)
);

INSERT INTO tablica_hnsw (id, vector_384, vector_768)
SELECT id, vector_384, vector_768
FROM articles_vectors 
WHERE vector_384 IS NOT NULL AND vector_768 IS NOT NULL;

INSERT INTO tablica_ivfflat (id, vector_384, vector_768)
SELECT id, vector_384, vector_768
FROM articles_vectors 
WHERE vector_384 IS NOT NULL AND vector_768 IS NOT NULL;