"""
Ce script PyQGIS extrait l'image géoréférencée d'une région du canvas cartographique principal,
calcule les boites englobantes orientées de toutes les étiquettes affichées dans la région, et les
exporte sous forme vectorielles au format Geopackage.
**Notes importante**

1. OOB par mot
Dans les mode de placement `Parallel` et `Horizontal`, une seule boite englobante sera crée par étiquette,
même si elle est composée de plusieurs mots.
Par exemple :
+---------------------------------------+
| PASSAGE␣DES␣CHARDONS |
+---------------------------------------+

Seul le mode `Curved` permet de créer une boite englobante par mot.
L'exemple précédent devient :
+--------------+ +--------+ +-------------------+
| PASSAGE |  | DES |  | CHARDONS |
+--------------+ +--------+ +-------------------+

1. Upside Down labels

En raison - probablement - d'un bug dans la construction des objets QgsLabelPosition, les boites
englobantes calculées pour les étiquettes Upside Down sont incorrectes.
Deux solution sont possibles pour contourner ce problème :
- soit forcer l'affichage des étiquettes upside down à `Always` dans le paramétrage `Rendering` des étiquettes.
  Toutefois cela causera potentiellement certaines etiquettes à être affichées à l'envers.
- soit, dans le cas d'une couche linéaire, réordonner les points des LineString de manière à ce qu'elles soient
  toujours orientées dans le sens de la lecture.
  Cela peut être fait en pré-traitement avec la requête SQL :
    SELECT ...,
    CASE WHEN ST_X(ST_StartPoint(geometry)) > ST_X(ST_EndPoint(geometry)) THEN ST_Reverse(geometry)
    ELSE geometry
    END AS geometry
    FROM some_linear_layer;

"""

import numpy as np
from qgis.core import (
    QgsProject,
    QgsRectangle,
    QgsLabelPosition,
    QgsMapRendererParallelJob,
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsMapSettings,
    edit,
    QgsMessageLog,
    QgsGeometry,
    QgsPointXY,
)
from qgis.utils import iface
import processing  # type: ignore -> automatically imported by QGIS, but prevent "undefined name" errors in the IDE.
from PyQt5.QtCore import QVariant, QSize
from timeit import default_timer as timer
from functools import lru_cache
import time 

# All blank spaces and breaks are considered word separators.
WORD_SEPARATORS = [" ", "\t", "\n", "\r", "\f", "\v"]

# Should we cut the OOBs to the extent of the region?
CLIP_OOB_TO_REGION = True

# In DEBUG mode, the OOBs layer is kept in the project
DEBUG = True

STYLES_ROOT = "E:/codes/cadastre_synth_maps/styles"
OUTPUT_FOLDER = "E:/codes/cadastre_synth_maps/outputs_3"

class RegionExtractor:
    """
    A class to extract and save regions from a QGIS map canvas.
    Attributes:
        extent (QgsRectangle): The extent of the region to extract.
        _map_settings (QgsMapSettings): The map settings for rendering.
        _renderer (QgsMapRendererParallelJob): The renderer for the map.
        _labels (QgsVectorLayer): The extracted labels.
    Methods:
        __init__(center, width, height):
            Initializes the RegionExtractor with a center point, width, and height.
        run(dimensions=(2000, 2000)):
            Runs the extraction process with the specified dimensions.
        _extract_labels():
            Extracts labels from the rendered map.
        save_image(output_file, format="jpg", geo=True):
            Saves the rendered image to a file.
        save_labels_geo(output_file, format="gpkg"):
            Saves the extracted labels to a file.
    """

    _labels: QgsVectorLayer = None
    extent: QgsRectangle = None
    _map_settings: QgsMapSettings = None
    _renderer: QgsMapRendererParallelJob = None

    def __init__(self, center: tuple[float, float], width: float, height: float):
        x, y = center
        self.extent = QgsRectangle(
            x - width / 2,
            y - height / 2,
            x + width / 2,
            y + height / 2,
        )

    def run(self, dimensions=(2000, 2000)):
        canvas = iface.mapCanvas()
        map_settings = canvas.mapSettings()
        map_settings.setExtent(self.extent)
        map_settings.setOutputSize(QSize(*dimensions))
        map_settings.setDestinationCrs(QgsCoordinateReferenceSystem.fromEpsgId(2154))

        render = QgsMapRendererParallelJob(map_settings)
        self._map_settings = map_settings
        self._renderer = render

        render.finished.connect(self._extract_labels)

        self._renderer.start()
        self._renderer.waitForFinished()
        self._renderer.deleteLater()

    def _extract_labels(self):
        labeling_results = self._renderer.takeLabelingResults()
        #print(labeling_results.allLabels()) # Check if there are labels
        if labeling_results:
            self._labels = create_label_layer(labeling_results.allLabels(), self.extent)

    def save_image(self, output_file, format="jpg", geo=True):
        of = force_format(output_file, format)
        self._renderer.renderedImage().save(of)

        if geo:
            wld = make_wld(self._renderer.renderedImage().size(), self.extent)
            wldfile = force_format(output_file, "wld")
            with open(wldfile, "w") as f:
                f.write(wld)

    def save_labels_geo(self, output_file, format="gpkg"):
        of = force_format(output_file, format)
        if self._labels:
            processing.run(
                "native:savefeatures",
                {
                    "INPUT": self._labels,
                    "OUTPUT": of,
                },
            )

    def export_for_pipeline(self, output_file, format="csv"):
        """Export the labels in image space to a CSV file with the 4 corners of the bounding box as WKT POINTs.
        This export is intended to produce the output for the next step in the pipeline
        """

        # Use native:affinetransform for this
        if self._labels:
            imsize = self._renderer.renderedImage().size()

            # Apply an affine transformation to the labels to convert them from geo coordinates to image (pixel) coordinates
            scale_x = imsize.width() / self.extent.width()
            scale_y = -imsize.height() / self.extent.height()
            delta_x = -self.extent.xMinimum() * scale_x
            delta_y = -((self.extent.yMinimum() + self.extent.height()) * scale_y)

            labels_imspace = processing.run(
                "native:affinetransform",
                {
                    "INPUT": self._labels,
                    "OUTPUT": "TEMPORARY_OUTPUT",
                    "SCALE_X": scale_x,
                    "SCALE_Y": scale_y,
                    "DELTA_X": delta_x,
                    "DELTA_Y": delta_y,
                },
            )
            labels_imspace = labels_imspace["OUTPUT"]

            # Save the layer to a CSV file using processing
            processing.run(
                "native:savefeatures",
                {
                    "INPUT": labels_imspace,
                    "OUTPUT": force_format(output_file, format),
                    "LAYER_OPTIONS": "GEOMETRY=AS_WKT",
                },
            )


