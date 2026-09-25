SELECT * 
  FROM crosstab ($$ SELECT ownerId, firstName, lastName, EXTRACT (YEAR FROM viewStartDateTime), count(*)  
                      FROM owner  
			               NATURAL JOIN trackview
			         WHERE NOT EXISTS (SELECT * 
					   	                 FROM ownerPack 
									    WHERE ownerPack.ownerId = owner.ownerId
									      AND UPPER(ownerPackPeriod) IS NULL)
                    GROUP BY ownerId, EXTRACT (YEAR FROM viewStartDateTime)
                    ORDER BY ownerId, EXTRACT (YEAR FROM viewStartDateTime) 
				 $$
               , $$ SELECT DISTINCT EXTRACT (YEAR FROM viewStartDateTime)  
				      FROM trackView 
				    ORDER BY EXTRACT (YEAR FROM viewStartDateTime) $$) 
               AS pivotTable (ownerId INT, firstName VARCHAR(20), lName VARCHAR(20) 
                            , y2016 int, y2017 int, y2018 int, y2019 int, y2020 int, y2021 int);
