-- Add a new column for style
ALTER TABLE temporary.zones ADD COLUMN style character varying(10);

-- Step 1: Calculate the total number of rows in `zones` and the count of unique `idstyle` values
WITH
    zone_counts AS (
        SELECT COUNT(*) AS total_zones FROM temporary.zones
    ),
    style_counts AS (
        SELECT COUNT(*) AS total_styles FROM styles
    ),
    
    -- Step 2: Calculate the batch size for each style
    batch_size AS (
        SELECT
            zone_counts.total_zones / style_counts.total_styles AS rows_per_style
        FROM
            zone_counts,
            style_counts
    ),
    
    -- Step 3: Create a row number and assign each zone to a style based on the batch size
    numbered_zones AS (
        SELECT 
            id,
            (ROW_NUMBER() OVER () - 1) / batch_size.rows_per_style AS style_group
        FROM
            temporary.zones, batch_size
    )
    
-- Step 4: Update the zones table in batches by joining with the style groups
UPDATE temporary.zones
SET style = (
        SELECT idstyle
        FROM styles
        ORDER BY idstyle
        LIMIT 1
        OFFSET (SELECT style_group FROM numbered_zones WHERE temporary.zones.id = numbered_zones.id)
    )
;

-- Step 5 : Stort zones by id
CREATE TABLE temporary.zones2 AS SELECT * FROM temporary.zones ORDER BY id;
ALTER TABLE temporary.zones RENAME TO zones_old;
ALTER TABLE temporary.zones2 RENAME TO zones;

-- If empty values in style
UPDATE temporary.zones SET style = 'style1' WHERE style IS NULL;