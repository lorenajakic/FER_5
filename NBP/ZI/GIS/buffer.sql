with unutrasnjost as (
    SELECT
        muny.name_2 as muny_name,
    st_buffer(muny.geom, -0.1 * least(ST_XMax(ST_Envelope(muny.geom)) - ST_XMin(ST_Envelope(muny.geom)),
  ST_YMax(ST_Envelope(muny.geom)) - ST_YMin(ST_Envelope(muny.geom)))) as ugeom
    from nbp_gis.muny
     join nbp_gis.muny split
           on split.name_2 = 'Split'
         where st_touches(muny.geom, split.geom)
                or muny.name_2 = 'Split'
)
select muny_name, rest.name --, atm.name, st_distance(atm.geom, rest.geom)
  From unutrasnjost
  join nbp_gis.pois rest
    on rest.fclass = 'artwork'
    and st_contains(unutrasnjost.ugeom, rest.geom)



WITH munys AS (
    SELECT all_muny.*,
           st_buffer(all_muny.geom, -0.1 * LEAST(ST_XMax(ST_Envelope(all_muny.geom)) - ST_XMin(ST_Envelope(all_muny.geom)),
                 ST_YMax(ST_Envelope(all_muny.geom)) - ST_YMin(ST_Envelope(all_muny.geom))
           )) inside_geom
    FROM muny as st_muny
    JOIN muny as all_muny ON st_touches(st_muny.geom, all_muny.geom) OR all_muny.name_2 = 'Split'
    WHERE st_muny.name_2 = 'Split'
)
SELECT munys.name_2, pois.name
FROM munys
JOIN pois ON pois.fclass='artwork' AND st_within(pois.geom, munys.inside_geom)