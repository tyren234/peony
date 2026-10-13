-- ============================================================================
-- 🏰 Waterdeep Watchtower – Schemat Relacyjnej Bazy Danych (Wymogi T4, B4)
-- Projekt: Zaawansowane Aplikacje Internetowe (ZAI 26Z)
-- Dialekt: Kompatybilny z SQLite 3 oraz PostgreSQL 14+
-- ============================================================================

-- 1. Tabela kont użytkowników / administratorów (Wymóg F8, T5)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_users_username ON users (username);


-- 2. Tabela tokenów sesji Bearer (Wymóg T5, autoryzacja z unieważnianiem)
CREATE TABLE IF NOT EXISTS user_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token VARCHAR(255) NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_tokens_user
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_user_tokens_token ON user_tokens (token);
CREATE INDEX IF NOT EXISTS ix_user_tokens_user_id ON user_tokens (user_id);


-- 3. Tabela serii pomiarowych (Wymogi F2, F4, F8)
CREATE TABLE IF NOT EXISTS series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    min_value REAL NOT NULL,
    max_value REAL NOT NULL,
    color VARCHAR(7) NOT NULL,
    icon VARCHAR(50) DEFAULT NULL,
    unit VARCHAR(20) DEFAULT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_series_min_lt_max CHECK (min_value < max_value)
);

CREATE INDEX IF NOT EXISTS ix_series_name ON series (name);


-- 4. Tabela sensorów IoT (Wymogi F12, T5)
-- Klucz API przechowywany jest wyłącznie jako skrót kryptograficzny SHA-256 (64 znaki hex).
CREATE TABLE IF NOT EXISTS sensors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    series_id INTEGER NOT NULL,
    api_key_hash VARCHAR(64) NOT NULL UNIQUE,
    last_measurement_at TIMESTAMP DEFAULT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sensors_series
        FOREIGN KEY (series_id) REFERENCES series (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_sensors_series_id ON sensors (series_id);
CREATE INDEX IF NOT EXISTS ix_sensors_api_key_hash ON sensors (api_key_hash);


-- 5. Tabela wyników pomiarów telemetrycznych (Wymogi F1, F6, T4, T11)
-- Wyniki są niezmiennicze (immutability). Usunięcie sensora zachowuje wyniki (SET NULL).
-- Usunięcie serii kaskadowo usuwa wszystkie jej wyniki (ON DELETE CASCADE).
CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id INTEGER NOT NULL,
    sensor_id INTEGER DEFAULT NULL,
    value REAL NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_measurements_series
        FOREIGN KEY (series_id) REFERENCES series (id) ON DELETE CASCADE,
    CONSTRAINT fk_measurements_sensor
        FOREIGN KEY (sensor_id) REFERENCES sensors (id) ON DELETE SET NULL
);

-- Indeks kompozytowy kluczowy dla szybkiego filtrowania po serii i przedziale czasu (F5, T4)
CREATE INDEX IF NOT EXISTS ix_measurements_series_timestamp ON measurements (series_id, timestamp);
CREATE INDEX IF NOT EXISTS ix_measurements_timestamp ON measurements (timestamp);
CREATE INDEX IF NOT EXISTS ix_measurements_sensor_id ON measurements (sensor_id);
