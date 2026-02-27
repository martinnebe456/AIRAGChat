import os

import jwt

from app.core import config as config_module
from app.core.jwt import create_access_token, decode_token


def test_jwt_issue_and_decode(monkeypatch):
    monkeypatch.setenv("APP_SECRETS_MASTER_KEY", "M0aL4bj9SVI6w9pT8S9u9NLC4d0wQJwZ0o8N3s8fPjQ=")
    monkeypatch.setenv("APP_JWT_SECRET", "unit-test-secret")
    config_module.get_settings.cache_clear()
    token = create_access_token(subject="user-1", role="admin")
    payload = decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_jwt_invalid_signature(monkeypatch):
    monkeypatch.setenv("APP_SECRETS_MASTER_KEY", "M0aL4bj9SVI6w9pT8S9u9NLC4d0wQJwZ0o8N3s8fPjQ=")
    monkeypatch.setenv("APP_JWT_SECRET", "unit-test-secret")
    config_module.get_settings.cache_clear()
    token = create_access_token(subject="user-1", role="user")
    tampered = token + "x"
    try:
      decode_token(tampered)
      assert False, "Expected decode to fail"
    except jwt.PyJWTError:
      assert True

