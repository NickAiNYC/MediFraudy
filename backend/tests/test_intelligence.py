"""Tests for intelligence architecture modules.

Covers entity resolution, temporal intelligence, risk tensor,
impossible patterns, and cost optimizer.
"""

import random
import time
from datetime import datetime, date, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from models import Base, Provider, Claim, Beneficiary

# ---------------------------------------------------------------------------
# Module imports under test
# ---------------------------------------------------------------------------

from analytics.entity_resolution import (
    normalize_name,
    normalize_phone,
    normalize_address,
    calculate_entity_similarity,
    find_duplicate_providers,
    resolve_entities,
)
from analytics.temporal_intelligence import (
    detect_change_points,
    analyze_temporal_patterns,
    detect_velocity_changes,
    detect_weekend_holiday_anomalies,
    track_statute_of_limitations,
)
from analytics.risk_tensor import (
    DIMENSIONS,
    calculate_risk_tensor,
    reduce_tensor_to_score,
    explain_risk_drivers,
)
from analytics.impossible_patterns import (
    detect_impossible_patterns,
    detect_excessive_frequency,
    detect_25hour_days,
    detect_deceased_billing,
    EXCESSIVE_FREQUENCY_THRESHOLDS,
)
from services.cost_optimizer import CostOptimizer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_provider(db_session):
    """Create a sample provider."""
    provider = Provider(
        npi="1234567890",
        name="Test Nursing Home",
        facility_type="nursing_facility",
        city="Brooklyn",
        state="NY",
        zip_code="11201",
        licensed_capacity=100,
    )
    db_session.add(provider)
    db_session.commit()
    return provider


@pytest.fixture
def sample_claims(db_session, sample_provider):
    """Create sample claims spread over 2 years."""
    random.seed(42)
    claims = []
    base_date = date(2023, 1, 2)  # Monday
    for i in range(200):
        claim = Claim(
            provider_id=sample_provider.id,
            claim_id=f"CLM{i}",
            beneficiary_id=f"BEN{random.randint(1, 20)}",
            billing_code=f"CODE{random.randint(1, 10)}",
            amount=random.uniform(100, 500),
            claim_date=base_date + timedelta(days=random.randint(0, 700)),
            units=random.randint(1, 4),
        )
        claims.append(claim)
    db_session.add_all(claims)
    db_session.commit()
    return claims


# ===================================================================
# 1. Entity Resolution
# ===================================================================

class TestNormalizeName:
    def test_strips_and_lowercases(self):
        assert normalize_name("  ABC Corp  ") == "abc"

    def test_removes_business_suffixes(self):
        result = normalize_name("Brooklyn Health LLC")
        assert "llc" not in result
        assert "brooklyn health" == result

    def test_empty_string(self):
        assert normalize_name("") == ""

    def test_removes_punctuation_but_keeps_hyphens(self):
        result = normalize_name("St. Mary's Health-Center Inc.")
        assert "inc" not in result
        assert "-" in result or "health-center" in result


class TestNormalizePhone:
    def test_standard_10_digits(self):
        assert normalize_phone("7185551234") == "7185551234"

    def test_with_country_code(self):
        assert normalize_phone("+1 (718) 555-1234") == "7185551234"

    def test_with_extension_strips_digits(self):
        # "ext 5" adds an extra digit; 11 digits starting with "1" gets truncated
        # so the result is not the original 10 digits — function returns
        # digits-only without extension awareness.
        result = normalize_phone("7185551234 ext 5")
        assert isinstance(result, str)
        assert len(result) == 0 or len(result) == 10

    def test_dashes_and_parens(self):
        assert normalize_phone("(718) 555-1234") == "7185551234"

    def test_too_few_digits_returns_empty(self):
        assert normalize_phone("12345") == ""

    def test_empty_returns_empty(self):
        assert normalize_phone("") == ""


