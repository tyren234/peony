from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from backend.app.config import settings
from backend.app.database import engine, Base
import backend.app.models  # noqa: F401 - rejestracja modeli w Base.metadata

@asynccontextmanager # we 
async def lifespan(app: FastAPI):
    # Inicjalizacja bazy danych przy starcie
    Base.metadata.create_all(bind=engine) # przed startem aplikacji
    yield # tutaj pauza
    # przy zamknięciu aplikacji

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan, # to się dzieje przy starcie aplikacji 
    docs_url="/docs",
    redoc_url=None
)

@app.middleware("http") # middleware przechwytuje wszyskie zapytania do naszej aplikacji 
async def add_security_headers(request: Request, call_next): # call_next to jest to co ma się wyażyć dalej z naszym requestem
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff" # potencjalnie blokuje MIME sniffing (jak ktoś zapisze skrypt jako .jpg i go prześle, żeby go nic nie zinterpretowało przez przypadek)
    return response

@app.get("/api/health", tags=["system"])
def health_check():
    """Endpoint sprawdzający stan dostępności aplikacji (liveness probe)."""
    return {"status": "ok"}
