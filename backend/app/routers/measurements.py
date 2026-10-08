from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.errors import ProblemException
from backend.app.models import Measurement, Sensor, Series, ensure_utc, utc_now
from backend.app.schemas.measurements import (
    MeasurementInput,
    MeasurementResponse,
)
from backend.app.security import hash_api_key

measurements_router = APIRouter(prefix="/api/measurements", tags=["measurements"])


def parse_query_datetime(raw_datetime_string: str, parameter_name: str) -> datetime:
    """Safely parse an ISO 8601 datetime string from query parameters handling HTTP '+' encoding."""
    cleaned_string = raw_datetime_string.strip().replace(" ", "+")
    if cleaned_string.endswith("Z"):
        cleaned_string = cleaned_string[:-1] + "+00:00"
    try:
        parsed_datetime = datetime.fromisoformat(cleaned_string)
        return ensure_utc(parsed_datetime)
    except Exception:
        raise ProblemException(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Bad Request",
            detail=f"Invalid date format for '{parameter_name}' parameter. Expected ISO 8601.",
        )


@measurements_router.get(
    "",
    response_model=list[MeasurementResponse],
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
def get_measurements(
    series: Optional[str] = Query(
        default=None,
        description="Comma-separated series identifiers, e.g. '1,3'",
    ),
    from_time: Optional[str] = Query(
        default=None,
        alias="from",
        description="Filter range start instant (inclusive)",
    ),
    to_time: Optional[str] = Query(
        default=None,
        alias="to",
        description="Filter range end instant (inclusive)",
    ),
    sort: str = Query(
        default="timestamp",
        description="Sort order: 'timestamp' (ascending) or '-timestamp' (descending)",
    ),
    limit: int = Query(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum number of records to return",
    ),
    database_session: Session = Depends(get_db),
) -> list[Measurement]:
    """Retrieve telemetry measurements with optional series and closed time range filters."""
    measurements_query = database_session.query(Measurement)

    # 1. Filtrowanie po liście serii
    if series is not None and series.strip():
        parsed_series_identifiers: list[int] = []
        raw_series_items = series.split(",")
        for raw_series_item in raw_series_items:
            clean_item = raw_series_item.strip()
            if not clean_item:
                continue
            try:
                parsed_series_identifiers.append(int(clean_item))
            except ValueError:
                raise ProblemException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    title="Bad Request",
                    detail=f"Invalid series identifier '{clean_item}' in query parameter.",
                )
        if parsed_series_identifiers:
            measurements_query = measurements_query.filter(
                Measurement.series_id.in_(parsed_series_identifiers)
            )

    # 2. Filtrowanie po czasie początkowym: from <= timestamp
    if from_time is not None:
        normalized_from_time = parse_query_datetime(from_time, "from")
        measurements_query = measurements_query.filter(
            Measurement.timestamp >= normalized_from_time
        )

    # 3. Filtrowanie po czasie końcowym: timestamp <= to
    if to_time is not None:
        normalized_to_time = parse_query_datetime(to_time, "to")
        measurements_query = measurements_query.filter(
            Measurement.timestamp <= normalized_to_time
        )

    # 4. Sortowanie: 'timestamp' lub '-timestamp'
    if sort == "timestamp":
        measurements_query = measurements_query.order_by(
            Measurement.timestamp.asc(), Measurement.id.asc()
        )
    elif sort == "-timestamp":
        measurements_query = measurements_query.order_by(
            Measurement.timestamp.desc(), Measurement.id.desc()
        )
    else:
        raise ProblemException(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Bad Request",
            detail="Invalid sort parameter. Allowed values are 'timestamp' and '-timestamp'.",
        )

    # 5. Limit wyników
    all_measurements = measurements_query.limit(limit).all()
    return all_measurements


@measurements_router.post(
    "",
    response_model=MeasurementResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
def create_measurement(
    measurement_input: MeasurementInput,
    response: Response,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    database_session: Session = Depends(get_db),
) -> Measurement:
    """Submit a telemetry measurement authenticating exclusively via sensor X-API-Key."""
    if not x_api_key or not x_api_key.strip():
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Missing or invalid X-API-Key header.",
        )

    hashed_api_key = hash_api_key(x_api_key.strip())
    found_sensor = (
        database_session.query(Sensor)
        .filter(Sensor.api_key_hash == hashed_api_key)
        .first()
    )
    if found_sensor is None:
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Invalid sensor API key.",
        )

    target_series = (
        database_session.query(Series)
        .filter(Series.id == found_sensor.series_id)
        .first()
    )
    if target_series is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail=f"Series with id {found_sensor.series_id} was not found.",
        )

    # Weryfikacja zakresu min/max serii (wymóg F4)
    if (
        measurement_input.value < target_series.min_value
        or measurement_input.value > target_series.max_value
    ):
        raise ProblemException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            title="Unprocessable Entity",
            detail=(
                f"Measurement value {measurement_input.value} is outside series allowed range "
                f"[{target_series.min_value}, {target_series.max_value}]."
            ),
        )

    # Weryfikacja znacznika czasu (nie dalej niż 5 minut w przyszłość)
    current_server_time = utc_now()
    if measurement_input.timestamp is not None:
        measurement_timestamp = ensure_utc(measurement_input.timestamp)
        if measurement_timestamp > current_server_time + timedelta(minutes=5):
            raise ProblemException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                title="Unprocessable Entity",
                detail="Measurement timestamp cannot be more than 5 minutes in the future.",
            )
    else:
        measurement_timestamp = current_server_time

    new_measurement = Measurement(
        series_id=target_series.id,
        sensor_id=found_sensor.id,
        value=measurement_input.value,
        timestamp=measurement_timestamp,
    )
    database_session.add(new_measurement)

    # Aktualizacja znacznika ostatniego pomiaru w czujniku
    found_sensor.last_measurement_at = measurement_timestamp

    database_session.commit()
    database_session.refresh(new_measurement)

    response.headers["Location"] = f"/api/measurements/{new_measurement.id}"
    return new_measurement


@measurements_router.get(
    "/{measurement_id}",
    response_model=MeasurementResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
def get_measurement_by_id(
    measurement_id: int,
    database_session: Session = Depends(get_db),
) -> Measurement:
    """Retrieve single telemetry measurement by identifier publicly."""
    found_measurement = (
        database_session.query(Measurement)
        .filter(Measurement.id == measurement_id)
        .first()
    )
    if found_measurement is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail=f"Measurement with id {measurement_id} was not found.",
        )
    return found_measurement
