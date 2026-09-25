SELECT id, title,
       ts_rank(allTSV, to_tsquery('dogs')) AS rank
FROM document
WHERE title ILIKE '%dogs%'
ORDER BY rank DESC;