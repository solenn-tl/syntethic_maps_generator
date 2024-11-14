import psycopg2
import random
import json
import pandas as pd
from sqlalchemy import create_engine

# Variable you have to set
BASE = "E:/codes/cadastre_synth_maps"

# Open credentials file and set variables
with open(BASE + '/config/credentials.json', encoding="utf-8") as f:
    credentials = json.load(f)

database_name = credentials['DB_NAME']
host = credentials['HOST']
port = credentials['PORT']
user = credentials['USER']
password = credentials['PASSWORD']
schema = credentials['DEFAULT_SCHEMA']
target_crs = credentials['PROJECT_CRS']
project = credentials['PROJECT_NAME']

# Database connection string for SQLAlchemy
conn_str = f"postgresql://{user}:{password}@{host}:{port}/{database_name}"
engine = create_engine(conn_str)

# Connection to psycopg2 for other operations
conn = psycopg2.connect(user=user,
                        password=password,
                        host=host,
                        port=port,
                        database=database_name)
cur = conn.cursor()

try:

    # Determine the total number of rows in the table
    cur.execute("SELECT COUNT(*), array_agg(id) FROM localisant;")
    total_rows, ids = cur.fetchone()

    # Calculate the number of rows for each rotation value based on the given percentages
    counts = {
        0: int(total_rows * 0.5),
        -5: int(total_rows * 0.1),
        5: int(total_rows * 0.1),
        -10: int(total_rows * 0.075),
        10: int(total_rows * 0.075),
        -45: int(total_rows * 0.05),
        45: int(total_rows * 0.05),
        -90: int(total_rows * 0.025),
        90: int(total_rows * 0.025)
    }
    
    # Generate a list of rotation values based on the distribution
    rotation_values = [val for val, count in counts.items() for _ in range(count)]
    
    # Shuffle the list to randomize the order of updates
    random.shuffle(rotation_values)
    
    # Create a DataFrame to store ids and rotation values
    df = pd.DataFrame({
        'id': ids[:len(rotation_values)],  # Ensure no overflow if rows and rotation_values don't perfectly match
        'rotation': rotation_values
    })

    df2 = pd.read_sql("SELECT * FROM localisant;", conn)

    #Join df and df2 on attribut "id"
    dfres = pd.merge(df2, df, on='id', how='left')

    #Rename table localisant to localisant_old
    cur.execute("ALTER TABLE localisant RENAME TO localisant_old;")
    
    # 7. Update the database in bulk
    dfres.to_sql('localisant', con=engine, schema=schema, if_exists='replace', index=False)

    # Commit and clean up
    conn.commit()
    
except Exception as e:
    # Roll back any changes if something goes wrong
    conn.rollback()
    print(f"An error occurred: {e}")

finally:
    cur.close()
    conn.close()
    engine.dispose()