def create_label_layer(labels: list[QgsLabelPosition], region: QgsRectangle):
    """Create a memory layer with the extracted labels."""

    layer_oob = QgsVectorLayer("Polygon?crs=epsg:2154", "oobs", "memory")
    provider = layer_oob.dataProvider()
    provider.addAttributes(
        [
            QgsField("id", QVariant.Int),
            QgsField("feature_id", QVariant.Int),
            QgsField("group_id", QVariant.Int),
            QgsField("element_id", QVariant.Int),
            QgsField("group_key", QVariant.String),
            QgsField("label", QVariant.String),
            QgsField("feature_label", QVariant.String),
            QgsField("layer", QVariant.String),
        ]
    )
    layer_oob.updateFields()

    prev = None
    char_id: int = 0
    group_id = 0

    features = []
    for id, label in enumerate(labels):
        if label.labelGeometry is None:
            print(f"Label ID {id} has no geometry: {label}")

    for id, label in enumerate(labels):
        if prev is None:
            prev = label

        if prev.labelText != label.labelText or label.featureId != prev.featureId:
            char_id = 0
            prev = label

        print(label.labelText)
        print(char_id)
        print(len(label.labelText))
        if label.labelText[char_id] in WORD_SEPARATORS:
            group_id += 1
        else:
            is_curved = label.groupedLabelId != 0  # Non zero if in a curved label.
            oob = label.labelGeometry
            
            feature = QgsFeature()
            feature.setGeometry(oob)
            feature.setAttributes(
                [
                    id,
                    label.featureId,
                    group_id,
                    char_id,
                    f"{label.featureId}-{group_id}",
                    label.labelText[char_id] if is_curved else label.labelText,
                    label.labelText,
                    # Get the layer name from the label.layerID
                    get_layer_name(label.layerID),
                ]
            )
            print(feature.geometry())
            features.append(feature)
            print(len(features))
        char_id += 1
    
    provider.addFeatures(features)
    print(f"Provider has {provider.featureCount()} features")
    
    # Adding the layer to the project is required to run SQL queries on it.
    QgsProject.instance().addMapLayer(layer_oob)

    # Run an SQL query on the scratch layer layer_oob to merge all polygons
    #  with the same group_key and concatenate the labels
    labels_obbs = processing.run(
        "qgis:executesql",
        {
            "INPUT_DATASOURCES": [layer_oob],
            "INPUT_QUERY": """
                SELECT  id,
                ST_OrientedEnvelope(ST_BUFFER(ST_Union(geometry), 0)) as geometry,
                STRING_AGG(label, '') AS texte,
                feature_label AS texte_complet,
                layer AS nature
                FROM oobs
                GROUP BY group_key
            """,
            "OUTPUT": "TEMPORARY_OUTPUT",
        },
    )
    labels_obbs = labels_obbs["OUTPUT"]
    
    
    if CLIP_OOB_TO_REGION:
        labels_obbs = processing.run(
            "native:extractbyextent",
            {
                "INPUT": labels_obbs,
                "EXTENT": region,
                "CLIP": True,
                "OUTPUT": "TEMPORARY_OUTPUT",
            },
        )
        labels_obbs = labels_obbs["OUTPUT"]
        
        # native:extractbyextent returns multi-part geometries to handle spcial cases
        # where the OOBs are cut in several parts by the region extent
        # We absolutely don't want that, so we force the geometries to be single part
        labels_obbs = processing.run(
            "native:multiparttosingleparts",
            {
                "INPUT": labels_obbs,
                "OUTPUT": "TEMPORARY_OUTPUT",
            },
        )
        labels_obbs = labels_obbs["OUTPUT"]
        

    if not DEBUG:
        # Drop the temporary OOB layer so it doesn't clutter the project
        QgsProject.instance().removeMapLayer(layer_oob)

    return labels_obbs


