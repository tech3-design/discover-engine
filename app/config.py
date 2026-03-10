from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "SIGNAL Discovery Engine"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    log_level: str = "INFO"
    crawler_timeout: int = 15
    crawler_max_retries: int = 2

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
