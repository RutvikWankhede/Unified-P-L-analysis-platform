import pandas as pd
from io import StringIO
from sqlalchemy.orm import Session
import uuid
from schemas.pl_schemas import PLRecordCreate
from repositories import pl_repository

def process_csv_upload(db: Session, file_content: bytes, user_id: int):
    # Read CSV
    content = file_content.decode('utf-8')
    df = pd.read_csv(StringIO(content))
    
    # Basic validation
    required_cols = ['domain', 'period', 'line_item', 'amount']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
            
    # Map to schema
    records = []
    for _, row in df.iterrows():
        records.append(
            PLRecordCreate(
                domain=row['domain'],
                period=row['period'],
                line_item=row['line_item'],
                amount=float(row['amount']),
                currency=row.get('currency', 'USD'),
                cost_center=row.get('cost_center')
            )
        )
        
    upload_id = str(uuid.uuid4())
    db_records = pl_repository.create_pl_records(db, records, upload_id, user_id)
    return upload_id, len(db_records)
