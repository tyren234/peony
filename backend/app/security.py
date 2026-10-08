import hashlib
import secrets
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

# PasswordHasher z domyślnymi bezpiecznymi parametrami Argon2id
_hasher = PasswordHasher()

# Stały hash używany do niwelowania ataków czasowych (timing attack / user enumeration)
_DUMMY_PASSWORD_HASH = _hasher.hash("dummy_constant_password_to_prevent_timing_attacks")


def hash_password(password: str) -> str:
    """Haszuje hasło algorytmem Argon2id z automatyczną solą."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Weryfikuje hasło względem hasha Argon2id.

    Zwraca False w przypadku niezgodności lub błędnego formatu hasha.
    """
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def verify_dummy_password(plain_password: str) -> bool:
    """Wykonuje kalkulację Argon2id dla nieistniejącego użytkownika, ujednolicając czas odpowiedzi."""
    try:
        return _hasher.verify(_DUMMY_PASSWORD_HASH, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def generate_api_key() -> str:
    """Generuje kryptograficznie bezpieczny klucz API (min. 32 znaki, format url-safe)."""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Oblicza skrót SHA-256 klucza API do bezpiecznego zapisu w bazie danych."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def generate_access_token() -> str:
    """Generuje kryptograficznie bezpieczny Bearer token sesji dla użytkownika."""
    return secrets.token_urlsafe(32)
