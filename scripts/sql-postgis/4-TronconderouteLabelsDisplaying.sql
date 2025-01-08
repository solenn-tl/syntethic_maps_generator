/* This script has been produced with Chat GPT 4 using the follwing prompt

I'm a GIS data scientist.
I want to edit a layer "tronconderoute" which contains roads (LineString). 
I also have a layer "zones" in schema "temporary" which contains squares (Polygon).
The task is as follows: for each line string, I want to fill a new column "reference_zone" with the "id_zone" attribute of the "zones" layer in which the line string in question has its largest part.
I use Postgres with Postgis extension.
*/

-- Step 1: Ensure spatial indexes exist
CREATE INDEX IF NOT EXISTS idx_zones_geom ON temporary.zones USING GIST (geom);

-- Step 2: Create a temporary table to store intersection lengths
DROP TABLE IF EXISTS temporary.temp_intersection_lengths;
CREATE TABLE temporary.temp_intersection_lengths (
    id_troncon SERIAL,
    id_zone INT,
    troncon_id INT,
    zone_id INT,
    intersected_length DOUBLE PRECISION
);

-- Step 3: Populate the temporary table with intersection lengths
INSERT INTO temporary.temp_intersection_lengths (troncon_id, zone_id, intersected_length)
SELECT 
    t.id AS troncon_id,
    z.id AS zone_id,
    ST_Length(ST_Intersection(t.geom, z.geom)) AS intersected_length
FROM 
    tronconderoute t
JOIN temporary.zones z ON ST_Intersects(t.geom, z.geom)
WHERE t.nom_ban_g IS NOT NULL;

-- Step 4: Identify the zone with the largest intersected length for each Linestring
-- Appartenance d'un tronçon à une unique zone (plus grande longueur)
CREATE TABLE temporary.max_intersection_lengths AS
WITH maxi AS (SELECT troncon_id, MAX(intersected_length) AS intersected_length
FROM temporary.temp_intersection_lengths
GROUP BY troncon_id)
SELECT t.* 
FROM temporary.temp_intersection_lengths AS t
INNER JOIN maxi ON ( maxi.troncon_id = t.troncon_id AND maxi.intersected_length = t.intersected_length);

CREATE TABLE temporary.tronconderoute_zoneid AS
	SELECT t.*, tmp.zone_id, tmp.intersected_length
	FROM tronconderoute AS t
	LEFT JOIN temporary.max_intersection_lengths AS tmp ON t.id = tmp.troncon_id;

CREATE TABLE temporary.count_num_troncon_by_nom_ban_g AS 
	SELECT t.nom_ban_g, t.zone_id, COUNT(t.id)
	FROM temporary.tronconderoute_zoneid AS t
	WHERE t.nom_ban_g is not null
	GROUP BY t.nom_ban_g, t.zone_id
	ORDER BY t.nom_ban_g DESC;

CREATE TABLE temporary.tronconderoute_zoneid_count_items AS 
	SELECT t.*, c.count AS count
	FROM temporary.tronconderoute_zoneid AS t
	LEFT JOIN temporary.count_num_troncon_by_nom_ban_g AS c ON (t.nom_ban_g = c.nom_ban_g AND t.zone_id = c.zone_id);

CREATE TABLE temporary.max_intersection_length_by_name AS 
	SELECT t.nom_ban_g, t.zone_id, MAX(intersected_length)
	FROM temporary.tronconderoute_zoneid_count_items AS t
	WHERE t.nom_ban_g is not null
	GROUP BY t.nom_ban_g, t.zone_id
	
CREATE TABLE temporary.tronconderoute_zoneid_count_items_max AS
	SELECT t.*, m.max
	FROM temporary.tronconderoute_zoneid_count_items as t
	LEFT JOIN temporary.max_intersection_length_by_name AS m ON (t.nom_ban_g = m.nom_ban_g AND t.zone_id = m.zone_id AND t.intersected_length = m.max);