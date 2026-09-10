"""运行时配置的安全与可复现性约束。"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_development_uses_local_sqlite_and_generates_ephemeral_secret():
    settings = Settings(_env_file=None, ENVIRONMENT="development", JWT_SECRET_KEY=None)

    assert settings.DATABASE_URL.startswith("sqlite+aiosqlite:///")
    assert settings.JWT_SECRET_KEY
    assert len(settings.JWT_SECRET_KEY) >= 32


def test_production_requires_an_explicit_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None, ENVIRONMENT="production", JWT_SECRET_KEY=None)


def test_production_rejects_demo_data_and_wildcard_cors():
    with pytest.raises(ValidationError, match="演示账号"):
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            JWT_SECRET_KEY="x" * 48,
            DEMO_DATA_ENABLED=True,
        )

    with pytest.raises(ValidationError, match="通配 CORS"):
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            JWT_SECRET_KEY="x" * 48,
            ALLOWED_ORIGINS=["*"],
        )
