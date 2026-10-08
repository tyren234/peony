from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.errors import ProblemException
from backend.app.models import Sensor, Series, User, UserToken
from backend.app.schemas.sensors import (
    SensorCreatedResponse,
    SensorInput,
    SensorResponse,
)
from backend.app.security import generate_api_key, hash_api_key

sensors_router = APIRouter(prefix="/api/sensors", tags=["sensors"])


@sensors_router.get(
    "",
    response_model=list[SensorResponse],
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
def get_all_sensors(
    current_user_auth: tuple[User, UserToken] = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> list[Sensor]:
    """Retrieve list of registered sensors (admin only)."""
    all_sensors = database_session.query(Sensor).order_by(Sensor.id.asc()).all()
    return all_sensors


@sensors_router.post(
    "",
    response_model=SensorCreatedResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
def register_sensor(
    sensor_input: SensorInput,
    response: Response,
    current_user_auth: tuple[User, UserToken] = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> SensorCreatedResponse:
    """Register a new sensor and return one-time plaintext API key."""
    target_series = (
        database_session.query(Series)
        .filter(Series.id == sensor_input.series_id)
        .first()
    )
    if target_series is None:
        raise ProblemException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            title="Unprocessable Entity",
            detail=f"Referenced series with id {sensor_input.series_id} does not exist.",
        )

    generated_api_key = generate_api_key()
    hashed_api_key = hash_api_key(generated_api_key)

    new_sensor = Sensor(
        name=sensor_input.name,
        series_id=sensor_input.series_id,
        api_key_hash=hashed_api_key,
    )
    database_session.add(new_sensor)
    database_session.commit()
    database_session.refresh(new_sensor)

    response.headers["Location"] = f"/api/sensors/{new_sensor.id}"

    return SensorCreatedResponse(
        id=new_sensor.id,
        name=new_sensor.name,
        seriesId=new_sensor.series_id,
        createdAt=new_sensor.created_at,
        lastMeasurementAt=new_sensor.last_measurement_at,
        apiKey=generated_api_key,
    )


@sensors_router.get(
    "/{sensor_id}",
    response_model=SensorResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
def get_sensor_by_id(
    sensor_id: int,
    current_user_auth: tuple[User, UserToken] = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> Sensor:
    """Retrieve sensor details by identifier (admin only)."""
    found_sensor = (
        database_session.query(Sensor)
        .filter(Sensor.id == sensor_id)
        .first()
    )
    if found_sensor is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail=f"Sensor with id {sensor_id} was not found.",
        )
    return found_sensor


@sensors_router.delete(
    "/{sensor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unregister_sensor(
    sensor_id: int,
    current_user_auth: tuple[User, UserToken] = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> Response:
    """Unregister sensor. Retains past measurements with sensor_id set to null."""
    found_sensor = (
        database_session.query(Sensor)
        .filter(Sensor.id == sensor_id)
        .first()
    )
    if found_sensor is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail=f"Sensor with id {sensor_id} was not found.",
        )

    database_session.delete(found_sensor)
    database_session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
