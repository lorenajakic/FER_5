--Napisati jednu SQL naredbu kojom će se za medijske sadržaje po žanrovima i godinama početka pregledavanja ispisati broj započetih pregledavanja:

--u promatranoj godini (views1Y)
--u trogodišnjem periodu koji obuhvaća godinu prije, promatranu godinu i godinu poslije promatrane (views3Y)
--kumulativno - u svim godinama prije promatrane uključujući i promatranoj godini
--Tablica na dnu zadatka ilustrira izgled rezultata.

SELECT genreName,
         EXTRACT (YEAR FROM viewStartDateTime) viewYear,
         COUNT(*) views1Y,
		 SUM(count(*)) OVER (PARTITION BY genreName 
						ORDER BY EXTRACT (YEAR FROM viewStartDateTime) 
						RANGE BETWEEN 1 PRECEDING AND 1 FOLLOWING) views3Y,
		 SUM(count(*)) OVER (PARTITION BY genreName 
						ORDER BY EXTRACT (YEAR FROM viewStartDateTime) ) viewsCumul		 
  FROM trackView
  NATURAL JOIN trackGenre
  NATURAL JOIN genre
GROUP BY genreName,
         EXTRACT (YEAR FROM viewStartDateTime) 
ORDER BY genreName,
         EXTRACT (YEAR FROM viewStartDateTime) 