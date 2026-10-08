from typing import Optional
from fastapi import Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.errors import ProblemException
from backend.app.models import User, UserToken, utc_now, ensure_utc

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    database_session: Session = Depends(get_db),
) -> tuple[User, UserToken]:
    """Weryfikuje nagłówek Authorization: Bearer <token> i zwraca zalogowanego użytkownika oraz token."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Missing or invalid Bearer authorization header.",
        )

    token_string = credentials.credentials.strip()
    if not token_string:
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Empty authorization token.",
        )

    user_token = (
        database_session.query(UserToken)
        .filter(UserToken.token == token_string)
        .first()
    )

    if not user_token or ensure_utc(user_token.expires_at) <= utc_now():
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Token is invalid or has expired.",
        )

    return user_token.user, user_token
