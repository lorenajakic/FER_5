UPDATE document
	SET allTSV = setweight(to_tsvector('english', title), 'A') ||
	setweight(to_tsvector('english', keyword), 'B') ||
	setweight(to_tsvector('english', abstract), 'C') ||
	setweight(to_tsvector('english', body), 'D');