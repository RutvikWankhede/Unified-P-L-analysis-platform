import sqlite3

conn = sqlite3.connect('enterprise_pl.db')
cur = conn.cursor()

# Row count
cur.execute("SELECT COUNT(*) FROM pl_records")
count = cur.fetchone()
print("pl_records row count:", count[0])

if count[0] == 0:
    print("TABLE IS EMPTY! No data to show. This is why KPIs are 0.")
else:
    # Sample rows
    cur.execute("SELECT id, domain, line_item, amount, period, upload_id FROM pl_records LIMIT 5")
    rows = cur.fetchall()
    print("\nSample rows:")
    for r in rows:
        print(" ", r)

    # Distinct upload_ids
    cur.execute("SELECT DISTINCT upload_id FROM pl_records")
    uids = cur.fetchall()
    print("\nDistinct upload_ids:", uids)

    # Revenue / expense totals
    cur.execute("""
    SELECT 
        SUM(CASE WHEN lower(line_item) LIKE '%revenue%' OR lower(line_item) LIKE '%income%' OR lower(line_item) LIKE '%sales%' THEN amount ELSE 0 END),
        SUM(CASE WHEN lower(line_item) LIKE '%expense%' OR lower(line_item) LIKE '%cost%' OR lower(line_item) LIKE '%cogs%' OR lower(line_item) LIKE '%opex%' THEN amount ELSE 0 END),
        COUNT(*)
    FROM pl_records
    """)
    agg = cur.fetchone()
    print("\nTotal Revenue:", agg[0], " | Total Expense:", agg[1], " | Total Rows:", agg[2])

    # Line items
    cur.execute("SELECT DISTINCT line_item FROM pl_records LIMIT 20")
    items = cur.fetchall()
    print("\nDistinct line_items (first 20):")
    for i in items:
        print(" ", i[0])

conn.close()
