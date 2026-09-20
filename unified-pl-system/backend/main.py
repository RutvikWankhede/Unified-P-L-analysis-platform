import sys
import traceback
import asyncio

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

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
    workflow_router,
)

logger = setup_logging()
limiter = Limiter(key_func=get_remote_address)

from database import SessionLocal, engine, Base
from sqlalchemy import inspect
import models
from services.pl_service import ensure_demo_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    import os

    try:
        logger.info("[BACKEND] Starting Unified P&L AI Platform...")
        print("[BACKEND] Starting Unified P&L AI Platform...", flush=True)

        if "PYTEST_CURRENT_TEST" not in os.environ:
            logger.info("[BACKEND] Verifying database...")
            print("[BACKEND] Verifying database...", flush=True)

            def _verify_and_init_db():
                try:
                    inspector = inspect(engine)
                    has_users = inspector.has_table("users")
                    has_pl = inspector.has_table("pl_records")
                    if not (has_users and has_pl):
                        Base.metadata.create_all(bind=engine)
                except Exception as tbl_err:
                    logger.warning(f"[BACKEND WARN] Table verification notice: {tbl_err}")

                try:
                    db_seed = SessionLocal()
                    try:
                        ensure_demo_data(db_seed)
                    finally:
                        db_seed.close()
                except Exception as seed_err:
                    logger.warning(f"[BACKEND WARN] Demo data verification notice: {seed_err}")

            await asyncio.to_thread(_verify_and_init_db)
            logger.info("[BACKEND] Database ready")
            print("[BACKEND] Database ready", flush=True)
            # Initialize Camunda BPMN Auto-Deployment and External Task Workers
            try:
                from camunda.client import camunda_client
                from camunda.workers import camunda_worker_service
                bpmn_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "camunda", "pl_financial_workflow.bpmn")
                if os.path.exists(bpmn_file):
                    dep = camunda_client.deploy_bpmn(bpmn_file)
                    if dep:
                        logger.info(f"[CAMUNDA] Workflow deployed successfully: {dep.get('id')}")
                camunda_worker_service.start()
                logger.info("[CAMUNDA] Background External Task Worker daemon started.")
            except Exception as camunda_err:
                logger.warning(f"[CAMUNDA] Worker initialization notice: {camunda_err}")

            logger.info("[BACKEND] Core services ready")
            print("[BACKEND] Core services ready", flush=True)
            logger.info("[BACKEND] Application startup complete")
            print("[BACKEND] Application startup complete", flush=True)

    except Exception as e:
        logger.error(f"[BACKEND ERROR] Startup initialization failed: {e}")
        logger.error(traceback.format_exc())
        print(f"[BACKEND ERROR] {e}\n{traceback.format_exc()}", flush=True)
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend.log")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(traceback.format_exc() + "\n")
                f.flush()
        except Exception:
            pass
        logger.warning("[BACKEND] Startup had errors but proceeding — backend will serve requests.")

    yield

    logger.info("[BACKEND] Shutting down Unified P&L AI Platform.")
    print("[BACKEND] Shutdown complete.", flush=True)
    try:
        from camunda.workers import camunda_worker_service
        camunda_worker_service.stop()
    except Exception:
        pass
    try:
        engine.dispose()
    except Exception:
        pass


app = FastAPI(
    title="Enterprise P&L AI Platform",
    description="Production-ready AI Financial Intelligence API",
    version="1.0.0",
    lifespan=lifespan,
)

from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

try:
    from prometheus_fastapi_instrumentator import Instrumentator
except ImportError:
    logger.warning("prometheus_fastapi_instrumentator not installed, metrics disabled.")

from core.logging_middleware import LoggingMiddleware

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
setup_exception_handlers(app)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With", "X-Correlation-ID"],
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
app.include_router(
    workflow_router.router, prefix="/api/v1/workflow", tags=["Workflow"], dependencies=viewer_deps
)
app.include_router(
    workflow_router.router, prefix="/api/workflows", tags=["Workflows"], dependencies=viewer_deps
)
app.include_router(ws_router.router, prefix="/api/v1", tags=["WebSockets"])

@app.get("/")
def read_root():
    return {"message": "Enterprise P&L AI API is running"}


@app.get("/health")
def health_endpoint():
    return health.health_check()

