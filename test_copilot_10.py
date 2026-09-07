import sys, io
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'unified-pl-system/backend')

from database import SessionLocal
from services.copilot_agent import ask_copilot

db = SessionLocal()
queries = [
    'which department has best profit and least anomalies',
    'which department has highest profit',
    'which department has least anomalies',
    'which department has highest revenue',
    'which department has lowest expenses',
    'show top 5 departments by net profit',
    'which departments have the most anomalies',
    'why did profit change',
    'what is driving expenses',
    'compare the top profit department with the department having the most anomalies'
]

for i, q in enumerate(queries, 1):
    print(f"==================================================")
    print(f"TEST {i}: {q}")
    print(f"==================================================")
    ans = ask_copilot(db, q)
    print(ans)
    print()

db.close()
