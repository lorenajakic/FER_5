DROP INDEX IF EXISTS articles_title_trgm;

EXPLAIN ANALYZE
SELECT title
FROM articles_vectors 
WHERE title % 'animals';

CREATE INDEX CONCURRENTLY articles_title_trgm 
ON articles_vectors USING GIST (title gist_trgm_ops);

EXPLAIN ANALYZE
SELECT title
FROM articles_vectors 
WHERE title % 'animals';