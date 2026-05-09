from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class QuantVisionError(Exception):
    """Base for all domain errors."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(QuantVisionError):
    status_code = 404
    code = "not_found"


class ValidationError(QuantVisionError):
    status_code = 422
    code = "validation_error"


class UpstreamError(QuantVisionError):
    """Raised when an external service (yfinance) misbehaves."""

    status_code = 502
    code = "upstream_error"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(QuantVisionError)
    async def handle_app_error(_request: Request, exc: QuantVisionError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
