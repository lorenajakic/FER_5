--Napisati jednu SQL naredbu kojom će se dobiti podaci o slijedu filmova koji su snimani kao nastavci, ali samo za serijale s barem 3 filma ukupno (inicijalni film ima barem 2 nastavka).

--Podatke prikazati kao u tablici na dnu zadatka. U prvom stupcu su prikazani identifikatori filmova povezani znakovima '->', a u drugom pripadni nazivi filmova.

--movieIdSequence: 47 -> 2715 -> 2716 znači da je filmu s identifikatorom 47 nasljednik film 2715, a njegov nasljednik je 2716.

--Vodite računa da za određeni serijal ispišete samo najdulji slijed filmova. Npr. za serijal od ukupno 7 filmova kao što je onaj prikazan u 4. retku tablice (3764 -> 3765 -> 2157 -> 4774 -> 3766 -> 4775 -> 3767 -> 4776), ne treba ispisivati kraće slijedove:
--3764 -> 3765 -> 2157 -> 4774 -> 3766 -> 4775 -> 3767
--3764 -> 3765 -> 2157 -> 4774 -> 3766 -> 4775
--itd.

WITH RECURSIVE movieHierarchy (movieId, followingMovieId, movieIdSequence, movieTitleSequence, level)
AS 
( SELECT trackId, trackId, trackId::VARCHAR(100), trackTitle::VARCHAR(500),  0
    FROM movie
    NATURAL JOIN track
    UNION ALL
    SELECT movieHierarchy.movieId, movie.trackId,
          (movieIdSequence || ' -> ' || movie.trackId)::VARCHAR(100), 
          (movieTitleSequence || ' -> ' || trackTitle)::VARCHAR(500), level+1
    FROM movieHierarchy, movie, track
    WHERE movieHierarchy.followingMovieId = movie.prevMovieId
      AND track.trackId = movie.trackId
)
SELECT movieIdSequence, movieTitleSequence
  FROM  movieHierarchy
 WHERE level >= 2
 AND level = (SELECT max(level) FROM movieHierarchy movieHierarchy2
				WHERE movieHierarchy.movieId =  movieHierarchy2.movieId)
 AND NOT EXISTS (SELECT * FROM movie
                 WHERE movie.trackId = movieHierarchy.movieId
                   AND prevMovieId IS NOT NULL)
order by level 