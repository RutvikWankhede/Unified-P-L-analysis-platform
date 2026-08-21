import time
import uuid
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("api_request_logger")

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Attach correlation ID to request state
        request.state.correlation_id = correlation_id
        
        client_ip = request.client.host if request.client else "unknown"
        user = "anonymous"  # Extracted in auth middleware if needed
        
        logger.info(
            f"[{correlation_id}] Request: {request.method} {request.url.path} "
            f"IP: {client_ip} User: {user}"
        )
        
        try:
            try:
                response = await call_next(request)
            except Exception as e:
                process_time = (time.time() - start_time) * 1000
                logger.error(
                    f"[{correlation_id}] Error: {str(e)} "
                    f"Execution Time: {process_time:.2f}ms", 
                    exc_info=True
                )
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
                
            process_time = (time.time() - start_time) * 1000
            
            logger.info(
                f"[{correlation_id}] Response: {response.status_code} "
                f"Execution Time: {process_time:.2f}ms"
            )
            
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Process-Time"] = f"{process_time:.2f} ms"
            
            return response
        except Exception:
            # Absolute fallback if logging or header assignment fails
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
