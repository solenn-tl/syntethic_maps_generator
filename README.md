# A synthetic cadastral index maps generator using real geographical data

This repository contains a tool to generate images of cadastral index maps annotated from text detection, text recognition and text classification tasks. These images can be used to (pre)train a text recognition model on old cadastral index maps of comparable style.

This pipeline has been developped with data of the French National Mapping Agency (IGN), using geographical features of the French land registry and of topographic databases. It as been designed to make it adaptable to other kind of maps nor data.

## Requirements
* Python (tested with Python 3.12.0)
* Postgres with PostGIS (tested with Postgres 16 and PostGIS )
* QGIS using OS4GeoW (tested with QGIS 3.38 Grenoble with Python 3.12)

## 0. Setup
* Create a Python Virtual Environnement 
* Execute ```setup.sh``` :
    * Create the ```data``` and ```outputs``` folders.
    * Install the libraries using ```requirements.txt```
* Check environnement variables : 
    * Windows : 
* Open the ```config/credentials.json``` and start to adapt it to your situation. You might have to update it with the database infos.
* Create a geographical database. In our case, it is named "cadastre". To create the database, you can use the ```scripts/sql-postgis/0-InitDatabase.sql``` script, copied into pgAdmin console or execute the ```scripts/python/0_prepare_db.py``` script. (! For this step, the name of the database is set into ```scripts/sql-postgis/0-InitDatabase.sql``` script, it doesn't use the ```credentials.json``` parameters !)
* Download and install the fonts listed in ```fonts```
* In QGIS, add connexion to your newly created database

## 1. Download data

For the cadastral index maps, we choose to use geographical data that also appears in the 19th century maps.
The downloaded data of each database (BDTOPO and PCI-EXPRES) have to be unzipp in the associated folder in the ```data``` folder.
Data are stored by departements. You have to list the departements that you want to use to generate the images at this step. You can update the ```config/your-project-name/areas.json``` file with your list of places.

In our example, we use the following French departements : 
* Marne (51)
* Paris (75)
* Seine-et-Marne (77)
* Essonne (91)
* Hauts-de-Seine (92)
* Seine-Saint-Denis (93)
* Val-de-Marne (94)

Using the downloaded data, you also can update the ```config/your-project-name/layers.json```.

### Parcellaire Express (PCI) data
Parcellaire Express (PCI-Express) data, specific to the land registry, can be downloaded by department from the IGN website: https://geoservices.ign.fr/parcellaire-express-pci
Choose one or many departements and download their associated folder. Once the folder has been downloaded and unzipped, we'll use the following files:
* *feuille.shp* (extent of a cadastral index map)
* *parcelle.shp* (plots of lands)
* *localisant.shp* (ponctual geometries representing the centroid of each plot)
* *batiment.shp* (buildings)

### BD TOPO data 
BD TOPO data (topographic data) can be downloaded by French Department from the IGN website: https://geoservices.ign.fr/bdtopo
Once the download folder has been unzipped, we'll use the following files:
* *departement.shp* (used for pre-treaments)
* *cours_d_eau.shp* (watersays as linestrings)
* *surface_hydrographique.shp* (pieces of water and waterways as surfaces)
* *troncon_de_route.shp* (roads and ways)
* *lieu_dit_non_habité.shp* (named place in inhabited areas). *For this one, we don't add data from departement 75 (it contains only duplicated street names from troncon_de_route)*

The layers *cours_d_eau.shp*, *surface_hydrographique.shp*, *lieu_dit_non_habité.shp* and *troncon_de_route.shp* contains a buffer of data of neighboring departements. A treatement step to remove them will be performed (to avoid overlaping labels on the maps).

## 2. Loading data into DB
* Execute the script ```python/1_create_styles_table.py``` in the Python console:
    - it will load the *style.csv* file into the database.
* Use the ```python/2_load_layers_into_db.py``` script and set the *BASE* variable depending on your situation. This script will :
    - Load the shape of each selected departement.
    - Load the data from PCI-EXPRESS.
    - Load the data from BDTOPO into tables in the *bdtopo_tmp* schema. Features from *departement* SHP are added to a layer *departement* of the public schema.
* The data from BDTOPO in *bdtopo_tmp* schema have to be cut and merged. The script ```python-qgis/bdtopo_layers_concat``` execute the following process for one kind of layer (executed in Python console of QGIS).
    - For each layer of each departement (*cours_d_eau.shp*, *surface_hydrographique.shp*, *lieu_dit_non_habité.shp*, *troncon_de_route.shp*), the layer is cut using the departement shape (to delete the data that are not in the treated departement).
    - Each group of layers of the same type (ex : *cours_d_eau.shp*) is merged.
    - The resultant layer is pushed into the database using QGIS loader into Postgis.
    - Finally, you have to add the resultant layer into the database using QGIS loader.
* In PgAdmin, execute the script ```sql-postgis/1-SomeTreaments.sql``` to make some final pre-treaments on the layers.

## 3. Create the images extent
* Execute the ```sql-postgis/2-CreateZones.sql``` into PgAdmin console to generate squares of 662x662 meters that correspond to images of 2000x2000 pixels representing the geographical features at a scale of 1:1250 :
    - it creates 2 tables in the ```temporary``` schema of the database :
        - ```zone_name``` (full grid over the extent of the considered area)
        - ```zones``` who contains only the squares of the grid that are completly covered by the geometries of the ```feuille``` table.
    - you can copy/paste additionnal squares from ```zone_name``` to ```zones``` using QGIS depending on the areas you want in your dataset, accepting gaps between the features of the ```feuille``` table.
* Execute the script ```sql-postgis/3-AttributeAStyle.sql``` into PgAdmin console: 
    - it will attribute a style to each square of the grid using the ```styles/styles.csv``` file.

## 4. Generate synthetic maps
* Open QGIS. In QGIS, open the Python console.
* Open the script ```python-qgis/open-layers.py``` into the QGIS Python console:
    - Run it. it will load layers from the database into the project.
* You can visualize the styles on QGIS using the script ```python-qgis/applystyle.py```.
* Open the ```python-qgis/crop.py``` script into QGIS Python console:
    - It will create the images an export he ground-truth annotations in ```.gpkg``` and ```.csv``` format

## 5. Export images metadata
* The layer ```zones``` in the schema ```temporary``` of the database contains metadata about each images including their geographical coordinates, applied style and identifier (same as the name of the images).
* It can be exported as a Geojson or a CSV using QGIS export tools.

## ICDAR 2025 competition

## Citation
