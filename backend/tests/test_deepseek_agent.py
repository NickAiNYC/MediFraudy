"""Tests for the DeepSeek AI legal assistant."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.deepseek_agent import DeepSeekAgent, get_agent, SYSTEM_PROMPT


class TestDeepSeekAgentConfig:
    """Test agent configuration."""

    def test_not_configured_without_key(self):
        """Agent should report not configured without API key."""
        agent = DeepSeekAgent(api_key="")
        assert agent.is_configured is False

    def test_configured_with_key(self):
        """Agent should report configured with API key."""
        agent = DeepSeekAgent(api_key="sk-test-key")
        assert agent.is_configured is True

    def test_system_prompt_contains_fca(self):
        """System prompt must reference the False Claims Act."""
        assert "False Claims Act" in SYSTEM_PROMPT

    def test_system_prompt_contains_nyc(self):
        """System prompt must reference NYC-specific fraud patterns."""
        assert "NYC" in SYSTEM_PROMPT
        assert "home care" in SYSTEM_PROMPT.lower()

    def test_system_prompt_contains_qui_tam(self):
        """System prompt must reference qui tam procedures."""
        assert "qui tam" in SYSTEM_PROMPT.lower() or "Qui tam" in SYSTEM_PROMPT

    def test_system_prompt_contains_whistleblower(self):
        """System prompt must reference whistleblower protections."""
        assert "whistleblower" in SYSTEM_PROMPT.lower()


class TestDeepSeekAgentSessions:
    """Test conversation session management."""

    def test_session_starts_empty(self):
        """New sessions should have empty history."""
        agent = DeepSeekAgent(api_key="sk-test")
        history = agent._get_history("test-session")
        assert history == []

    def test_clear_session(self):
        """Clearing a session should remove its history."""
        agent = DeepSeekAgent(api_key="sk-test")
        agent._get_history("s1").append({"role": "user", "content": "test"})
        assert len(agent._get_history("s1")) == 1

        agent.clear_session("s1")
        assert len(agent._get_history("s1")) == 0

    def test_separate_sessions(self):
        """Different session IDs should have separate histories."""
        agent = DeepSeekAgent(api_key="sk-test")
        agent._get_history("s1").append({"role": "user", "content": "hello"})
        agent._get_history("s2").append({"role": "user", "content": "world"})

        assert len(agent._get_history("s1")) == 1
        assert len(agent._get_history("s2")) == 1
        assert agent._get_history("s1")[0]["content"] == "hello"
        assert agent._get_history("s2")[0]["content"] == "world"


class TestDeepSeekAgentChat:
    """Test chat functionality."""

    @pytest.mark.asyncio
    async def test_unconfigured_returns_warning(self):
        """Chat without API key should return a helpful warning."""
        agent = DeepSeekAgent(api_key="")
        result = await agent.chat("Hello")
        assert result["configured"] is False
        assert "DEEPSEEK_API_KEY" in result["response"]

    def test_format_provider_context(self):
        """Provider context should be formatted correctly."""
        agent = DeepSeekAgent(api_key="sk-test")
        ctx = {
            "provider": {
                "name": "Sunrise Adult Day Care",
                "npi": "1234567890",
                "city": "Queens",
                "state": "NY",
                "facility_type": "adult_day_care",
                "licensed_capacity": 75,
            },
            "risk_score": 94,
            "risk_level": "HIGH",
            "drivers": [
                "Billing 4.8x peer average",
                "Capacity violation: 312% excess",
            ],
            "anomalies": [
                {"billing_code": "97110", "z_score": 6.2, "type": "high_volume"},
            ],
        }
        formatted = agent._format_provider_context(ctx)

        assert "Sunrise Adult Day Care" in formatted
        assert "1234567890" in formatted
        assert "94" in formatted
        assert "HIGH" in formatted
        assert "4.8x peer average" in formatted
        assert "high_volume" in formatted
        assert "6.2" in formatted

    def test_format_empty_context(self):
        """Empty context should still produce valid output."""
        agent = DeepSeekAgent(api_key="sk-test")
        formatted = agent._format_provider_context({})
        assert "PROVIDER INTELLIGENCE CONTEXT" in formatted


class TestAgentSingleton:
    """Test the global agent singleton."""

    def test_get_agent_returns_instance(self):
        """get_agent should return a DeepSeekAgent instance."""
        agent = get_agent()
        assert isinstance(agent, DeepSeekAgent)

    def test_get_agent_returns_same_instance(self):
        """get_agent should return the same instance on repeated calls."""
        a1 = get_agent()
        a2 = get_agent()
        assert a1 is a2
