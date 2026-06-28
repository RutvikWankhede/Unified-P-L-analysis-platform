from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import settings
from core.exceptions import setup_exception_handlers
from core.logging import setup_logging
from routers import (
    anomaly_router,
    auth_router,
    explanation_router,
    health,
    notifications,
    pl_router,
    recommendation_router,
    reports,
)

logger = setup_logging()
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Enterprise P&L AI Platform",
    description="Production-ready AI Financial Intelligence API",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
setup_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(pl_router.router, prefix="/api/v1/pl", tags=["P&L Records"])
app.include_router(
    anomaly_router.router, prefix="/api/v1/anomalies", tags=["Anomalies"]
)
app.include_router(
    explanation_router.router, prefix="/api/v1/explanations", tags=["AI Explanations"]
)
app.include_router(
    recommendation_router.router,
    prefix="/api/v1/recommendations",
    tags=["AI Recommendations"],
)
app.include_router(health.router, prefix="/api/v1/system", tags=["System"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reporting"])
app.include_router(
    notifications.router, prefix="/api/v1/notifications", tags=["Notifications"]
)


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Enterprise API...")


@app.get("/")
def read_root():
    return {"message": "Enterprise P&L AI API is running"}
