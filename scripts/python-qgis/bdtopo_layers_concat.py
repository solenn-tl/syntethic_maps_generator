# Start the QGIS application
from qgis.core import (
    QgsApplication, 
    QgsDataSourceUri, 
    QgsVectorLayer, 
    QgsProject
)
import json

#Variables you have to set
BASE = "E:/codes/cadastre_synth_maps"
table_to_treat = 'lieuditnonhabite'
departements_codes = [51,75,77,91,92,93,94]

# Layers configuration (MEMO to set table_to_treat value)
layers = [
    {"schema": "public", "table": "departement", "geom_name": "geom", "key": "id"},
    {"schema": "bdtopo_tmp", "table": "surfacehydrographique", "geom_name": "geom", "key": "id"},
    {"schema": "bdtopo_tmp", "table": "coursdeau", "geom_name": "geom", "key": "id"},
    {"schema": "bdtopo_tmp", "table": "tronconderoute", "geom_name": "geom", "key": "id"},
    {"schema": "bdtopo_tmp", "table": "lieuditnonhabite", "geom_name": "geom", "key": "id"},
]

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

# Construct the PostGIS URI
uri = QgsDataSourceUri()
uri.setConnection(
    postgis_connection['host'], 
    postgis_connection['port'], 
    postgis_connection['database'], 
    postgis_connection['user'], 
    postgis_connection['password']
)
    
uri.setDataSource('public', 'departement', 'geom', "", 'id')
layer = QgsVectorLayer(uri.uri(), "departement", "postgres")
QgsProject.instance().addMapLayer(layer)

clipped_layers = []
# Load each layer and apply its style
for layer_info in departements_codes:

    uri.setDataSource("bdtopo_tmp", table_to_treat + '_d0' + str(layer_info), "geom", "", "id")
    # Create the layer
    layer = QgsVectorLayer(uri.uri(), "bdtopo_tmp." + table_to_treat + '_d0' + str(layer_info), "postgres")
    
    if not layer.isValid():
        print(f'Layer {"bdtopo_tmp." + table_to_treat + "_d0" + str(layer_info)} failed to load!')
        continue

    # Add the layer to the project
    QgsProject.instance().addMapLayer(layer)
    
    # Load the required layers
    departement_layer = QgsProject.instance().mapLayersByName("departement")[0]

    # Step 1: Select the feature in 'departement' where insee_dep = '94'
    expression = QgsExpression(f"code_insee = '{layer_info}'")
    selection = departement_layer.getFeatures(QgsFeatureRequest(expression))

    # Apply the selection
    departement_layer.selectByExpression(f"code_insee = '{layer_info}'")

    # Get the selected feature geometry for clipping
    selected_features = departement_layer.selectedFeatures()
    if not selected_features:
        print("No feature with insee_dep = '94' found in the 'departement' layer.")
    else:
        # Get the first selected feature's geometry
        dep_geometry = selected_features[0].geometry()

        clipped_layer_name = "clipped_lieuditnonhabite" + '_' + str(layer_info)

        # Step 2: Create an in-memory layer to store the clipped results
        clipped_layer = QgsVectorLayer("Point?crs=" + layer.crs().authid(), 
                                    clipped_layer_name, "memory")
        clipped_layer_data = clipped_layer.dataProvider()
        
        # Add the fields from the original lieuditnonhabite layer to the clipped layer
        clipped_layer_data.addAttributes(layer.fields())
        clipped_layer.updateFields()
        
        # Step 3: Iterate over features in 'lieuditnonhabite' and add those intersecting 'dep_geometry' to the new layer
        for feature in layer.getFeatures():
            if feature.geometry().intersects(dep_geometry):
                # If it intersects, add the feature to the clipped layer
                clipped_layer_data.addFeature(feature)

        # Step 4: Add the clipped layer to the project
        QgsProject.instance().addMapLayer(clipped_layer)
        crs = layer.crs()
        print("Clipping process complete, and the clipped layer has been added to the project.")
        clipped_layers.append(clipped_layer)
        QgsProject.instance().removeMapLayer(QgsProject.instance().mapLayersByName("bdtopo_tmp." + table_to_treat + '_d0' + str(layer_info))[0])

# Create a list of the clipped layers to be merged
clipped_layer_uris = [layer.source() for layer in clipped_layers]

# Step 5: Merge the clipped layers
merged = processing.run("native:mergevectorlayers", {
    'LAYERS': clipped_layers,  # Use the QgsVectorLayer objects directly
    'CRS': QgsCoordinateReferenceSystem('EPSG:2154'),
    'OUTPUT': 'TEMPORARY_OUTPUT'
})

print(uri)
# Get the merged layer and add it to the project
merged_layer = merged['OUTPUT']
QgsProject.instance().addMapLayer(merged_layer)

print("Merging complete.") 
#♠You still have to add the layer "Fusionné" into the database manually !!! 
