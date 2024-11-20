import pandas as pd
from shapely.wkt import loads, dumps
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
import geopandas as gpd
import numpy as np
from PIL import Image
import ast
import glob

BASE = "E:/codes/cadastre_synth_maps"
OUTPUT = BASE + "/outputs"

imgs = sorted(glob.glob(OUTPUT + "/*.jpg"))

for img in imgs[:3]:

    image_path = img
    csv_path = img.replace(".jpg", ".csv").replace("region", "prov_region")
    output_csv = img.replace(".jpg", ".csv").replace("region", "processed_region")
    WRLD = img.replace(".jpg", ".wld")
    gpkg = img.replace(".jpg", ".gpkg")

    #Load the wld file
    f = open(WRLD, "r")
    lines = f.readlines()
    f.close()

    df = pd.read_csv(csv_path)

    # Parameters
    origin_x, origin_y = float(lines[4]), float(lines[5])  # Replace with your Lambert 93 origin (top-left corner)
    print(origin_x, origin_y)
    area_width, area_height = 662, 662  # Area size in meters
    image_width, image_height = 2000, 2000  # Image size in pixels
    pixel_size_x = area_width / image_width  # Pixel size in meters
    pixel_size_y = area_height / image_height
    extent = box(0, 0, image_width, image_height)  # Image extent as a Shapely box

    # Step 2: Merge polygons by group_key and concatenate labels
    def merge_polygons(group):
        merged_polygon = unary_union([loads(geom) for geom in group["geometry"]])
        concatenated_labels = "".join(map(str, group["label"]))
        feature_id = group["feature_id"].iloc[0]
        group_id = group["group_id"].iloc[0]
        group_key = group["group_key"].iloc[0]
        feature_label = group["feature_label"].iloc[0]
        layer = group["layer"].iloc[0]
        return pd.Series({"feature_id":feature_id,
                        "group_id":group_id,
                        "label": concatenated_labels,
                        "feature_label":feature_label,
                        "layer":layer,
                        "geometry": merged_polygon,
                        })

    merged_df = df.groupby("group_key").apply(merge_polygons).reset_index()

    # Get the enveloppe of each multipolygon (oriented bbox)
    def get_enveloppe(geometry):
        return geometry.convex_hull

    merged_df["geometry"] = merged_df["geometry"].apply(get_enveloppe)

    # Step 3: Truncate polygons outside the extent
    #Create the extent of the image usign origin_x, origin_y, pixel_size_x, pixel_size_y
    geoextent = box(origin_x, origin_y, origin_x + image_width * pixel_size_x, origin_y - image_height * pixel_size_y)

    def truncate_polygon(geometry):
        return geometry.intersection(geoextent)  # Truncate to the extent

    merged_df["geometry"] = merged_df["geometry"].apply(truncate_polygon)

    #Create a shapefile
    gdf = gpd.GeoDataFrame(merged_df, geometry='geometry')
    gdf.crs = "EPSG:2154"
    gdf.to_file(gpkg,driver="GPKG")

    # Step 4: Translate geographical coordinates to image coordinates
    def translate_to_image_coords(geometry):
        def transform_coords(x, y):
            # Translate Lambert 93 to image coordinates
            pixel_x = (x - origin_x) / pixel_size_x
            pixel_y = (origin_y - y) / pixel_size_y  # Reverse Y for image coords (bottom-left origin)
            return pixel_x, pixel_y

        transformed_polygon = Polygon([transform_coords(x, y) for x, y in geometry.exterior.coords])
        return transformed_polygon

    merged_df["geometry"] = merged_df["geometry"].apply(translate_to_image_coords)

    # Step 5: Save the resulting data
    merged_df["geometry"] = merged_df["geometry"].apply(dumps)  # Convert Shapely geometry to WKT

    #Wkt to list of list
    def wkt_to_list(wkt):
        return list(loads(wkt).exterior.coords)

    merged_df["geometry"] = merged_df["geometry"].apply(wkt_to_list)

    #Replace ( and ) by [ and ]
    def replace_parenthesis(coords):
        return str(coords).replace("(", "[").replace(")", "]")

    merged_df["geometry"] = merged_df["geometry"].apply(replace_parenthesis)

    merged_df = merged_df.astype(str)
    merged_df.to_csv(output_csv, index=False)