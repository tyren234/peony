from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.errors import ProblemException
from backend.app.models import Measurement, Series, User
from backend.app.schemas.series import SeriesInput, SeriesResponse

series_router = APIRouter(prefix="/api/series", tags=["series"])


@series_router.get(
    "",
    response_model=list[SeriesResponse],
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
def get_all_series(
    database_session: Session = Depends(get_db),
) -> list[Series]:
    """Retrieve all measurement series publicly."""
    all_series = database_session.query(Series).order_by(Series.id.asc()).all()
    return all_series


@series_router.post(
    "",
    response_model=SeriesResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
def create_series(
    series_input: SeriesInput,
    response: Response,
    current_user: User = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> Series:
    """Create a new measurement series and set the Location header."""
    new_series = Series(
        name=series_input.name,
        min_value=series_input.min_value,
        max_value=series_input.max_value,
        color=series_input.color,
        icon=series_input.icon,
        unit=series_input.unit,
    )
    database_session.add(new_series)
    database_session.commit()
    database_session.refresh(new_series)

    response.headers["Location"] = f"/api/series/{new_series.id}"
    return new_series


@series_router.get(
    "/{series_id}",
    response_model=SeriesResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
def get_series_by_id(
    series_id: int,
    database_session: Session = Depends(get_db),
) -> Series:
    """Retrieve a single measurement series by its identifier."""
    found_series = database_session.query(Series).filter(Series.id == series_id).first()
    if found_series is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail=f"Series with id {series_id} was not found",
        )
    return found_series


@series_router.put(
    "/{series_id}",
    response_model=SeriesResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
def update_series(
    series_id: int,
    series_input: SeriesInput,
    current_user: User = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> Series:
    """Update a measurement series, checking for conflicting out-of-range measurements."""
    found_series = database_session.query(Series).filter(Series.id == series_id).first()
    if found_series is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail=f"Series with id {series_id} was not found",
        )

    # Weryfikacja konfliktu: czy istnieją pomiary wykraczające poza nowy przedział [minValue, maxValue]
    conflicting_measurement = (
        database_session.query(Measurement.id)
        .filter(
            Measurement.series_id == series_id,
            (Measurement.value < series_input.min_value) | (Measurement.value > series_input.max_value),
        )
        .first()
    )
    if conflicting_measurement is not None:
        raise ProblemException(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail="New value range excludes existing measurements in this series",
        )

    found_series.name = series_input.name
    found_series.min_value = series_input.min_value
    found_series.max_value = series_input.max_value
    found_series.color = series_input.color
    found_series.icon = series_input.icon
    found_series.unit = series_input.unit

    database_session.commit()
    database_session.refresh(found_series)
    return found_series


@series_router.delete(
    "/{series_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_series(
    series_id: int,
    current_user: User = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> None:
    """Delete a measurement series and cascade-delete its sensors and measurements."""
    found_series = database_session.query(Series).filter(Series.id == series_id).first()
    if found_series is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail=f"Series with id {series_id} was not found",
        )

    database_session.delete(found_series)
    database_session.commit()
