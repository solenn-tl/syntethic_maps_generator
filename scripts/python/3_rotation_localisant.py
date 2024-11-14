"""
This script adds a new column 'rotation' to the 'localisant' table in the database and 
populates it with random rotation values based on the given distribution.
"""

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
    # 1. Add the rotation column if it doesn't already exist
    cur.execute("""
        ALTER TABLE localisant
        ADD COLUMN IF NOT EXISTS rotation INTEGER;
    """)
    
    # 2. Determine the total number of rows in the table
    cur.execute("SELECT COUNT(*) FROM localisant;")
    total_rows = cur.fetchone()[0]
    
    # 3. Calculate the number of rows for each rotation value based on the given percentages
    counts = {
        0: int(total_rows * 0.5),
        -10: int(total_rows * 0.15),
        10: int(total_rows * 0.15),
        -90: int(total_rows * 0.1),
        90: int(total_rows * 0.1)
    }
    
    # 4. Generate a list of rotation values based on the distribution
    rotation_values = [val for val, count in counts.items() for _ in range(count)]
    
    # 5. Shuffle the list to randomize the order of updates
    random.shuffle(rotation_values)
    
    # 6. Update the rotation column in the table
    cur.execute("SELECT id FROM localisant;")  # Assuming 'id' is the primary key
    ids = [row[0] for row in cur.fetchall()]
    
    # Use the ids to update each row's rotation value
    for i, rotation in enumerate(rotation_values):
        cur.execute("""
            UPDATE localisant
            SET rotation = %s
            WHERE id = %s;
        """, (rotation, ids[i]))

    # Commit the changes
    conn.commit()

except Exception as e:
    # Roll back any changes if something goes wrong
    conn.rollback()
    print(f"An error occurred: {e}")

finally:
    # Close the cursor and connection
    cur.close()
    conn.close()
