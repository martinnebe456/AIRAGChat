from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.schemas.common import ErrorResponse


def _error_response(status_code: int, code: str, message: str, details=None) -> JSONResponse:  # noqa: ANN001
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(code=code, message=message, details=details).model_dump(mode="json"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        return _error_response(exc.status_code, "http_error", str(exc.detail), None)

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(_: Request, exc: ValidationError) -> JSONResponse:
        return _error_response(422, "validation_error", "Validation failed", exc.errors())

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(422, "request_validation_error", "Request validation failed", exc.errors())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        return _error_response(500, "internal_error", "Internal server error", {"error": str(exc)})
