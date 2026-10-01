from functools import lru_cache
from typing import Literal
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: Literal['HS256'] = 'HS256'
    access_token_expire_minutes: int = Field(default=60, ge=5, le=1440)
    environment: Literal['development', 'test', 'production'] = 'development'
    frontend_url: str = 'http://localhost:5500'
    cors_origins: str = 'http://localhost:5500,http://localhost:5173'
    gemini_api_key: str = ''
    gemini_model: str = 'gemini-2.5-flash'
    embedding_model: str = 'gemini-embedding-001'
    ai_timeout_seconds: float = Field(default=12, gt=0, le=60)
    rate_limit_per_minute: int = Field(default=10, ge=1)

    @property
    def origins(self) -> list[str]:
        return list(dict.fromkeys([self.frontend_url.rstrip('/')] +
                    [s.strip().rstrip('/') for s in self.cors_origins.split(',') if s.strip()]))

    @model_validator(mode='after')
    def production(self):
        if self.environment == 'production':
            if not self.database_url.startswith(('postgresql://', 'postgres://', 'postgresql+psycopg://')):
                raise ValueError('Production requires PostgreSQL')
            if any(not o.startswith('https://') or '*' in o for o in self.origins):
                raise ValueError('Production CORS origins must be explicit HTTPS origins')
            if self.jwt_secret.lower().startswith(('change', 'example', 'development', 'test')):
                raise ValueError('Set a randomly generated JWT_SECRET')
        return self


@lru_cache
def settings() -> Settings:
    return Settings()
