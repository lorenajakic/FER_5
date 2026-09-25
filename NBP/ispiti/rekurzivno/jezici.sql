--Ispisati identifikator i naziv žanra na najvišoj razini hijerarhije žanrova (nema nadređeni žanr), naziv jezika podnapisa/titlova te po jezicima podnapisa/titlova ukupan broj medijskih sadržaja koji pripadaju tom žanru i to bez obzira radi li se o filmovima ili epizodama serija.
--Pored medijskih sadržaja koji žanru pripadaju temeljem evidencije u trackGenre smatra se da mu pripadaju i oni koji pripadaju nekom od njemu podređenih žanrova (direktno i indirektno podređeni).
--Ispisati podatke samo za žanrove i jezike za koje postoji barem 100 medijskih sadržaja.

--Donja tablica ilustrira izgled rezultata.

WITH RECURSIVE R(genreid, genrename, highestgenreid, highestgenrename, supgenreid)
    AS (
        SELECT genreid, genrename, genreid highestgenreid, genrename highestgenrename, supgenreid
        FROM genre
        WHERE supgenreid IS NULL

        UNION

        SELECT genre.genreid, genre.genrename, R.highestgenreid, R.highestgenrename,genre.supgenreid
        FROM genre JOIN R ON genre.supgenreid = R.genreid
    )

SELECT highestgenreid, highestgenrename, langname, COUNT(*) numoftracks
FROM R NATURAL JOIN trackgenre NATURAL JOIN track NATURAL JOIN subtitle JOIN language ON subtitle.subtitlelangid = language.langid
GROUP BY highestgenreid, highestgenrename, langname
HAVING COUNT(*) > 100