def make_wld(image_dims: QSize, world_dims: QgsRectangle):
    """Create a world file for a given image and map extent."""

    # bbox is the bounding box of the map extent
    bbox = world_dims

    # Calculate pixel size in the x and y directions
    # Note: pixel size in y is negative in the world file
    pixel_size_x = bbox.width() / image_dims.width()
    pixel_size_y = -bbox.height() / image_dims.height()

    # Upper-left corner coordinates
    upper_left_x = bbox.xMinimum()
    upper_left_y = bbox.yMaximum()

    wld_dat = [
        pixel_size_x,  # Pixel size in the x direction
        0.0,  # Rotation term (usually 0)
        0.0,  # Rotation term (usually 0)
        pixel_size_y,  # Pixel size in the y direction (negative)
        upper_left_x,  # X coordinate of the upper-left corner
        upper_left_y,  # Y coordinate of the upper-left corner
    ]

    wld_str = "\n".join([f"{x:.10f}" for x in wld_dat])

    return wld_str


# Utility functions


#@lru_cache(maxsize=250)  # Adjust maxsize as needed
def get_layer_name(layer_id):
    """Retrieve the name of the layer by its ID, with caching."""
    layer = QgsProject.instance().mapLayer(layer_id)
    if layer:
        return layer.name()
    else:
        raise ValueError(f"Layer with ID {layer_id} not found.")


def force_format(file, format):
    """Force file to be <file>.<format>, whatever the extension of file.
    Any existing extension will be replaced by format."""
    if "." in file:
        file, _ = file.rsplit(".", 1)
    file = f"{file}.{format}"

    return file


# --- Main script ---

if __name__ == "__console__":
    """
    Run the region extraction process when this script is executed in the QGIS Python console.
    """

    # Use a (hopefully non visible) grid layer as the source for regions
    regions_layer = "zones"
    regions_layer = QgsProject.instance().mapLayersByName(regions_layer)[0]

    exec_times = []

    # Each feature of the grid layer is a region to extract
    regions = regions_layer.getFeatures()
    regions = sorted(regions, key=lambda feature: feature['id'], reverse=False) #sort the squares by id

    old_style = ""
    project_layers_names = [l.name() for l in QgsProject.instance().mapLayers().values()]

    for ix, region in enumerate(regions):
        if ix <= 10:    
            center = region.geometry().centroid().asPoint()
            width = region.geometry().boundingBox().width()
            height = region.geometry().boundingBox().height()
            
            id_ = region['id']
            style = region['style']
            style_folder = f'{STYLES_ROOT}/{style}/'
            if style != old_style:
                for layer_name in project_layers_names:
                    # Get the layer by name
                    layer = QgsProject.instance().mapLayersByName(layer_name)
                    qml_file_path = os.path.join(style_folder, f"{layer_name}.qml")
                    if layer:
                        layer = layer[0]  # Get the first layer with the specified name
                        # Load the QML style
                        if layer.loadNamedStyle(qml_file_path):
                            layer.triggerRepaint()  # Refresh the layer to apply changes
                            print(f"Applied style from '{qml_file_path}' to layer: {layer_name}")
                        else:
                            print(f"Failed to load style from '{qml_file_path}' for layer: {layer_name}.")
                    else:
                        print(f"Layer '{layer_name}' not found.")

            output = f"{OUTPUT_FOLDER}/region_{id_}.jpg"
            
            start = timer()
            extractor = RegionExtractor(center, width, height)
            extractor.run()
            extractor.save_image(output)
            extractor.save_labels_geo(output)
            extractor.export_for_pipeline(output)
            end = timer()
            exec_times.append(end - start)
            print(f"#{ix} took {(end - start):.2f} seconds")
            #QgsProject.instance().removeMapLayer(QgsProject.instance().mapLayersByName("oobs")[0])#Delete the temporary layer

    print(f"Extracted {len(exec_times)} regions")
    print(
        f"Average execution time: {sum(exec_times)/len(exec_times):.2f}s (±{np.std(exec_times):.2f}s)"
    )
