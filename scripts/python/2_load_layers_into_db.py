import json
import subprocess
import re 
import os
import psycopg2
import time
from tools import find_deep_folders_ign, file_exists

#Variables you have to set
BASE = "E:/codes/cadastre_synth_maps"
RUN_BBTOPO = True
RUN_PCI = True

# Open credentials file and set variables for the connection
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

# Construct the ogr2ogr command with Python variables
def create_table_ogr2ogr_command(database_name, host, port, user, password, shapefile_path, target_table_name, target_crs, sql):
    command = f"""ogr2ogr \
    -f "PostgreSQL" PG:"dbname={database_name} host={host} port={port} user={user} password={password}" \
    "{shapefile_path}" \
    -nln {target_table_name} \
    -t_srs {target_crs} \
    -overwrite \
    -lco FID="id" \
    -lco SPATIAL_INDEX=GIST \
    -lco LAUNDER=YES \
    -lco GEOMETRY_NAME=geom \
    -lco PRECISION=NO \
    -fieldTypeToString All \
    -dim 2 \
    -explodecollections \
    {sql} \
    --config PG_USE_COPY YES"""
    return command

def insert_into_table_ogr2ogr_command(database_name, host, port, user, password, shapefile_path, target_table_name, target_crs,sql):
    command = f"""ogr2ogr \
    -f "PostgreSQL" PG:"dbname={database_name} host={host} port={port} user={user} password={password}" \
    "{shapefile_path}" \
    -nln {target_table_name} \
    -t_srs {target_crs} \
    -append \
    -lco FID="id" \
    -lco SPATIAL_INDEX=GIST \
    -lco LAUNDER=YES \
    -lco GEOMETRY_NAME=geom \
    -lco PRECISION=NO \
    -fieldTypeToString All \
    -dim 2 \
    -explodecollections \
    {sql} \
    --config PG_USE_COPY YES"""
    return command

if __name__ == "__main__":

    # connect 
    conn = psycopg2.connect(user=user,
                            password=password,
                            host=host,
                            port=port,
                            database=database_name)
    cur = conn.cursor()

    #Load layers list
    with open(BASE + f"/config/{project}/layers.json") as f:
        layers = json.load(f)

    with open(BASE + f"/config/{project}/areas.json") as f:
        areas = json.load(f)

    # Separate data into two lists based on the 'DB' value (because .shp paths are not exactly the same)
    bdtopo = [entry for entry in layers if entry['DB'] == 'BDTOPO']
    print(bdtopo)
    pci = [entry for entry in layers if entry['DB'] == 'PCI-EXPRESS']

    counter = 0
    tmp_tables = []
    for area in areas:
        print(f"Processing area {area['NAME']} ({area['CODE']})")
        departement = area["CODE"]
        if len(departement) == 1:
            departement_code = 'D00' + departement
        elif len(departement) == 2:
            departement_code = 'D0' + departement
        elif len(departement) == 3:
            departement_code = 'D' + departement

        #Look for BD TOPO data : it will add the shapefiles in a tmp schema (one table = 1 shapefile named as the following table_name + departement_id)
        if RUN_BBTOPO:
            base_directory = BASE + '/data/BDTOPO'
            for elem in bdtopo:
                folder = find_deep_folders_ign(base_directory, departement_code)
                shapefile_path =  folder + '/' + elem['THEME'] + '/' + elem['SHP_NAME'] + '.shp'
                shapefile_path = shapefile_path.replace('\\', '/')
                file_exists(shapefile_path)
                table_name = elem['TABLE_NAME']
                

                print(f"Start processing {table_name} from {shapefile_path}")
                if table_name == "departement" and counter == 0:
                    sql = " -where INSEE_DEP='" + departement + "'"
                    target_table_name = schema + '.' + table_name
                    command = create_table_ogr2ogr_command(database_name, host, port, user, password, shapefile_path, target_table_name, target_crs,sql)
                    subprocess.run(command, shell=True)
                elif table_name == "departement" and counter > 0:
                    sql = " -where INSEE_DEP='" + departement + "'"
                    target_table_name = schema + '.' + table_name
                    command = insert_into_table_ogr2ogr_command(database_name, host, port, user, password, shapefile_path, target_table_name, target_crs,sql)
                    subprocess.run(command, shell=True)
                else:
                    sql = ""
                    schema = 'bdtopo_tmp'
                    target_table_name = schema + '.' + table_name + '_' + str(departement)
                    command = create_table_ogr2ogr_command(database_name, host, port, user, password, shapefile_path, target_table_name, target_crs,sql)
                    subprocess.run(command, shell=True)

        #Look for PCI-EXPRESS data
        if RUN_PCI:
            base_directory = BASE + '/data/PCI-EXPRESS'
            for elem in pci[:0]:
                time.sleep(2)
                folder = find_deep_folders_ign(base_directory, departement_code)
                shapefile_path =  folder + '/' + elem['SHP_NAME'] + '.shp'
                shapefile_path = shapefile_path.replace('\\', '/')
                file_exists(shapefile_path)
                table_name = elem['TABLE_NAME']
                target_table_name = schema + '.' + table_name
                if counter == 0:
                    command = create_table_ogr2ogr_command(database_name, host, port, user, password, shapefile_path, target_table_name, target_crs,sql = "")
                    print(f"Create table {table_name}")
                else:
                    command = insert_into_table_ogr2ogr_command(database_name, host, port, user, password, shapefile_path, target_table_name, target_crs,sql = "")
                    print(f"Insert into table {table_name}")
                subprocess.run(command, shell=True)
        counter += 1

    conn.commit() 
    conn.close()
    cur.close()