CREATE TYPE trackT AS 
(trackId INTEGER, 
 trackTitle VARCHAR(50));
                    
SELECT COUNT(*)  noOfTracks, CastCrewName,  Array_agg((trackId, trackTitle)::trackT) tracks
  FROM (SELECT trackId, trackTitle, CastCrewName
          FROM track  
	         , unnest (castAndCrew) CastCrewName) trackCastAndCrew
GROUP BY CastCrewName
ORDER BY noOfTracks desc, CastCrewName
LIMIT 20