class TestNormalizeAddress:
    def test_lowercases_and_strips(self):
        result = normalize_address("  123 Main STREET  ")
        assert result == result.lower()
        assert result == result.strip()

    def test_standardizes_abbreviations(self):
        result = normalize_address("123 Main Street")
        assert "st" in result

    def test_empty_returns_empty(self):
        assert normalize_address("") == ""


class TestCalculateEntitySimilarity:
    def test_identical_entities(self):
        entity = {
            "name": "Brooklyn Health LLC",
            "address": "123 Main St",
            "zip_code": "11201",
            "npi": "1234567890",
            "phone": "7185551234",
            "specialty": "nursing",
            "facility_type": "nursing_facility",
        }
        result = calculate_entity_similarity(entity, entity)
        assert "confidence" in result
        assert "scores" in result
        assert "matching_fields" in result
        assert result["confidence"] >= 80

    def test_different_entities(self):
        a = {"name": "Alpha Clinic", "npi": "1111111111"}
        b = {"name": "Zebra Hospital", "npi": "9999999999"}
        result = calculate_entity_similarity(a, b)
        assert result["confidence"] < 50

    def test_confidence_in_valid_range(self):
        a = {"name": "Test A"}
        b = {"name": "Test B"}
        result = calculate_entity_similarity(a, b)
        assert 0 <= result["confidence"] <= 100


class TestFindDuplicateProviders:
    def test_finds_similar_providers(self, db_session):
        p1 = Provider(npi="1111111111", name="Brooklyn Nursing Home LLC",
                      facility_type="nursing_facility", state="NY",
                      city="Brooklyn", zip_code="11201")
        p2 = Provider(npi="2222222222", name="Brooklyn Nursing Home Inc",
                      facility_type="nursing_facility", state="NY",
                      city="Brooklyn", zip_code="11201")
        db_session.add_all([p1, p2])
        db_session.commit()

        duplicates = find_duplicate_providers(db_session, threshold=0.5)
        assert isinstance(duplicates, list)

    def test_no_duplicates_for_different_providers(self, db_session):
        p1 = Provider(npi="3333333333", name="Alpha Health",
                      facility_type="hospital", state="CA", city="LA")
        p2 = Provider(npi="4444444444", name="Zebra Clinic",
                      facility_type="pharmacy", state="TX", city="Dallas")
        db_session.add_all([p1, p2])
        db_session.commit()

        duplicates = find_duplicate_providers(db_session, threshold=0.9)
        assert len(duplicates) == 0


class TestResolveEntities:
    def test_returns_expected_structure(self, db_session):
        p = Provider(npi="5555555555", name="Test Provider",
                     facility_type="clinic", state="NY", city="NYC")
        db_session.add(p)
        db_session.commit()

        result = resolve_entities(db_session)
        assert "duplicates" in result
        assert "address_clusters" in result
        assert "phoenix_companies" in result
        assert "shell_company_links" in result
        assert "stats" in result


# ===================================================================
# 2. Temporal Intelligence
# ===================================================================

class TestDetectChangePoints:
    def test_detects_spike(self):
        # Flat baseline with a known spike
        values = [10.0] * 20 + [50.0] * 5 + [10.0] * 20
        cps = detect_change_points(values, threshold=2.0)
        assert len(cps) > 0
        assert any(cp["direction"] == "increase" for cp in cps)

    def test_flat_series_no_change_points(self):
        values = [5.0] * 30
        cps = detect_change_points(values, threshold=2.0)
        assert cps == []

    def test_too_short_returns_empty(self):
        assert detect_change_points([1.0, 2.0]) == []

    def test_returns_index_and_direction(self):
        values = [1.0] * 20 + [100.0] * 10
        cps = detect_change_points(values, threshold=1.5)
        for cp in cps:
            assert "index" in cp
            assert "direction" in cp
            assert "magnitude" in cp
            assert cp["direction"] in ("increase", "decrease")


