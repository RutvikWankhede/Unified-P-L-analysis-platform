import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class DomainException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code


async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)} on {request.method} {request.url}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "details": str(exc)},
    )


async def domain_exception_handler(request: Request, exc: DomainException):
    logger.warning(f"Domain exception: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.message},
    )


def setup_exception_handlers(app):
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(DomainException, domain_exception_handler)
