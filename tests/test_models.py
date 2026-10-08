from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app.models import User, UserToken, Series, Sensor, Measurement, utc_now

"""
Testy sprawdzające czy różne tabele się dobrze tworzą i czy obiekty dobrze się inicjalizują
"""

@pytest.fixture
def db_session():
    """Tworzy czystą bazę w pamięci SQLite dla każdego testu modeli z włączonymi kluczami obcymi."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    database_session = TestingSessionLocal()
    try:
        yield database_session
    finally:
        database_session.close()
        Base.metadata.drop_all(bind=engine)


def test_create_user_and_token(db_session):
    user = User(
        username="admin",
        password_hash="argon2_hashed_secret",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.username == "admin"
    assert user.created_at is not None

    token = UserToken(
        token="test_bearer_token_123",
        user_id=user.id,
        expires_at=utc_now() + timedelta(hours=1),
    )
    db_session.add(token)
    db_session.commit()

    assert len(user.tokens) == 1
    assert user.tokens[0].token == "test_bearer_token_123"

    # Test usunięcia kaskadowego: usunięcie usera usuwa jego tokeny
    db_session.delete(user)
    db_session.commit()
    assert db_session.query(UserToken).filter_by(user_id=user.id).count() == 0


def test_create_series_sensor_and_measurement(db_session):
    series = Series(
        name="Temperatura Powietrza",
        min_value=-40.0,
        max_value=60.0,
        color="#1f77b4",
        icon="thermometer",
        unit="°C",
    )
    db_session.add(series)
    db_session.commit()
    db_session.refresh(series)

    assert series.id is not None

    sensor = Sensor(
        name="Czujnik Południowy",
        series_id=series.id,
        api_key_hash="hash_sha256_of_random_key_1234567890abcdef",
    )
    db_session.add(sensor)
    db_session.commit()
    db_session.refresh(sensor)

    assert sensor.id is not None
    assert sensor.series_id == series.id

    measurement = Measurement(
        series_id=series.id,
        sensor_id=sensor.id,
        value=21.5,
        timestamp=utc_now(),
    )
    db_session.add(measurement)
    db_session.commit()
    db_session.refresh(measurement)

    assert measurement.id is not None
    assert measurement.value == 21.5
    assert measurement.series.name == "Temperatura Powietrza"
    assert measurement.sensor.name == "Czujnik Południowy"


def test_series_cascade_delete(db_session):
    series = Series(
        name="Wilgotność",
        min_value=0.0,
        max_value=100.0,
        color="#2ca02c",
    )
    db_session.add(series)
    db_session.commit()

    sensor = Sensor(
        name="Czujnik Ogrodowy",
        series_id=series.id,
        api_key_hash="hash_humidity_123",
    )
    db_session.add(sensor)
    db_session.commit()

    measurement = Measurement(
        series_id=series.id,
        sensor_id=sensor.id,
        value=55.0,
    )
    db_session.add(measurement)
    db_session.commit()

    # Usunięcie serii kaskadowo usuwa czujnik i pomiar
    db_session.delete(series)
    db_session.commit()

    assert db_session.query(Sensor).filter_by(series_id=series.id).count() == 0
    assert db_session.query(Measurement).filter_by(series_id=series.id).count() == 0


def test_sensor_delete_retains_measurements(db_session):
    series = Series(
        name="Ciśnienie",
        min_value=900.0,
        max_value=1100.0,
        color="#ff7f0e",
    )
    db_session.add(series)
    db_session.commit()

    sensor = Sensor(
        name="Barometr Wschodni",
        series_id=series.id,
        api_key_hash="hash_pressure_123",
    )
    db_session.add(sensor)
    db_session.commit()

    measurement = Measurement(
        series_id=series.id,
        sensor_id=sensor.id,
        value=1013.25,
    )
    db_session.add(measurement)
    db_session.commit()
    measurement_id = measurement.id

    # Usunięcie czujnika nie usuwa pomiaru – sensor_id staje się None (kontrakt API)
    db_session.delete(sensor)
    db_session.commit()

    retained_measurement = db_session.query(Measurement).filter_by(id=measurement_id).first()
    assert retained_measurement is not None
    assert retained_measurement.sensor_id is None
    assert retained_measurement.value == 1013.25
