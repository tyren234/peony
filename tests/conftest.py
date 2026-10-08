import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.config import settings
from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models import User
from backend.app.security import hash_password


@pytest.fixture
def client():
    """Tworzy odizolowaną bazę w pamięci SQLite dla każdego testu i wstrzykuje TestClient."""
    # 1. Nowa baza w pamięci RAM per test (StaticPool pozwala dzielić pamięć RAM między wątkami)
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Włącz obsługę kluczy obcych w testowej bazie SQLite
    @event.listens_for(test_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # 2. Inicjalizacja domyślnego użytkownika z konfiguracji
    with TestingSessionLocal() as database_session:
        default_user = User(
            username=settings.default_user_username,
            password_hash=hash_password(settings.default_user_password),
        )
        database_session.add(default_user)
        database_session.commit()

    # 3. Podmiana zależności bazy danych w FastAPI na czas testu
    def override_get_db():
        database_session = TestingSessionLocal()
        try:
            yield database_session
        finally:
            database_session.close()

    app.dependency_overrides[get_db] = override_get_db

    # 4. Wykonanie testu
    with TestClient(app) as test_client:
        yield test_client

    # 5. Sprzątanie po teście
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
