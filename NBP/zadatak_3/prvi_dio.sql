SELECT ts_rank(allTSV, to_tsquery('wildlife')) AS rank
FROM document
WHERE id = 1

SELECT ts_rank(allTSV, to_tsquery('animals')) AS rank
FROM document
WHERE id = 1