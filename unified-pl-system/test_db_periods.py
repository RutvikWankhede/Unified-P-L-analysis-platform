from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys

sys.path.append('c:\\Users\\HP\\.gemini\\antigravity-ide\\scratch\\P&L system\\unified-pl-system\\backend')
from database import Base, engine, SessionLocal
from models.pl_record import PLRecord
import pandas as pd

db = SessionLocal()
records = db.query(PLRecord.period, PLRecord.amount).limit(50000).all()
df = pd.DataFrame(records, columns=['period', 'amount'])
print("Total rows:", len(df))
print("Unique periods:", df['period'].unique()[:20])
