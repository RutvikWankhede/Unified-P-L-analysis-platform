from sqlalchemy import text
from database import engine
with engine.begin() as conn:
    conn.execute(text('DROP SCHEMA public CASCADE; CREATE SCHEMA public;'))
