-- Za svaku općinu (muny.name_2) želimo doznati koliko su udaljena križanja cesta (roads) i željezničkih pruga (railways) iz te općine od najbliže bolnice (pois.fclass='hospital').
-- Općenito, u nekoj općini može biti više križanja cesta i pruge, a mi za svako želimo naći udaljenost do najbliže bolnice.

-- Dakle, za svaku općinu i njeno križanje ispisati: ime općine, identifikatore ceste i željezničke pruge, naziv najbliže bolnice i udaljenost do te bolnice zaokruženu na cijeli broj. Nije potrebno ispisivati općine koje nemaju križanja


SELECT name_2,roads_gid, railways_gid, hospital_name, round(dist) as distance
 FROM (

SELECT    muny.name_2
        , roads.gid as roads_gid
        , railways.gid as railways_gid
        , pois.name as hospital_name
        , st_distance(pois.geom, st_intersection(railways.geom, roads.geom)) as dist
        , row_number() over (partition by muny.name_2, railways.gid, roads.gid order by st_distance ( st_intersection(railways.geom, roads.geom), pois.geom)) as rn 
  FROM railways
  JOIN roads 
    ON st_crosses(railways.geom, roads.geom)
  JOIN muny 
    ON st_contains(muny.geom, st_intersection(railways.geom, roads.geom))
       and st_intersects(muny.geom, railways.geom)  -- da ubrzam
       -- and st_intersects(muny.geom, roads.geom)  
       -- and muny.id_1 = 16 -- da ubrzam
  JOIN pois
    ON pois.fclass = 'hospital'
) a
WHERE rn = 1
ORDER BY 1, 2, 3, rn