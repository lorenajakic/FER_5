CREATE EXTENSION pgvector; 	  
CREATE EXTENSION fuzzystrmatch; 	-- (soundex, levenshtein, metaphone)
CREATE EXTENSION pg_trgm;		-- (similarity , show_Trgm,…, %, <->)


CREATE TEXT SEARCH CONFIGURATION lj53867 (COPY = simple);

CREATE TEXT SEARCH DICTIONARY lj53867Syn
(TEMPLATE = synonym,
SYNONYMS = lj53867syn);

ALTER TEXT SEARCH CONFIGURATION lj53867
	ALTER MAPPING FOR word, asciiword WITH lj53867Syn, english_stem;

SELECT *
FROM ts_debug('lj53867', 'He did not respond to the gigantic question about xyz quickly.');


CREATE TABLE document(
	id SERIAL PRIMARY KEY,
	title TEXT,
	keyword TEXT,
	abstract TEXT,
	body TEXT,
	allTSV TSVECTOR
);

CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    title VECTOR(384),
    body VECTOR(768),
	creted_at TIMESTAMP
);

INSERT INTO document (title, keyword, abstract, body)
VALUES
('Wildlife Conservation Efforts',
 'animals, conservation, environment',
 'Conservation programs protect endangered animals and restore ecosystems.',
 'Efforts to preserve wildlife include protecting habitats, preventing poaching, and educating the public about endangered species.'),
('Dogs in Everyday Life',
 'dogs, pets',
 'They are loyal animals and often considered best friends to humans.',
 'Dogs help humans in many ways. Dogs can assist in therapy, dogs work in search and rescue, and dogs bring joy to families.'),
 ('Dogs in Everyday Life',
 'dogs, pets',
 'They are loyal animals and often considered best friends to humans.',
 'Dogs help humans in many ways. Dogs can assist in therapy, dogs work in search and rescue, and dogs bring joy to families.
  Dogs help humans in many ways. Dogs can assist in therapy, dogs work in search and rescue, and dogs bring joy to families.'),
 ('Dogs in Everyday Life Dogs Dogs',
 'dogs, pets',
 'They are loyal animals and often considered best friends to humans.',
 'Dogs help humans in many ways. Dogs can assist in therapy, dogs work in search and rescue, and dogs bring joy to families.
  Dogs help humans in many ways. Dogs can assist in therapy, dogs work in search and rescue, and dogs bring joy to families.');
  

UPDATE document
	SET allTSV = setweight(to_tsvector('english', title), 'A') ||
	setweight(to_tsvector('english', keyword), 'B') ||
	setweight(to_tsvector('english', abstract), 'C') ||
	setweight(to_tsvector('english', body), 'D');

Primjer tsvectora: Slika allTSV pokazuje da su dijelovima dokumenta dodijeljene različite težine. N
Npr. 'environ':6B, environ je normalizirana riječ, pojavljuje se 6 puta u odjeljku s težinom B.
   
SELECT allTSV FROM document LIMIT 1;

# 'anim':4B,11C 'conserv':2A,5B,7C 'ecosystem':14C 'educ':25 'effort':3A,15 'endang':10C,29 'environ':6B 'habitat':21 'includ':19 'poach':23 'preserv':17 'prevent':22 'program':8C 


Primjer kako rang dokumenta raste kada se riječi iz upita pojavljuju u dijelovima dokumenta s većim težinama. Title i body imaju najveću težinu.
Dokument id = 1:
('Wildlife Conservation Efforts',
 'animals, conservation, environment',
 'Conservation programs protect endangered animals and restore ecosystems.',
 'Efforts to preserve wildlife include protecting habitats, preventing poaching, and educating the public about endangered species.'),

Slika wildlife:
SELECT ts_rank(allTSV, to_tsquery('wildlife')) AS rank
FROM document
WHERE id = 1
Rezultat: 0.6231253, riječ wildlife nalazi se u body i title stoga se dobije viša sličnost.

Slika animals:
SELECT ts_rank(allTSV, to_tsquery('animals')) AS rank
FROM document
WHERE id = 1
Rezlutat: 0.2735672, riječ animals nalazi se u abstract i keyword stoga se dobije niža sličnost.


DODATNI DIO

SELECT id, title,
       ts_rank(allTSV, to_tsquery('dogs')) AS rank
FROM document
WHERE title ILIKE '%dogs%'
ORDER BY rank DESC;
  
Kao rezltat dobijemo sljedeće rezulatte
1. 0.84896547 = Dokument s najmanje teksta, ali isti broj ponavljanja riječi 'dogs' kao 3. dokument.
2. 0.6833945  = Dokument s 'običnim' tekstom, bez dodatnog ponavljanja riječi 'dogs'.
3. 0.6869435 = Dokument s najviše teksta, a isti broj ponavljanja riječi 'dogs' kao 1. dokument.
  
Zaključak:
 a) Većim ponavljanjem riječi dobijemo i veću sličnost.
 b) Ako povećavamo broj riječi koje nisu u našem upitu sličnost se povećava ali u manjoj mjeri.


CREATE INDEX CONCURRENTLY hnsw_index ON documents USING hnsw (title vector_cosine_ops);
CREATE INDEX CONCURRENTLY hnsw_index ON documents USING hnsw (body vector_cosine_ops);
