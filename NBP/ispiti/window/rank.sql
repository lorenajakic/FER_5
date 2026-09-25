--Ispisati podatke za 50 vlasnika korisničkih računa koji su uplatili najviše novca za usluge streaming platforme.
--Rang odredite temeljem ukupnog uplaćenog iznosa - najbolji (najniži) rang pripada onome tko je uplatio najviše novca.
--Dodatno ispišite podatke o ugovorenim paketima tog korisnika (stupac ownerPacks).
--Stupac ownerPacks sadrži ugovorene pakete bez ponavljanja redoslijedom kojim su ugovarani (pomoć - možete ga odrediti pomoću podupita).
--Elementi su mu složenog tipa i sastoje se od:

--packId
--packName
--ownerPackPeriod

CREATE TYPE ownerPackT AS 
(packId INT, packName VARCHAR(20), ownerPackPeriod DATERANGE);
                    
SELECT lastName, firstName
    , rank() OVER (ORDER BY SUM(paidAmount) DESC) rang
    , SUM(paidAmount) totalPaidAmount
    , (SELECT Array_agg((packId, packName, ownerPackPeriod)::ownerPackT) 
         FROM (SELECT packId, packName, ownerPackPeriod 
		         FROM ownerPack
                 NATURAL JOIN Pack
                  WHERE ownerPack.ownerId = owner.ownerId 
		          ORDER BY ownerPackPeriod) ownerPackrTemp
      ) ownerPacks
  FROM payment
  NATURAL JOIN owner
   GROUP BY owner.ownerid, lastName, firstName
  ORDER BY rang
LIMIt 50