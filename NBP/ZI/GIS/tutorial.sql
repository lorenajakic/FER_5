-- Print the cummulative area of all schools ('škola' in Croatian):

SELECT SUM(st_area(geom)) 
  FROM buildings 
 WHERE lower(name) like '%škola%';

-- Print all information about named plots (parcels) that touch cemeteries:
SELECT *
  FROM landuse land1, landuse land2
 WHERE land1.name IS NOT NULL
   AND land2.fclass = 'cemetery'
   AND ST_Touches(land1.geom, land2.geom);

-- How many toilets are there in Bundek (park in Zagreb)?
SELECT pois.* 
  FROM pois, landuse
  WHERE st_within(pois.geom, landuse.geom) 
    AND landuse.name = 'Bundek' 
    AND pois.fclass = 'toilet';

-- Print the number and total length of all roads in Bundek:
SELECT count(*),sum( st_length(st_intersection( roads.geom, landuse.geom))) 
  FROM roads, landuse
 WHERE landuse.name = 'Bundek'
   AND st_intersects(roads.geom, landuse.geom);

--  Print areas (landuse) that have at least 10 cafes or bars, descending by the number of cafes/bars:
  SELECT landuse.gid, landuse.name, count(*) as noOfPoints
    FROM pois, landuse
   WHERE st_within(pois.geom, landuse.geom) 
     AND pois.fclass in ('cafe', 'bar')
GROUP BY landuse.gid, landuse.name
  HAVING count(*) > 10
ORDER BY noOfPoints desc;

-- Print data for all buildings that are located less than 500 meters away from the Murter placemark (point):
SELECT buildings.*
  FROM places p1, buildings  
 WHERE p1.name = 'Murter'
   AND st_distance(p1.geom, buildings.geom)  < 500;
