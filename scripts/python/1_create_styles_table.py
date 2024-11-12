import psycopg2
import json

BASE = "E:/codes/cadastre_synth_maps"
STYLES_FOLDER = BASE + "/styles"

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

# Open csv file describing styles
f = open(STYLES_FOLDER + '/styles.csv', 'r', encoding='utf-8')
table_name = "styles"

#List of the columns in the csv file
columns = f.readline().strip().split(',')
columns_str = ""
for elem in columns:
    columns_str += elem + " character varying, "
columns_str = columns_str[:-2]

# connect 
conn = psycopg2.connect(user=user,
                        password=password,
                        host=host,
                        port=port,
                        database=database_name)
cur = conn.cursor()

# Create the table (modify this to match your CSV columns)
cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        {columns_str})
    """)
conn.commit()

# Insert the data into the table
columns_list = ""
for elem in columns:
    columns_list += elem + ", "
columns_list = columns_list[:-2]

#Count len of columns
col_num = len(columns)
#Create the string for the values
values = ""
for i in range(col_num):
    values += "%s, "
values = values[:-2]

for row in f:
    row = row.strip().split(',')
    cur.execute(f"""
        INSERT INTO {table_name} ({columns_list})
        VALUES ({values})
    """, row)
    conn.commit()

f.close()

if conn:
    cur.close()
    conn.close()