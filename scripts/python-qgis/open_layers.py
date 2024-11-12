# Start the QGIS application
from qgis.core import (
    QgsApplication, 
    QgsDataSourceUri, 
    QgsVectorLayer, 
    QgsProject
)
import json

BASE = "E:/codes/cadastre_synth_maps"

STYLES_FOLDER = BASE + "/styles"
DEFAULT_STYLE = "style1" #It's just a default style to initialized the project, not used in the crop script

# Open credentials file and set variables
with open(BASE + '\config\credentials.json', encoding="utf-8") as f:
    credentials = json.load(f)
database_name = credentials['DB_NAME']
host = credentials['HOST']
port = credentials['PORT']
user = credentials['USER']
password = credentials['PASSWORD']
schema = credentials['DEFAULT_SCHEMA']
target_crs = credentials['PROJECT_CRS']
project = credentials['PROJECT_NAME']

# Define the layers configuration
layers = [
    {"schema": "public", "table": "feuille", "geom_name": "geom", "key": "id"}, 
    {"schema": "public", "table": "surfacehydrographique", "geom_name": "geom", "key": "id"},
    {"schema": "public", "table": "parcelle", "geom_name": "geom", "key": "id"}, 
    {"schema": "public", "table": "coursdeau", "geom_name": "geom", "key": "id"},
    {"schema": "public", "table": "batiment", "geom_name": "geom", "key": "id"},
    {"schema": "public", "table": "tronconderoute", "geom_name": "geom", "key": "id"},
    {"schema": "public", "table": "lieuditnonhabite", "geom_name": "geom", "key": "id"},
    {"schema": "public", "table": "localisant", "geom_name": "geom", "key": "id"},
    {"schema": "temporary", "table": "zones", "geom_name": "geom", "key": "id_zone"},
]

# Define the PostGIS connection parameters
postgis_connection = {
    'host': host,       
    'port': port,       
    'database': database_name,
    'user': user,  
    'password': password 
}

# Set default projection of the project
QgsProject.instance().setCrs(QgsCoordinateReferenceSystem(2154))

# Load each layer and apply its style
for layer_info in layers:
    # Construct the PostGIS URI
    uri = QgsDataSourceUri()
    uri.setConnection(
        postgis_connection['host'], 
        postgis_connection['port'], 
        postgis_connection['database'], 
        postgis_connection['user'], 
        postgis_connection['password']
    )
    uri.setDataSource(layer_info["schema"], layer_info["table"], layer_info["geom_name"], "", layer_info["key"])
    
    # Create the layer
    layer = QgsVectorLayer(uri.uri(), layer_info["table"], "postgres")
    
    if not layer.isValid():
        print(f"Layer {layer_info['table']} failed to load!")
        continue

    # Add the layer to the project
    QgsProject.instance().addMapLayer(layer)

    # Construct the style file path
    qml_path = STYLES_FOLDER + "/" + DEFAULT_STYLE + f"/{layer_info['table']}.qml"
    
    # Load the QML style if the file exists
    if os.path.exists(qml_path):
        layer.loadNamedStyle(qml_path)
        layer.triggerRepaint()
        print(f"Loaded layer {layer_info['table']} with style from {qml_path}")
    else:
        print(f"Style file {qml_path} not found for layer {layer_info['table']}")