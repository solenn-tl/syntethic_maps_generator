/*Treat "numero" to remove the 0 before the real plot number*/
CREATE INDEX numero_idx ON localisant(numero);
ALTER TABLE localisant ADD COLUMN numero_court character varying(5);
UPDATE localisant SET numero_court = regexp_replace(numero, '(0*)([0-9]*)', '\2');

/* Deal with upside down labels */
-- Change tronconderoute
CREATE TABLE tronconderoute2 AS SELECT *,
  CASE WHEN ST_X(ST_StartPoint(geom)) > ST_X(ST_EndPoint(geom)) THEN ST_Reverse(geom)
  ELSE geom
  END AS geom2
  FROM tronconderoute;

ALTER TABLE tronconderoute RENAME TO tronconderoute_old;
ALTER TABLE tronconderoute2 RENAME TO tronconderoute;
ALTER TABLE tronconderoute DROP COLUMN geom;
ALTER TABLE tronconderoute RENAME COLUMN geom2 TO geom;

-- Change coursdeau
CREATE TABLE coursdeau2 AS SELECT *,
  CASE WHEN ST_X(ST_StartPoint(geom)) > ST_X(ST_EndPoint(geom)) THEN ST_Reverse(geom)
  ELSE geom
  END AS geom2
  FROM coursdeau;

ALTER TABLE coursdeau RENAME TO coursdeau_old;
ALTER TABLE coursdeau2 RENAME TO coursdeau;
ALTER TABLE coursdeau DROP COLUMN geom;
ALTER TABLE coursdeau RENAME COLUMN geom2 TO geom;