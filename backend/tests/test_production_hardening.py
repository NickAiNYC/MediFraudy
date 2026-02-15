"""Tests for production hardening features.

Tests API key authentication, tiered rate limiting,
data quality endpoints, and Sentry configuration.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_production.db"
os.environ["ENVIRONMENT"] = "development"

import pytest
from datetime import datetime, date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import engine, Base
from models import APIKey
from core.api_key_auth import generate_api_key, TIER_LIMITS, validate_api_key
from core.security import create_access_token


@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def _get_partner_token() -> str:
    """Create a JWT token for a partner user."""
    return create_access_token({"sub": "testpartner", "role": "partner"})


class TestAPIKeyGeneration:
    """Test API key generation utility."""

    def test_generate_api_key_length(self):
        key = generate_api_key()
        assert len(key) == 64  # 32 bytes hex = 64 chars

    def test_generate_unique_keys(self):
        keys = {generate_api_key() for _ in range(100)}
        assert len(keys) == 100  # All unique


class TestTierLimits:
    """Test rate limit tier configuration."""

    def test_free_tier_limit(self):
        assert TIER_LIMITS["free"] == 100

    def test_pro_tier_limit(self):
        assert TIER_LIMITS["pro"] == 10_000

    def test_enterprise_unlimited(self):
        assert TIER_LIMITS["enterprise"] is None


class TestAPIKeyEndpoints:
    """Test API key management endpoints."""

    def test_create_api_key_requires_auth(self):
        """Creating an API key requires partner role."""
        response = client.post(
            "/api/v1/api-keys",
            json={"name": "Test Key", "tier": "free", "owner_email": "test@example.com"},
        )
        assert response.status_code == 401

    def test_create_api_key_with_partner_token(self):
        """Partner role can create API keys."""
        token = _get_partner_token()
        response = client.post(
            "/api/v1/api-keys",
            json={"name": "Test Key", "tier": "free", "owner_email": "test@example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Key"
        assert data["tier"] == "free"
        assert data["key"] is not None  # Key returned on creation
        assert len(data["key"]) == 64

    def test_create_api_key_invalid_tier(self):
        """Invalid tier should return 400."""
        token = _get_partner_token()
        response = client.post(
            "/api/v1/api-keys",
            json={"name": "Bad Key", "tier": "platinum", "owner_email": "test@example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400

    def test_list_api_keys(self):
        """List API keys requires partner role."""
        token = _get_partner_token()
        # Create a key first
        client.post(
            "/api/v1/api-keys",
            json={"name": "Key 1", "tier": "pro", "owner_email": "test@example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        response = client.get(
            "/api/v1/api-keys",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1

    def test_revoke_api_key(self):
        """Revoking an API key should deactivate it."""
        token = _get_partner_token()
        # Create
        create_resp = client.post(
            "/api/v1/api-keys",
            json={"name": "To Revoke", "tier": "free", "owner_email": "test@example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        key_id = create_resp.json()["id"]

        # Revoke
        revoke_resp = client.delete(
            f"/api/v1/api-keys/{key_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert revoke_resp.status_code == 200
        assert revoke_resp.json()["detail"] == "API key revoked"

    def test_revoke_nonexistent_key(self):
        """Revoking a non-existent key returns 404."""
        token = _get_partner_token()
        response = client.delete(
            "/api/v1/api-keys/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


class TestDataQualityEndpoints:
    """Test data quality reporting endpoints."""

    def test_data_quality_report(self):
        """Data quality report returns expected structure."""
        response = client.get("/api/v1/data-quality/report")
        assert response.status_code == 200
        data = response.json()
        assert "tables" in data
        assert "overall_health" in data
        assert "issues" in data
        assert "providers" in data["tables"]
        assert "claims" in data["tables"]

    def test_data_quality_report_empty_db(self):
        """Report on empty database shows zero counts."""
        response = client.get("/api/v1/data-quality/report")
        data = response.json()
        assert data["tables"]["providers"]["total_records"] == 0
        assert data["tables"]["claims"]["total_records"] == 0
        assert data["overall_health"] == "healthy"

    def test_data_freshness(self):
        """Data freshness endpoint returns expected structure."""
        response = client.get("/api/v1/data-quality/freshness")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "claims" in data
        assert "anomalies" in data


class TestSentryConfig:
    """Test Sentry configuration."""

    def test_sentry_dsn_default_none(self):
        """SENTRY_DSN should default to None when not set."""
        from config import Settings
        s = Settings()
        assert s.SENTRY_DSN is None


class TestAPIKeyModel:
    """Test the APIKey model."""

    def test_api_key_model_creation(self):
        """APIKey model should be in the database schema."""
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "api_keys" in tables

    def test_api_key_model_columns(self):
        """APIKey model should have expected columns."""
        from sqlalchemy import inspect
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("api_keys")}
        expected = {"id", "key", "name", "tier", "owner_email", "is_active",
                    "requests_today", "last_request_date", "created_at", "expires_at"}
        assert expected.issubset(columns)
