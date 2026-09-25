-- Želimo pronaći broj vila (buildings.name sadrži niz villa) po općinama (muny.name_2).
-- Dodatno, ako pretpostavimo da smo osjetiljivi na zvuk, uzet ćemo u obzir samo one vile koje su udaljene barem
-- 300 metara od najbliže crkve (buildings.type je church).

-- Za svaku općinu ispišite naziv općine, broj vila, ukupnu kvadraturu vila,
-- te prosječnu udaljenost vila od centra općine (imate funkciju na službenom podsjetniku).
-- Realne brojeve zaokružiti na dvije decimale. Zapise poredati silazno po broju vila.


SELECT name_2 as muny_name
    , COUNT(*) as cnt
    , ROUND(SUM(st_area(buildings.geom))::decimal, 2) as total_area
    , ROUND(AVG(st_distance(buildings.geom, st_centroid(muny.geom)))::decimal, 2) as avg_distance_center                
    
  FROM buildings 
  JOIN muny
         ON st_contains (muny.geom, buildings.geom)
 WHERE name ilike '%villa%'  
   AND (SELECT MIN(st_distance(buildings.geom, church.geom)) 
          FROM buildings church 
         WHERE church.type = 'church') >= 300
 GROUP BY name_2
 ORDER BY cnt DESC