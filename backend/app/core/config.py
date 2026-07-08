from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Energy Consumption Forecasting & Optimization System"
    DATABASE_URL: str = "sqlite:///./energy.db"

    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_super_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # ML defaults
    ANOMALY_Z_THRESHOLD: float = 3.0
    PEAK_PERCENTILE: float = 0.90

    class Config:
        env_file = ".env"


settings = Settings()
