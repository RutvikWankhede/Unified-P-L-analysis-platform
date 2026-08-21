import sqlite3
import os

db_path = 'unified-pl-system/enterprise_pl.db'
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = c.fetchall()
print("Tables:", tables)

for t in tables:
    table_name = t[0]
    c.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = c.fetchone()[0]
    print(f"Table {table_name}: {count} rows")

c.execute("SELECT * FROM datasets LIMIT 5")
print("Datasets:", c.fetchall())

try:
    c.execute("SELECT dataset_id, COUNT(*) FROM pl_record GROUP BY dataset_id")
    print("pl_record by dataset_id:", c.fetchall())
except Exception as e:
    print(e)
