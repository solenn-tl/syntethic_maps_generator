import psycopg2
import random
import json

#Variable you have to set
BASE = "E:/codes/cadastre_synth_maps"

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

# Connection parameters
conn = psycopg2.connect(user=user,
                        password=password,
                        host=host,
                        port=port,
                        database=database_name)
# Create a cursor object
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE lieuditnonhabite RENAME TO lieuditnonhabite_points;")
    
    conn.commit()

    cur.execute("""CREATE TABLE lieuditnonhabite AS 
	                SELECT l.id, ST_MakeLine(ST_SetSRID(ST_Point(ST_X(geom),ST_Y(geom)),2154), ST_SetSRID(ST_Point(ST_X(geom)+150,ST_Y(geom)),2154)) AS geom, l.nature, 
l.toponyme, l.statut_top, l.importance, l.date_creat, l.date_maj, l.date_app, l.date_conf, l.source, l.id_source, l.acqu_plani, l.prec_plani, l.id_ban, l.layer, l.path, l.rotation
	                FROM lieuditnonhabite_points AS l""")
    conn.commit()

except Exception as e:
    # Roll back any changes if something goes wrong
    conn.rollback()
    print(f"An error occurred: {e}")

finally:
    # Close the cursor and connection
    cur.close()
    conn.close()
