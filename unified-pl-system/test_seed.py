import sys
import os

sys.path.append('c:\\Users\\HP\\.gemini\\antigravity-ide\\scratch\\P&L system\\unified-pl-system\\backend')
from database import Base, engine, SessionLocal
from models.pl_record import PLRecord
from models.workflow import WorkflowInstance
from models.anomaly import Anomaly
from models.user import User

db = SessionLocal()
db.query(PLRecord).delete()
db.query(Anomaly).delete()
db.query(WorkflowInstance).delete()
db.commit()

from services.pl_service import ensure_demo_data
ensure_demo_data(db)

records = db.query(PLRecord).limit(10).all()
for r in records:
    print(f"ID={r.id}, period={r.period}, dept={r.domain}, amt={r.amount}, item={r.line_item}")

from seed import seed_db
seed_db()
print("Seeded demo user admin/admin123")
