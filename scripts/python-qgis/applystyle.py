import os
from qgis.core import QgsProject

BASE = "E:/codes/cadastre_synth_maps"

# Define the directory where the QML files are located
qml_directory = BASE + "/styles/" + "style5bis"

# Get the current project
project = QgsProject.instance()

# Iterate over all layers in the project
for layer in project.mapLayers().values():
    # Construct the expected QML file path
    qml_file_path = os.path.join(qml_directory, f"{layer.name()}.qml")
    
    # Check if the QML file exists
    if os.path.exists(qml_file_path):
        try:
            # Apply the QML style to the layer
            layer.loadNamedStyle(qml_file_path)
            layer.triggerRepaint()  # Refresh layer after applying style
            print(f"Applied style from {qml_file_path} to layer '{layer.name()}'")
        except Exception as e:
            print(f"Failed to apply style to layer '{layer.name()}': {e}")
    else:
        print(f"No QML file found for layer '{layer.name()}'")