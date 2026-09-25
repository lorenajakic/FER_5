--Po godinama, od 2016 do 2021, ispisati naziv medijskog sadržaja i broj pregledavanja.
--Godinu pregledavanja odrediti prema trenutku početka gledanja.
--Ispisati podatke samo za medijske sadržaje u čijem je stvaranju sudjelovao "James Franco" - kao glumac ili u nekoj drugoj ulozi.

--Pomoć: Donjim izrazom se dobije polje od 3 cijela broja, pa na sličan način napišite izraz kojim se dobije polje čiji je element niz znakova (potrebne duljine - provjerite kolika treba biti u opisu baze).


SELECT * FROM crosstab(
              $$
                SELECT tracktitle, extract(year FROM viewstartdatetime) as year, COUNT(*)
                FROM track NATURAL JOIN trackview
                WHERE director @> ARRAY['James Franco']::varchar[] OR castandcrew @> ARRAY['James Franco']::varchar[]
                GROUP BY tracktitle, extract(year FROM viewstartdatetime)
              $$,
              $$
              SELECT DISTINCT extract(year FROM viewstartdatetime) FROM trackview order by extract(year FROM viewstartdatetime)
              $$
              ) AS pivotTable(tracktitle VARCHAR, y2016 INT, y2017 INT, y2018 INT, y2019 INT, y2020 INT, y2021 INT)