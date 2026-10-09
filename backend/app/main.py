from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from pathlib import Path
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
import backend.app.models
from backend.app.security import hash_password
from backend.app.errors import (
    ProblemException,
    create_problem_response,
    problem_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from backend.app.routers.auth import router as auth_router
from backend.app.routers.series import series_router
from backend.app.routers.sensors import sensors_router
from backend.app.routers.measurements import measurements_router


def init_default_user_account() -> None:
    """Inicjalizuje domyślne konto użytkownika z konfiguracji jeśli nie istnieje."""
    with SessionLocal() as database_session:
        existing_user = (
            database_session.query(backend.app.models.User)
            .filter_by(username=settings.default_user_username)
            .first()
        )
        if not existing_user:
            default_user = backend.app.models.User(
                username=settings.default_user_username,
                password_hash=hash_password(settings.default_user_password),
            )
            database_session.add(default_user)
            database_session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicjalizacja bazy danych i konta użytkownika przy starcie
    Base.metadata.create_all(bind=engine)
    init_default_user_account()
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
app.add_exception_handler(Exception, generic_exception_handler)


@app.middleware("http")
async def api_headers_and_security_middleware(request: Request, call_next) -> Response:
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
                    detail="Server only supports JSON formats (application/json).",
                    instance=request.url.path,
                )

        # Weryfikacja Content-Type przy przesyłaniu danych (kontrakt: 415 Unsupported Media Type)
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            if content_type and "application/json" not in content_type:
                return create_problem_response(
                    status_code=415,
                    title="Unsupported Media Type",
                    detail="Content-Type header must be application/json.",
                    instance=request.url.path,
                )

    # 2. Przekazanie zapytania dalej
    response: Response = await call_next(request)

    # 3. Dodanie nagłówków bezpieczeństwa
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' ws: wss: https:; "
        "font-src 'self' data:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    return response


# Rejestracja routerów API
app.include_router(auth_router)
app.include_router(series_router)
app.include_router(sensors_router)
app.include_router(measurements_router)


@app.get("/api/health", tags=["system"], summary="Health check")
def health_check() -> dict[str, str]:
    """Liveness probe verifying application availability."""
    return {"status": "ok"}


frontend_distribution_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
frontend_assets_path = frontend_distribution_path / "assets"
if frontend_assets_path.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_assets_path)), name="static_assets")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def get_home_page() -> HTMLResponse:
    """Serve single page application entry point."""
    index_html_file_path = frontend_distribution_path / "index.html"
    if index_html_file_path.exists():
        with open(index_html_file_path, "r", encoding="utf-8") as file_handle:
            html_markup = file_handle.read()
    else:
        html_markup = (
            "<!DOCTYPE html>\n"
            "<html lang=\"pl\">\n"
            "<head>\n"
            "  <meta charset=\"UTF-8\" />\n"
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n"
            "  <meta name=\"description\" content=\"Waterdeep Watchtower – System Monitoringu Miasta Waterdeep\" />\n"
            "  <title>Waterdeep Watchtower</title>\n"
            "</head>\n"
            "<body>\n"
            "  <div id=\"root\">\n"
            "    <header>\n"
            "      <h1>Waterdeep Watchtower</h1>\n"
            "      <p>Punkt Dowodzenia Straży Miejskiej Waterdeep i Wieży Blackstaffa</p>\n"
            "    </header>\n"
            "  </div>\n"
            "</body>\n"
            "</html>\n"
        )
    return HTMLResponse(content=html_markup, status_code=200)
