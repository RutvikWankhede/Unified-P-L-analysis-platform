from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.recommendation import Recommendation
from schemas.anomaly_schemas import RecommendationResponse
from services.recommendation_engine import generate_recommendations

router = APIRouter()


@router.post(
    "/generate/{anomaly_id}",
    response_model=List[RecommendationResponse],
    status_code=201,
)
def create_recommendations(anomaly_id: int, db: Session = Depends(get_db)):
    recs = generate_recommendations(db, anomaly_id)
    return recs


@router.get("/{anomaly_id}", response_model=List[RecommendationResponse])
def get_recommendations(anomaly_id: int, db: Session = Depends(get_db)):
    recs = (
        db.query(Recommendation).filter(Recommendation.anomaly_id == anomaly_id).all()
    )
    return recs
