from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os
sys.path.append(r"C:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\unified-pl-system\backend")

from database import SQLALCHEMY_DATABASE_URL
from models.user import User

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

admin = db.query(User).filter(User.username == "admin").first()
print(f"Admin found: {admin is not None}")
if admin:
    print(f"Role: {admin.role}")

db.close()