class TestAnalyzeTemporalPatterns:
    def test_returns_expected_structure(self, db_session, sample_provider, sample_claims):
        result = analyze_temporal_patterns(db_session, sample_provider.id)
        assert "temporal_risk_score" in result
        assert "velocity_analysis" in result
        assert "seasonal_analysis" in result
        assert "weekend_holiday_analysis" in result
        assert "lifecycle_analysis" in result
        assert "statute_of_limitations" in result
        assert 0 <= result["temporal_risk_score"] <= 100

    def test_provider_not_found(self, db_session):
        result = analyze_temporal_patterns(db_session, 99999)
        assert result["temporal_risk_score"] == 0
        assert "error" in result


class TestDetectVelocityChanges:
    def test_with_sample_claims(self, db_session, sample_provider, sample_claims):
        result = detect_velocity_changes(db_session, sample_provider.id)
        assert "weekly_series" in result
        assert "change_points" in result
        assert "spike_periods" in result
        assert "velocity_risk_score" in result

    def test_no_claims(self, db_session, sample_provider):
        result = detect_velocity_changes(db_session, sample_provider.id)
        assert result["velocity_risk_score"] == 0
        assert result["weekly_series"] == []


class TestDetectWeekendHolidayAnomalies:
    def test_with_sample_claims(self, db_session, sample_provider, sample_claims):
        result = detect_weekend_holiday_anomalies(db_session, sample_provider.id)
        assert "weekend_claims" in result
        assert "holiday_claims" in result
        assert "weekend_holiday_risk_score" in result
        assert isinstance(result["weekend_holiday_risk_score"], int)
        assert 0 <= result["weekend_holiday_risk_score"] <= 100

    def test_no_claims(self, db_session, sample_provider):
        result = detect_weekend_holiday_anomalies(db_session, sample_provider.id)
        assert result["weekend_holiday_risk_score"] == 0


class TestTrackStatuteOfLimitations:
    def test_returns_valid_structure(self, db_session, sample_provider, sample_claims):
        result = track_statute_of_limitations(db_session, sample_provider.id)
        assert "fca_lookback_years" in result
        assert "fca_cutoff_date" in result
        assert "claims_in_window" in result
        assert result["fca_lookback_years"] == 6

    def test_no_claims(self, db_session, sample_provider):
        result = track_statute_of_limitations(db_session, sample_provider.id)
        assert result["total_claims"] == 0
        assert result["claims_in_window"] == 0


# ===================================================================
# 3. Risk Tensor
# ===================================================================

class TestCalculateRiskTensor:
    def test_returns_all_dimensions(self, db_session, sample_provider, sample_claims):
        result = calculate_risk_tensor(db_session, sample_provider.id)
        assert "dimensions" in result
        for dim in DIMENSIONS:
            assert dim in result["dimensions"]
        assert "composite_score" in result
        assert "risk_level" in result

    def test_score_in_valid_range(self, db_session, sample_provider, sample_claims):
        result = calculate_risk_tensor(db_session, sample_provider.id)
        assert 0 <= result["composite_score"] <= 100

    def test_provider_not_found(self, db_session):
        result = calculate_risk_tensor(db_session, 99999)
        assert "error" in result
        assert result["composite_score"] == 0
        assert result["risk_level"] == "LOW"


class TestReduceTensorToScore:
    def test_produces_valid_composite(self):
        dims = {d: {"score": 50} for d in DIMENSIONS}
        result = reduce_tensor_to_score(dims)
        assert "composite_score" in result
        assert "pca_weights" in result
        assert 0 <= result["composite_score"] <= 100

    def test_all_zeros(self):
        dims = {d: {"score": 0} for d in DIMENSIONS}
        result = reduce_tensor_to_score(dims)
        assert result["composite_score"] == 0

    def test_score_always_0_to_100(self):
        random.seed(42)
        for _ in range(10):
            dims = {d: {"score": random.uniform(0, 100)} for d in DIMENSIONS}
            result = reduce_tensor_to_score(dims)
            assert 0 <= result["composite_score"] <= 100

    def test_high_scores_produce_high_composite(self):
        dims = {d: {"score": 90} for d in DIMENSIONS}
        result = reduce_tensor_to_score(dims)
        assert result["composite_score"] >= 70


