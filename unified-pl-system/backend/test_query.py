import os
import sys
import sqlite3

print("Testing direct sqlite3 connection...")
con = sqlite3.connect("enterprise_pl.db")
cur = con.cursor()
cur.execute("SELECT count(*) FROM pl_records")
print("Direct sqlite count:", cur.fetchone())
cur.execute("SELECT DISTINCT upload_id FROM pl_records")
print("Upload IDs in DB:", cur.fetchall())
con.close()
print("Direct sqlite test completed successfully!")
