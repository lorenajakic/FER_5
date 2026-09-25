-- Definirajmo "zelenu cestu" kao cestu (roads) koja je nekim svojim dijelom udaljena 50m ili manje od šume ili voćnjaka (landuse.fclass, forest ili orchard).

-- Za općinu Šibenik (muny.name_2) i njene zelene ceste je potrebno ispisati naziv općine, gid ceste, te broj šuma/voćnjaka koji su 50m ili manje udaljeni od zelene ceste, te prosječnu udaljenost do tih šuma/voćnjaka.

-- Prosječnu udaljenost zaokružiti na dva decimalna mjesta (možda ćete prije zaokruživanja trebati napraviti cast na numeric - broj::numeric), a rezultate poredati po broju šuma/voćnjaka silazno, te prosječnoj udaljenosti uzlazno.

SELECT muny.name_2, roads.gid road_gid, COUNT(*) AS no,
       ROUND(AVG(st_distance(st_intersection(roads.geom, muny.geom), st_intersection(landuse.geom, muny.geom)))::numeric, 2) avg_distance
FROM muny
JOIN roads ON st_intersects(muny.geom, roads.geom)
JOIN landuse ON st_intersects(muny.geom, landuse.geom)
WHERE muny.name_2 = 'Šibenik' AND (landuse.fclass = 'forest' OR landuse.fclass = 'orchard') AND
       st_distance(st_intersection(roads.geom, muny.geom), st_intersection(landuse.geom, muny.geom)) <= 50
GROUP BY muny.name_2, roads.gid
ORDER BY no DESC, avg_distance ASC