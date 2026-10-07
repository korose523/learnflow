"""Public callers cannot self-provision a research administrator or fake OAuth."""
import pytest
from fastapi import HTTPException
from app.api.auth import register,login_oauth,RegisterRequest,OAuthLoginRequest

@pytest.mark.asyncio
async def test_public_registration_rejects_admin_before_db_access():
    with pytest.raises(HTTPException) as error:
        await register(RegisterRequest(email='admin@example.org',password='Research-Test-2026!' ,name='Test',role='admin'),db=None)
    assert error.value.status_code==403

@pytest.mark.asyncio
async def test_uid_without_verified_provider_token_cannot_login():
    with pytest.raises(HTTPException) as error:
        await login_oauth(OAuthLoginRequest(provider='wechat',oauth_uid='known-user-id',name='Test',role='admin'),db=None)
    assert error.value.status_code==501
