from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Waterdeep Watchtower"
    app_version: str = "1.0.0"
    database_url: str = "sqlite:///./waterdeep.db"
    default_user_username: str = "admin"
    default_user_password: str = "HasloAdministratora123!"
    token_expiration_seconds: int = 86400

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
