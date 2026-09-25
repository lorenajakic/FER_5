--Ispisati broj medijskih sadržaja po kategorijama (track.categories) i ograničenjema na sadržaje ovisno o starosnoj dobi (track.tAgeRestriction). Zanemarite medijske sadržaje s nedefiniram ograničenjem.

--Tablica na dnu zadatka ilustrira izgled rezultata, ali sami morate odrediti konačni broj stupaca u rezultatu tj. sva postojeća ograničenja na sadržaje ovisno o starosnoj dobi. Stupce u tablici nazovite slijedeći obrazac vidljiv iz naziva prikazanih stupaca.

SELECT * 
FROM crosstab ($$ SELECT catName::VARCHAR(50), tAgeRestriction, count(*)  
                  FROM track, unnest (categories) catName
                 WHERE tAgeRestriction IS NOT NULL
              GROUP BY catName, tAgeRestriction
              ORDER BY catName, tAgeRestriction $$
             , $$ SELECT DISTINCT tAgeRestriction FROM track WHERE tAgeRestriction IS NOT NULL ORDER BY tAgeRestriction $$) 
               AS pivotTable (catName VARCHAR(50)
                          , Age7 int, Age12 int, Aget13 int, Age14 int, rest17 int);

