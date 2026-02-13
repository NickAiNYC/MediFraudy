"""Tests for the FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

# We need to set up a test database before importing main
import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from main import app  # noqa: E402

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestProviderEndpoints:
    def test_list_providers_empty(self):
        response = client.get("/api/providers")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "count" in data

    def test_get_provider_not_found(self):
        response = client.get("/api/providers/99999")
        assert response.status_code == 404


class TestAnomalyEndpoints:
    def test_list_anomalies_empty(self):
        response = client.get("/api/anomalies")
        assert response.status_code == 200
        data = response.json()
        assert "anomalies" in data


class TestAnalyticsEndpoints:
    def test_billing_stats(self):
        response = client.get("/api/analytics/stats?state=NY")
        assert response.status_code == 200

    def test_outliers(self):
        response = client.get("/api/analytics/outliers?z_threshold=3")
        assert response.status_code == 200

    def test_trends(self):
        response = client.get("/api/analytics/trends?state=NY")
        assert response.status_code == 200

    def test_fraud_patterns(self):
        response = client.get("/api/analytics/fraud-patterns")
        assert response.status_code == 200


class TestCaseEndpoints:
    def test_list_cases_empty(self):
        response = client.get("/api/cases")
        assert response.status_code == 200
        data = response.json()
        assert "cases" in data


class TestExportEndpoints:
    def test_export_provider_not_found(self):
        response = client.get("/api/export/provider/99999")
        assert response.status_code == 404
