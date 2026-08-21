from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys

sys.path.append('c:\\Users\\HP\\.gemini\\antigravity-ide\\scratch\\P&L system\\unified-pl-system\\backend')
from database import Base, engine, SessionLocal
from models.pl_record import PLRecord

db = SessionLocal()
records = db.query(PLRecord).limit(10).all()
for r in records:
    print(f"ID={r.id}, period={r.period}, dept={r.domain}, amt={r.amount}, item={r.line_item}")