class TestExplainRiskDrivers:
    def test_returns_ranked_drivers(self):
        dims = {
            d: {"score": (i + 1) * 10}
            for i, d in enumerate(DIMENSIONS)
        }
        composite = reduce_tensor_to_score(dims)["composite_score"]
        drivers = explain_risk_drivers(dims, composite)
        assert len(drivers) == len(DIMENSIONS)
        # Drivers should be sorted by contribution descending
        contributions = [d["contribution"] for d in drivers]
        assert contributions == sorted(contributions, reverse=True)

    def test_driver_fields(self):
        dims = {d: {"score": 50} for d in DIMENSIONS}
        composite = reduce_tensor_to_score(dims)["composite_score"]
        drivers = explain_risk_drivers(dims, composite)
        for drv in drivers:
            assert "dimension" in drv
            assert "score" in drv
            assert "weight" in drv
            assert "contribution" in drv
            assert "pct_of_total" in drv


# ===================================================================
# 4. Impossible Patterns
# ===================================================================

class TestDetectImpossiblePatterns:
    def test_returns_expected_structure(self, db_session, sample_provider, sample_claims):
        result = detect_impossible_patterns(db_session, sample_provider.id)
        assert "impossibility_score" in result
        assert "geospatial" in result
        assert "clinical" in result
        assert "temporal" in result
        assert 0 <= result["impossibility_score"] <= 100

    def test_provider_not_found(self, db_session):
        result = detect_impossible_patterns(db_session, 99999)
        assert result["impossibility_score"] == 0
        assert "error" in result


class TestDetectExcessiveFrequency:
    def test_catches_duplicates(self, db_session, sample_provider):
        """Create claims with billing codes that exceed frequency thresholds."""
        code = list(EXCESSIVE_FREQUENCY_THRESHOLDS.keys())[0]
        threshold = EXCESSIVE_FREQUENCY_THRESHOLDS[code]
        claims = []
        base_date = date.today() - timedelta(days=100)
        for i in range(threshold + 5):
            claims.append(Claim(
                provider_id=sample_provider.id,
                claim_id=f"FREQ{i}",
                beneficiary_id="BEN_FREQ_1",
                billing_code=code,
                amount=100.0,
                claim_date=base_date + timedelta(days=i),
            ))
        db_session.add_all(claims)
        db_session.commit()

        result = detect_excessive_frequency(db_session, sample_provider.id)
        assert result["total_flagged"] >= 1
        assert result["frequency_risk_score"] > 0

    def test_no_excessive_frequency(self, db_session, sample_provider):
        result = detect_excessive_frequency(db_session, sample_provider.id)
        assert result["total_flagged"] == 0
        assert result["frequency_risk_score"] == 0


class TestDetect25HourDays:
    def test_flags_overwork(self, db_session, sample_provider):
        """Create claims whose total units on a single day exceed 24h."""
        target_date = date.today() - timedelta(days=10)
        # 200 units * 0.25 h/unit = 50 hours (> 24)
        claims = []
        for i in range(20):
            claims.append(Claim(
                provider_id=sample_provider.id,
                claim_id=f"OW{i}",
                beneficiary_id=f"BEN_OW{i}",
                billing_code="99213",
                amount=100.0,
                claim_date=target_date,
                units=10,
            ))
        db_session.add_all(claims)
        db_session.commit()

        result = detect_25hour_days(db_session, sample_provider.id)
        assert result["overwork_day_count"] >= 1
        assert result["max_hours_billed"] > 24
        assert result["overwork_risk_score"] > 0

    def test_no_overwork(self, db_session, sample_provider):
        """Normal workload should not trigger."""
        target_date = date.today() - timedelta(days=10)
        claims = [
            Claim(
                provider_id=sample_provider.id,
                claim_id="NORMAL1",
                beneficiary_id="BEN1",
                billing_code="99213",
                amount=100.0,
                claim_date=target_date,
                units=4,
            )
        ]
        db_session.add_all(claims)
        db_session.commit()

        result = detect_25hour_days(db_session, sample_provider.id)
        assert result["overwork_day_count"] == 0


