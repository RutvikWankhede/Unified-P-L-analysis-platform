import sqlite3

conn = sqlite3.connect('enterprise_pl.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print("Tables in enterprise_pl.db:", tables)
conn.close()
