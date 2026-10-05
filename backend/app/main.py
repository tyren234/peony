from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.config import settings
from backend.app.database import engine, Base
import backend.app.models  # noqa: F401 - rejestracja modeli w Base.metadata
from backend.app.errors import (
    ProblemException,
    create_problem_response,
    problem_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicjalizacja bazy danych przy starcie
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

# Rejestracja globalnych handlerów błędów zgodnych z RFC 9457 Problem Details
app.add_exception_handler(ProblemException, problem_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


@app.middleware("http")
async def api_headers_and_security_middleware(request: Request, call_next):
    # 1. Walidacja formatów dla endpointów /api/*
    if request.url.path.startswith("/api/"):
        # Weryfikacja nagłówka Accept (kontrakt: 406 Not Acceptable)
        accept = request.headers.get("accept")
        if accept and accept != "*/*":
            acceptable = any(
                media_type in accept for media_type in ("application/json", "application/problem+json", "*/*")
            )
            if not acceptable:
                return create_problem_response(
                    status_code=406,
                    title="Not Acceptable",
                    detail="Serwer obsługuje wyłącznie formaty JSON (application/json).",
                    instance=request.url.path,
                )

        # Weryfikacja Content-Type przy przesyłaniu danych (kontrakt: 415 Unsupported Media Type)
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            if content_type and "application/json" not in content_type:
                return create_problem_response(
                    status_code=415,
                    title="Unsupported Media Type",
                    detail="Wymagany nagłówek Content-Type: application/json.",
                    instance=request.url.path,
                )

    # 2. Przekazanie zapytania dalej
    response: Response = await call_next(request)

    # 3. Dodanie nagłówków bezpieczeństwa
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/api/health", tags=["system"])
def health_check():
    """Endpoint sprawdzający stan dostępności aplikacji (liveness probe)."""
    return {"status": "ok"}
