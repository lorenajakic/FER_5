--Napisati jednu SQL naredbu kojom će se dobiti slika o ustroju hijerarhije žanrova (vidi sliku na dnu zadatka).
--Za žanrove na najvišoj razini hijerarhije žanrova (nema nadređeni žanr), ispisati podatke kao u tablici na dnu zadatka s tim da je značenje stupaca sljedeće:

--level - razina u hijerarhijskoj strukturi. Iznosi 1 za razinu na kojoj je sam žanr i povećava za 1 u svakoj podređenoj razini.
--noOfGenres - broj žanrova koji su "podređeni" nekom žanru točno na toj razini
--noOfGenresCumul - kumulativni broj "podređenih" žanrova - podređeni su tom žanru na toj i svim sljedećim razinama

WITH RECURSIVE genreHierarchy (genreId, sub_GenreId, level)
AS 
( SELECT genreId, genreId, 1
    FROM genre
    UNION ALL
    SELECT genreHierarchy.genreId, genre.genreId, level+1
    FROM genreHierarchy, genre
    WHERE genreHierarchy.sub_genreId = genre.supGenreId
)
SELECT genreHierarchy.genreId, genre.genreName, level, 
      COUNT(*),
      SUM(COUNT(*)) OVER (PARTITION BY genreHierarchy.genreId ORDER BY level DESC)

  FROM genreHierarchy, genre
  WHERE genreHierarchy.genreId =  genre.genreid
  AND genre.supgenreId is NULL
GROUP by genreHierarchy.genreId, genre.genreName, level
ORDER BY genreHierarchy.genreId, level