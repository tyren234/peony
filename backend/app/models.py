from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from backend.app.database import Base


def utc_now():
    """Zwraca bieżący czas w formacie UTC."""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relacja do aktywnych sesji/tokenów
    tokens = relationship("UserToken", back_populates="user", cascade="all, delete-orphan")


class UserToken(Base):
    __tablename__ = "user_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="tokens")


class Series(Base):
    __tablename__ = "series"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    min_value = Column(Float, nullable=False)
    max_value = Column(Float, nullable=False)
    color = Column(String(7), nullable=False)  # Format HEX: #RRGGBB
    icon = Column(String(50), nullable=True)   # Opcjonalny identyfikator ikony
    unit = Column(String(20), nullable=True)   # Opcjonalna jednostka (np. °C, hPa, %)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Usunięcie serii kaskadowo usuwa jej czujniki i pomiary (wymóg kontraktu API)
    sensors = relationship("Sensor", back_populates="series", cascade="all, delete-orphan")
    measurements = relationship("Measurement", back_populates="series", cascade="all, delete-orphan")


class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    series_id = Column(Integer, ForeignKey("series.id", ondelete="CASCADE"), nullable=False, index=True)
    api_key_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA-256
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_measurement_at = Column(DateTime(timezone=True), nullable=True)

    series = relationship("Series", back_populates="sensors")
    measurements = relationship("Measurement", back_populates="sensor")


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(Integer, ForeignKey("series.id", ondelete="CASCADE"), nullable=False, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id", ondelete="SET NULL"), nullable=True, index=True)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    series = relationship("Series", back_populates="measurements")
    sensor = relationship("Sensor", back_populates="measurements")

    __table_args__ = (
        # Indeks kompozytowy dla szybkiego filtrowania po serii i przedziale czasu
        Index("ix_measurements_series_timestamp", "series_id", "timestamp"),
    )