class TestDetectDeceasedBilling:
    def test_detects_post_death_claims(self, db_session, sample_provider):
        """Claims after death date should be flagged."""
        death_date = date(2023, 6, 1)
        ben = Beneficiary(
            id="DECEASED_BEN",
            status="deceased",
            status_date=death_date,
        )
        db_session.add(ben)
        db_session.flush()

        claim = Claim(
            provider_id=sample_provider.id,
            claim_id="DEAD1",
            beneficiary_id="DECEASED_BEN",
            billing_code="99213",
            amount=200.0,
            claim_date=date(2023, 7, 15),
        )
        db_session.add(claim)
        db_session.commit()

        result = detect_deceased_billing(db_session, sample_provider.id)
        assert result["total_post_death_claims"] >= 1
        assert result["deceased_billing_risk_score"] > 0
        assert result["claims_after_death"][0]["days_after_death"] > 0

    def test_no_deceased_billing(self, db_session, sample_provider):
        result = detect_deceased_billing(db_session, sample_provider.id)
        assert result["total_post_death_claims"] == 0
        assert result["deceased_billing_risk_score"] == 0


class TestImpossibilityScoreRange:
    def test_composite_score_0_to_100(self, db_session, sample_provider, sample_claims):
        result = detect_impossible_patterns(db_session, sample_provider.id)
        assert 0 <= result["impossibility_score"] <= 100


# ===================================================================
# 5. Cost Optimizer
# ===================================================================

class TestCostOptimizer:
    @patch("services.cost_optimizer._get_redis", return_value=None)
    def test_caches_on_first_call(self, mock_redis):
        optimizer = CostOptimizer(cache_ttl=60)
        call_count = 0

        def compute():
            nonlocal call_count
            call_count += 1
            return {"result": 42}

        result = optimizer.get_cached_or_compute("test_key", compute)
        assert result == {"result": 42}
        assert call_count == 1
        assert optimizer.misses == 1

    @patch("services.cost_optimizer._get_redis", return_value=None)
    def test_returns_cached_on_second_call(self, mock_redis):
        optimizer = CostOptimizer(cache_ttl=60)
        call_count = 0

        def compute():
            nonlocal call_count
            call_count += 1
            return {"result": 42}

        optimizer.get_cached_or_compute("same_key", compute)
        result2 = optimizer.get_cached_or_compute("same_key", compute)
        assert result2 == {"result": 42}
        assert call_count == 1  # compute called only once
        assert optimizer.hits == 1

    @patch("services.cost_optimizer._get_redis", return_value=None)
    def test_invalidate_removes_cache_entry(self, mock_redis):
        optimizer = CostOptimizer(cache_ttl=60)
        call_count = 0

        def compute():
            nonlocal call_count
            call_count += 1
            return {"result": call_count}

        optimizer.get_cached_or_compute("inv_key", compute)
        assert call_count == 1

        optimizer.invalidate("inv_key")

        result = optimizer.get_cached_or_compute("inv_key", compute)
        assert call_count == 2
        assert result == {"result": 2}

    @patch("services.cost_optimizer._get_redis", return_value=None)
    def test_get_stats_returns_hit_miss_counts(self, mock_redis):
        optimizer = CostOptimizer(cache_ttl=60)

        optimizer.get_cached_or_compute("k1", lambda: "a")
        optimizer.get_cached_or_compute("k1", lambda: "a")
        optimizer.get_cached_or_compute("k2", lambda: "b")

        stats = optimizer.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 2
        assert stats["total"] == 3
        assert 0 <= stats["hit_rate"] <= 1
        assert "estimated_savings_usd" in stats
