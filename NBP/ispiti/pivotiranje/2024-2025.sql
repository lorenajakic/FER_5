-- Za uplate iz 2020 godine, ispisati za sve pakete uplaćene iznose po mjesecima.


CREATE TEMP TABLE pivotTemp
(month INT);
INSERT INTO pivotTemp
SELECT generate_series(1, 12);

SELECT * 
FROM crosstab ('
SELECT packId, packname, EXTRACT(YEAR FROM paymentDateTime) paidYear, EXTRACT(MONTH FROM paymentDateTime)
    , SUM(paidAmount) amountInYear
  FROM payment
  NATURAL JOIN pack
               WHERE EXTRACT(YEAR FROM paymentDateTime) = 2020
   GROUP BY packId, packname, EXTRACT(YEAR FROM paymentDateTime) , EXTRACT(MONTH FROM paymentDateTime)
  ORDER BY packId, packname, EXTRACT(YEAR FROM paymentDateTime) , EXTRACT(MONTH FROM paymentDateTime)
			   '

               , 'SELECT DISTINCT month FROM pivotTemp ORDER BY month')  
    AS pivotTable (packId int, packName VARCHAR(20), paidyear NUMERIC
               , January     NUMERIC
               , February    NUMERIC
               , March       NUMERIC
               , April       NUMERIC
               , May         NUMERIC
               , June        NUMERIC
               , July        NUMERIC
               , August      NUMERIC
               , September   NUMERIC
               , October     NUMERIC
               , November    NUMERIC
               , December    NUMERIC);