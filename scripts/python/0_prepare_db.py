import subprocess
import json
import os

BASE = "E:/codes/cadastre_synth_maps"
# Open credentials file
with open(BASE + '/config/credentials.json') as f:
    credentials = json.load(f)

#Set paths
SCRIPT_PATH = BASE + "/scripts/sql-postgis/" + "0-InitDatabase.sql"

# psql command to execute the script to init the database (can also be copied into PgAdmin console)
command = f"psql -U {credentials["USER"]} -h {credentials["HOST"]} -p {credentials["PORT"]} -f " + SCRIPT_PATH

# Execute the command
subprocess.run(command, shell=True)

#You then have to write your db password into the terminal.