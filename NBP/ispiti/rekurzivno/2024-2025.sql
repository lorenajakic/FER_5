--Napisati jednu SQL naredbu kojom će se za serijal filmova ispisati identifikator 
--i naziv zadnjeg filma u serijalu, 
--ukupan broj filmova u serijalu i ukupnu zaradu od svih filmova u serijalu (totalBoxIncome).
--Uočite da zadnji film u serijalu ima prethodnika, ali nema nasljednika

WITH RECURSIVE movieHierarchy (movieId, prevMovieId)
AS 
(SELECT trackId, trackId
    FROM movie
   WHERE prevMovieid is not null
     AND NOT EXISTS (SELECT * 
                       FROM movie movieNasljednik
		              WHERE movie.trackId = movieNasljednik.prevMovieId) 
    UNION
 SELECT movieHierarchy.movieId, movie.prevMovieId
   FROM movieHierarchy, movie
  WHERE movieHierarchy.prevMovieId = movie.trackId
   AND movie.prevMovieId IS NOT NULL
)
SELECT movieHierarchy.movieid, track.trackTitle, COUNT(*) noOfMovies, SUM(boxIncome) totalBoxIncome
  FROM movieHierarchy 
  JOIN track ON movieHierarchy.movieId = track.trackId
  JOIN movie ON movieHierarchy.prevMovieId = movie.trackId
--where movieid = 2716
GROUP BY movieHierarchy.movieId, track.trackTitle
ORDER BY totalBoxIncome DESC