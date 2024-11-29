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
    QgsMessageLog,
    Qgis,
)
from qgis.utils import iface
import processing  # type: ignore -> automatically imported by QGIS, but prevent "undefined name" errors in the IDE.
from PyQt5.QtCore import QVariant, QSize
from timeit import default_timer as timer
from functools import lru_cache
import time
import pandas as pd
import os 

# All blank spaces and breaks are considered word separators.
WORD_SEPARATORS = [" ", " ","\t", "\n", "\r", "\f", "\v"]

# Should we cut the OOBs to the extent of the region?
CLIP_OOB_TO_REGION = True

# In DEBUG mode, the OOBs layer is kept in the project
DEBUG = False

# Force garbage collection to avoid memory leaks every GC_FREQ iterations
GC_FREQ = 10

BASE = "E:/codes/cadastre_synth_maps"
STYLES_ROOT = BASE + "/styles"

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
        save_labels(output_file, format="gpkg"):
            Saves the extracted labels to a file.
    """

    _labels: QgsVectorLayer = None
    extent: QgsRectangle = None
    _map_settings: QgsMapSettings = None
    _renderer: QgsMapRendererParallelJob = None
    _layers_garbage_collector = []

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

        render = QgsMapRendererParallelJob(map_settings)
        self._map_settings = map_settings
        self._renderer = render

        render.finished.connect(self._extract_labels)

        self._renderer.start()
        self._renderer.waitForFinished()
        self._renderer.deleteLater()

    def _extract_labels(self):
        labeling_results = self._renderer.takeLabelingResults()
        if labeling_results:
            self._labels = self._create_label_layer(
                labeling_results.allLabels(), self.extent
            )

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

    def _create_label_layer(self, labels: list[QgsLabelPosition], region: QgsRectangle):
        """Create a memory layer with the extracted labels."""
        #print(labels)
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
        export = []

        for id, label in enumerate(labels):
        
            if prev is None:
                prev = label

            if prev.labelText != label.labelText or label.featureId != prev.featureId:
                char_id = 0
                prev = label

            if char_id < len(label.labelText) and label.labelText[char_id] in WORD_SEPARATORS:
                group_id += 1
            elif char_id == len(label.labelText):
                continue
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
                features.append(feature)

            char_id += 1
        print(f"There are {len(features)} features in the list features")
        
        header = ["id","feature_id","group_id","element_id","group_key","label","feature_label","layer","geometry"]
        final =[]
        for f in features:
            tmp_e = f.attributes()
            tmp_e.append(f.geometry().asWkt())
            final.append(tmp_e)
        df = pd.DataFrame(final, columns=header)
        df.to_csv(BASE + "/outputs/region.csv",index=False) #Tmp save thas is rename bellow

    def __del__(self):
        print("Cleaning up", len(self._layers_garbage_collector))
        for layer in self._layers_garbage_collector:
            try:
                QgsProject.instance().removeMapLayer(layer)
                layer.deleteLater()
            except RuntimeError:
                pass  # C++ object already deleted

        self._layers_garbage_collector.clear()
        self._renderer.deleteLater()


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


#@lru_cache(maxsize=128)  # Adjust maxsize as needed
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

# if __name__ == "__console__":
"""Run the region extraction process when this script is executed in the QGIS Python console."""

# Use a (hopefully non visible) grid layer as the source for regions
regions_layer = "zones"
regions_layer = QgsProject.instance().mapLayersByName(regions_layer)[0]

exec_times = []

# Each feature of the grid layer is a region to extract
regions = regions_layer.getFeatures()
regions = sorted(regions, key=lambda feature: feature['id'], reverse=False)
old_style = ""
project_layers_names = [l.name() for l in QgsProject.instance().mapLayers().values()]

for ix, region in enumerate(regions):
    if ix >= 5000 and ix < 5005: 
        print(ix)
        center = region.geometry().centroid().asPoint()
        width = region.geometry().boundingBox().width()
        height = region.geometry().boundingBox().height()
        
        id_ = region['id']
        style = region['style']
        style_folder = f'{STYLES_ROOT}/{style}/'
        if style != old_style:
            old_style = style
            for layer_name in project_layers_names:
                # Get the layer by name
                layer = QgsProject.instance().mapLayersByName(layer_name)
                qml_file_path = os.path.join(style_folder, f"{layer_name}.qml")
                if layer:
                    layer = layer[0]  # Get the first layer with the specified name
                    # Load the QML style
                    if layer.loadNamedStyle(qml_file_path):
                        layer.triggerRepaint()  # Refresh the layer to apply changes
                        #print(f"Applied style from '{qml_file_path}' to layer: {layer_name}")
                    else:
                        print(f"Failed to load style from '{qml_file_path}' for layer: {layer_name}.")
                else:
                    print(f"Layer '{layer_name}' not found.")
        
        output = f"{BASE}/outputs/region_{region['id']}.jpg"

        start = timer()
        extractor = RegionExtractor(center, width, height)
        extractor.run()
        extractor.save_image(output)
        
        input_path = f"{BASE}/outputs/region.csv"
        output_path = f"{BASE}/outputs/tmp_region_{region['id']}.csv"
        #Rename this file to the region id
        os.replace(input_path,output_path)

        end = timer()
        exec_times.append(end - start)
        print(f"#{ix} took {(end - start):.2f} seconds")


print(f"Extracted {len(exec_times)} regions")
print(
    f"Average execution time: {sum(exec_times)/len(exec_times):.2f}s (±{np.std(exec_times):.2f}s)"
)
