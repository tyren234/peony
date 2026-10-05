from backend.app.security import (
    hash_password,
    verify_password,
    generate_api_key,
    hash_api_key,
    generate_access_token,
)


def test_password_hashing_and_verification():
    raw_password = "MojeSekretneHaslo123!"

    # 1. Poprawne haszowanie i weryfikacja
    hashed = hash_password(raw_password)
    assert hashed != raw_password
    assert hashed.startswith("$argon2id$")
    assert verify_password(raw_password, hashed) is True

    # 2. Błędne hasło
    assert verify_password("ZleHaslo123!", hashed) is False

    # 3. Solenie (dwa hasze tego samego hasła muszą być różne)
    hashed_second = hash_password(raw_password)
    assert hashed != hashed_second
    assert verify_password(raw_password, hashed_second) is True


def test_api_key_generation_and_hashing():
    key1 = generate_api_key()
    key2 = generate_api_key()

    # Długość min. 32 znaki
    assert len(key1) >= 32
    assert len(key2) >= 32
    assert key1 != key2 # Teoretycznie to chyba się może powtórzyć, ale to by było niesamowite

    # Haszowanie SHA-256
    hash1 = hash_api_key(key1)
    hash2 = hash_api_key(key2)

    assert len(hash1) == 64  # sha-256 w heksadecymalnym zapisie
    assert hash1 != hash2
    # Haszowanie jest deterministyczne
    assert hash_api_key(key1) == hash1
    assert hash_api_key(key2) == hash2


def test_access_token_generation():
    token1 = generate_access_token()
    token2 = generate_access_token()

    assert len(token1) >= 32
    assert len(token2) >= 32
    assert token1 != token2
