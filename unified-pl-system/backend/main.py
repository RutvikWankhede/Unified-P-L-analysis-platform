from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import Base, engine
from routers import auth_router, pl_router, anomaly_router, explanation_router, recommendation_router
from services.escalation_service import start_scheduler
from config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables are created
    Base.metadata.create_all(bind=engine)
    scheduler = start_scheduler()
    yield
    scheduler.shutdown()

app = FastAPI(
    title="Unified P&L AI Governance System",
    version="1.0.0",
    lifespan=lifespan
)

origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix='/api/auth', tags=['Auth'])
app.include_router(pl_router.router, prefix='/api/pl', tags=['P&L'])
app.include_router(anomaly_router.router, prefix='/api/anomalies', tags=['Anomalies'])
app.include_router(explanation_router.router, prefix='/api/explanations', tags=['Explanations'])
app.include_router(recommendation_router.router, prefix='/api/recommendations', tags=['Recommendations'])

@app.get("/")
def read_root():
    return {"message": "Welcome to Unified P&L AI Governance System API"}
