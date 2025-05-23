# A synthetic cadastral index maps generator using real geographical data

Authors : Nathalie Abadie, Bertrand Duménieu, Solenn Tual

This repository contains a tool to generate images of cadastral index maps annotated for text detection, text recognition and text classification tasks. These images can be used for pre-training.

This pipeline has been developed with data from the French National Mapping Agency (IGN), using geographical features from the French land registry and topographic databases. It has been designed to be adaptable to other types of maps and data.

## Requirements
* Python (tested using Python 3.12.0)
* Postgres with PostGIS (tested with Postgres 16 and PostGIS)
* QGIS with OS4GeoW (tested with QGIS 3.38 Grenoble using Python 3.12)

## 0. Setup
* Create a Python virtual environment 
* Run ```setup.sh```:
    * Create the ```data``` and ```outputs``` folders.
    * Install the libraries using ```requirements.txt```.
* Check the environment variables: 
    * Windows: 
* Open ```config/credentials.json``` and start customising it to suit your situation. You may need to update it with the database information.
* Create a geographical database. In our case it is called "cadastre". To create the database, you can use the ```scripts/sql-postgis/0-InitDatabase.sql``` script, copied to the pgAdmin console, or run the ```scripts/python/0_prepare_db.py``` script. (! For this step, the database name is set in the ```scripts/sql-postgis/0-InitDatabase.sql``` script, it doesn't use the ```credentials.json``` parameters !)
* Download and install the fonts listed in ```fonts```.
* In QGIS, add connexion to your newly created database

## 1. Download data

For the cadastral index maps, we have chosen to use geographical data that also appears in the 19th century maps.
The downloaded data from each database (BDTOPO and PCI-EXPRES) must be unzipped into the appropriate folder in the ```data``` folder.
The data is stored by department. You need to list the departments you want to use to generate the images at this stage. You can update the ```config/your-project-name/areas.json``` file with your list of areas.

In our example we use the following French departements:
* Marne (51)
* Paris (75)
* Seine-et-Marne (77)
* Essonne (91)
* Hauts-de-Seine (92)
* Seine-Saint-Denis (93)
* Val-de-Marne (94)

You can also use the downloaded data to update ``config/your-project-name/layers.json''.

### Parcellaire Express (PCI) data
Parcellaire Express (PCI-Express) data, specific to the cadastre, can be downloaded by department from the IGN website: https://geoservices.ign.fr/parcellaire-express-pci
Select one or more departements and download the corresponding folder. Once the folder has been downloaded and unzipped, we'll use the following files
* *feuille.shp* (extent of a cadastral index map)
* *parcelle.shp* (plots)
* *localisant.shp* (ponctual geometries representing the centre of gravity of each parcel)
* *datiment.shp* (buildings)

### BD TOPO data 
BD TOPO data (topographic data) can be downloaded from the IGN website: https://geoservices.ign.fr/bdtopo
After unzipping the download folder, we'll use the following files
* *department.shp*
* *cours_d_eau.shp* (water courses as line strings)
* *surface_hydrographique.shp* (water bodies and waterways as surfaces)
* *troncon_de_route.shp* (roads and paths)
* *lieu_dit_non_habité*.shp (named places in inhabited areas). *For this one, we don't add the data of the département 75 (it only contains duplicated street names from troncon_de_route).

The layers *cours_d_eau.shp*, *surface_hydrographique.shp*, *lieu_dit_non_habité.shp* and *troncon_de_route.shp* contain a buffer of data from neighbouring départements. A processing step is performed to remove them (to avoid overlapping labels on the maps).

## 2. Loading data into DB
* Run the ```python/1_create_styles_table.py``` script in the Python console:
    - This will load the *style.csv* file into the database.
* Use the ```python/2_load_layers_into_db.py``` script and set the *BASE* variable according to your situation. This script will :
    - Load the shape of each selected department.
    - Load the PCI-EXPRESS data.
    - Load the data from BDTOPO into tables in the *bdtopo_tmp* schema. Features from the *department* SHP are added to a *department* layer of the public schema.
* The data from BDTOPO in the *bdtopo_tmp* schema needs to be cut and merged. The script ```python-qgis/bdtopo_layers_concat``` will do the following for one type of layer (run in the Python console of QGIS).
    - For each layer of each department (*cours_d_eau.shp*, *surface_hydrographique.shp*, *lieu_dit_non_habité.shp*, *troncon_de_route.shp*), the layer is cut using the department shape (to remove the data that is not in the treated department).
    - Each group of layers of the same type (e.g. *cours_d_eau.shp*) is merged.
    - The resulting layer is loaded into Postgis using the QGIS loader.
    - Finally, the resulting layer must be added to the database using the QGIS loader.
* In PgAdmin run the script ```sql-postgis/1-SomeTreaments.sql``` to make some final pre-treaments on the layers.
* To set rotation of the labels of *localisant* ans *lieuditnonhabite*, execute the scripts ```python/3_rotation_localisant.py``` and ```python/4_rotation_lieuditnonhabite.py```.
* Because of QGIS properties on labels display, each feature of the layer *lieuditnonhabite* needs to be represented by a LineString instead of a Point. Execute the script ```python/5_create_linestring_lieuditnonhabite.py```.

## 3. Create the images extent
* Run ```sql-postgis/2-CreateZones.sql``` in the PgAdmin console to create 662x662 metre squares corresponding to 2000x2000 pixel images representing the geographical features at a scale of 1:1250:
    - It creates 2 tables in the ```temporary``` schema of the database:
        - ```zone_name``` (full grid over the extent of the area considered)
        - ```zones```, which contains only the squares of the grid that are completely covered by the geometries of the ```feuille``` table.
    - You can copy/paste additional squares from ```zone_name``` to ```zones``` using QGIS, depending on the areas you want in your dataset, accepting gaps between the features of the ```feuille``` table.
* Run the script ```sql-postgis/3-AttributeAStyle.sql``` in the PgAdmin console: 
    - It will attribute a style to each square of the grid using the ```styles/styles.csv``` file.

## 4. Generate synthetic maps
* Open QGIS. Open the Python console in QGIS.
* Open the script ```python-qgis/open-layers.py``` in the QGIS Python console:
    - This will load layers from the database into the project.
* You can visualise the styles in QGIS using the script ```python-qgis/applystyle.py```.
* Open the script ```python-qgis/crop.py``` in the QGIS Python console:
    - It will create the images and export the ground truth annotations ```.csv``` format.
* Finally, use the script ```python/6_treat_crops.py``` to translate the annotations in image referential.

## 5. Export images metadata
* The ```zones``` layer in the ```temporary``` schema of the database contains metadata about each image, including its geographic coordinates, its style applied, its name (*region_X_Y*) and its identifier (number that is in the name of the image).
* It can be exported as GeoJson or CSV using the QGIS export tools.

## Notes
* It is possible to have the same place named many times in the same image.
* Due to QGIS rendering, some areas with high number of small plots can have overlapping text.

## ICDAR 2025 competition

## Citation
