from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import logger


class DataLensException(Exception):
    """Base exception for application-level domain errors."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR", details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class DatabaseConnectionException(DataLensException):
    """Raised when the database cannot be reached."""

    def __init__(self, message: str = "Database connection failed", details: dict[str, Any] | None = None):
        super().__init__(message=message, code="DATABASE_UNAVAILABLE", details=details)


class StorageException(DataLensException):
    """Raised when file storage operations fail."""

    def __init__(self, message: str = "Storage operation failed", code: str = "STORAGE_ERROR", details: dict[str, Any] | None = None):
        super().__init__(message=message, code=code, details=details)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DataLensException)
    async def datalens_exception_handler(request: Request, exc: DataLensException):
        logger.error(f"Domain Exception [{exc.code}]: {exc.message} - Path: {request.url.path}")
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if exc.code == "DATABASE_UNAVAILABLE":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif exc.code in ("NOT_FOUND", "STORAGE_NOT_FOUND"):
            status_code = status.HTTP_404_NOT_FOUND
        elif exc.code in ("FORBIDDEN_DATASET_ACCESS", "FORBIDDEN", "PERMISSION_DENIED"):
            status_code = status.HTTP_403_FORBIDDEN
        elif exc.code in ("VALIDATION_ERROR", "BAD_REQUEST", "PATH_TRAVERSAL"):
            status_code = status.HTTP_400_BAD_REQUEST

        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request parameters",
                    "details": {"validation_errors": exc.errors()},
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "HTTP_ERROR",
                    "message": exc.detail,
                    "details": {},
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception during request {request.url.path}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected internal server error occurred.",
                    "details": {},
                }
            },
        )
