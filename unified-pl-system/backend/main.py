import sys
import traceback

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import settings
from core.exceptions import setup_exception_handlers
from core.logging import setup_logging
from core.security import require_role
from routers import (
    anomaly_router,
    auth_router,
    explanation_router,
    health,
    notifications,
    pl_router,
    recommendation_router,
    reports,
    datasets_router,
    ws_router,
    copilot_router,
)

logger = setup_logging()
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    import os

    try:
        logger.info("Starting up Unified P&L AI Platform...")

        if "PYTEST_CURRENT_TEST" not in os.environ:
            # ── Step 1: Create DB tables ───────────────────────────────────
            logger.info("[Startup] Step 1/3 — Creating DB tables...")
            from database import SessionLocal, engine, Base
            import models.user
            import models.schema_mapping
            import models.pl_record
            import models.uploaded_file
            import models.anomaly
            import models.forecast
            import models.audit_log
            import models.workflow
            import models.notification
            import models.chat_history
            import models.recommendation
            import models.ai_log

            try:
                await asyncio.to_thread(Base.metadata.create_all, engine)
                logger.info("[Startup] Step 1/3 — DB tables ready.")
            except Exception as tbl_err:
                logger.error(f"[Startup] Step 1/3 — DB table creation failed: {tbl_err}. Continuing anyway.")

            # ── Step 2: Warm P&L summary cache ────────────────────────────
            logger.info("[Startup] Step 2/3 — Warming P&L summary cache...")
            try:
                db = SessionLocal()
                from routers.pl_router import get_pl_summary
                await get_pl_summary(db=db, current_user=None)
                logger.info("[Startup] Step 2/3 — P&L summary cache warmed.")
            except Exception as cache_err:
                logger.warning(f"[Startup] Step 2/3 — P&L summary warmup failed: {cache_err}. Skipping.")
            finally:
                try:
                    db.close()
                except Exception:
                    pass

            # ── Step 3: Warm forecast cache ────────────────────────────────
            logger.info("[Startup] Step 3/3 — Warming forecast cache...")
            try:
                db = SessionLocal()
                from routers.pl_router import get_domain_forecast
                await asyncio.to_thread(get_domain_forecast, domain="Overall", db=db, current_user=None)
                logger.info("[Startup] Step 3/3 — Forecast cache warmed.")
            except Exception as fc_err:
                logger.warning(f"[Startup] Step 3/3 — Forecast warmup failed: {fc_err}. Skipping.")
            finally:
                try:
                    db.close()
                except Exception:
                    pass

            # Release all startup DB connections before serving traffic
            try:
                engine.dispose()
            except Exception:
                pass

            logger.info("Successfully warmed P&L summary and forecast caches.")

    except Exception as e:
        logger.error(f"Startup initialization failed: {e}")
        logger.error(traceback.format_exc())
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend.log")
        with open(log_path, "a") as f:
            f.write(traceback.format_exc())
            f.flush()
        # Do NOT re-raise — let uvicorn start anyway so health/ready endpoints respond
        logger.warning("Startup had errors but proceeding — backend will serve requests.")

    yield

    logger.info("Shutting down Unified P&L AI Platform.")
    try:
        from database import engine
        engine.dispose()
    except Exception:
        pass


app = FastAPI(
    title="Enterprise P&L AI Platform",
    description="Production-ready AI Financial Intelligence API",
    version="1.0.0",
    lifespan=lifespan,
)

@app.middleware("http")
async def print_headers(request, call_next):
    if "api" in request.url.path:
        print(f"[{request.method}] {request.url.path} - Headers: {dict(request.headers)}")
    response = await call_next(request)
    return response

try:
    from prometheus_fastapi_instrumentator import Instrumentator
except ImportError:
    logger.warning("prometheus_fastapi_instrumentator not installed, metrics disabled.")

from core.logging_middleware import LoggingMiddleware

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
setup_exception_handlers(app)

app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Authentication"])

viewer_deps = [Depends(require_role(["Viewer"]))]

app.include_router(pl_router.router, prefix="/api/v1/pl", tags=["P&L Records"], dependencies=viewer_deps)
app.include_router(datasets_router.router, prefix="/api/v1/datasets", tags=["Datasets"], dependencies=viewer_deps)
app.include_router(
    anomaly_router.router, prefix="/api/v1/anomalies", tags=["Anomalies"], dependencies=viewer_deps
)
app.include_router(
    explanation_router.router, prefix="/api/v1/explanations", tags=["AI Explanations"], dependencies=viewer_deps
)
app.include_router(
    recommendation_router.router,
    prefix="/api/v1/recommendations",
    tags=["AI Recommendations"],
    dependencies=viewer_deps
)
app.include_router(health.router, prefix="/api/v1/system", tags=["System"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reporting"], dependencies=viewer_deps)
app.include_router(
    notifications.router, prefix="/api/v1/notifications", tags=["Notifications"], dependencies=viewer_deps
)
app.include_router(
    copilot_router.router, prefix="/api/v1/copilot", tags=["AI Copilot"], dependencies=viewer_deps
)
app.include_router(ws_router.router, prefix="/api/v1", tags=["WebSockets"])

@app.get("/")
def read_root():
    return {"message": "Enterprise P&L AI API is running"}

