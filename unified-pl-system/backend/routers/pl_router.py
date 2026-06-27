from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from schemas.pl_schemas import UploadResponse
from services.pl_service import process_csv_upload
from models.user import User

router = APIRouter()

# Mock auth dependency for now
def get_current_user(db: Session = Depends(get_db)) -> User:
    # In a real app, this parses the JWT token. 
    # For now, just return a dummy user or the first user.
    user = db.query(User).first()
    if not user:
        user = User(username="dummy", email="dummy@test.com", hashed_password="pwd")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_pl_data(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files allowed")
        
    try:
        content = await file.read()
        upload_id, count = process_csv_upload(db, content, current_user.id)
        return {"upload_id": upload_id, "records_ingested": count, "message": "Upload successful"}
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
