from datetime import timedelta
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.errors import ProblemException
from backend.app.models import User, UserToken, utc_now
from backend.app.schemas.auth import LoginRequest, LoginResponse, PasswordChangeRequest
from backend.app.security import (
    generate_access_token,
    hash_password,
    verify_password,
    verify_dummy_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
)
def login(
    payload: LoginRequest,
    database_session: Session = Depends(get_db),
) -> LoginResponse:
    """Authenticate user with credentials and return a Bearer token valid for configured expiration time."""
    user = (
        database_session.query(User)
        .filter(User.username == payload.username)
        .first()
    )

    if not user:
        # Zapobieganie timing attacks (user enumeration): stały czas odpowiedzi
        verify_dummy_password(payload.password)
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Invalid username or password.",
        )

    if not verify_password(payload.password, user.password_hash):
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Invalid username or password.",
        )

    access_token = generate_access_token()
    token_expiration_time = utc_now() + timedelta(
        seconds=settings.token_expiration_seconds
    )

    user_token = UserToken(
        token=access_token,
        user_id=user.id,
        expires_at=token_expiration_time,
    )
    database_session.add(user_token)
    database_session.commit()

    return LoginResponse(
        accessToken=access_token,
        tokenType="Bearer",
        expiresIn=settings.token_expiration_seconds,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="User logout (token invalidation)",
)
def logout(
    user_auth: tuple[User, UserToken] = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> Response:
    """Invalidate the active session token of the authenticated user."""
    _, current_user_token = user_auth
    database_session.delete(current_user_token)
    database_session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password of authenticated user",
)
def change_password(
    payload: PasswordChangeRequest,
    user_auth: tuple[User, UserToken] = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> Response:
    """Change the authenticated user password after verifying current password."""
    current_user, _ = user_auth

    if not verify_password(payload.currentPassword, current_user.password_hash):
        raise ProblemException(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            detail="Current password is incorrect.",
        )

    current_user.password_hash = hash_password(payload.newPassword)
    database_session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
