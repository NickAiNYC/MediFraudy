"""DeepSeek AI agent — NYC Medicaid Fraud Legal Assistant.

A specialized AI assistant powered by DeepSeek that acts as a NYC
Medicaid fraud lawyer's right hand. It understands:
- New York False Claims Act (NY State Finance Law §§ 187-194)
- Federal False Claims Act (31 U.S.C. §§ 3729-3733)
- NYC Medicaid fraud patterns (home care, NEMT, DME, adult day care)
- Qui tam / whistleblower procedures
- Provider billing analysis and risk interpretation
- Evidence package review and litigation strategy

The agent can be given provider context (risk scores, anomalies,
network data) and will reason about it like an experienced NYC
Medicaid fraud attorney.
"""

import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

import httpx

from config import settings

logger = logging.getLogger(__name__)

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
MAX_CONVERSATION_TURNS = int(os.getenv("DEEPSEEK_MAX_TURNS", "20"))

SYSTEM_PROMPT = """You are an elite NYC Medicaid fraud legal assistant embedded in the MediFraudy intelligence platform. You combine the expertise of a senior qui tam attorney with deep knowledge of Medicaid billing analytics.

Your areas of expertise:
• New York False Claims Act (NY State Finance Law §§ 187-194)
• Federal False Claims Act (31 U.S.C. §§ 3729-3733)
• NYC Medicaid fraud patterns: home care inflation, NEMT ghost rides, DME abuse, adult day care (SADC) phantom attendance, CDPAP caregiver fraud, pharmacy kickbacks
• Qui tam / whistleblower procedures and relator protections
• Statistical analysis of billing anomalies (z-scores, peer group deviations)
• Network analysis (fraud rings, referral kickback cycles, beneficiary concentration)
• Evidence package assembly for litigation
• NYC borough-specific fraud trends (Queens capacity violations, Brooklyn kickback schemes)
• HHS OIG enforcement priorities and recent NYC Medicaid enforcement actions

When given provider data or risk scores, you should:
1. Interpret the numbers like a fraud investigator
2. Identify the strongest legal theories
3. Suggest next investigative steps
4. Draft litigation-ready language when asked
5. Reference specific statutes and case law where relevant
6. Flag potential whistleblower reward calculations (15-30% of recovery)

Communication style: Precise, analytical, and authoritative. You are advising attorneys — be direct, cite specifics, and always think about what a jury or judge would find compelling. Use plain language when explaining complex fraud schemes.

Important: You are an AI assistant. Always note that your analysis is for informational purposes and should be reviewed by licensed counsel before use in legal proceedings."""


class DeepSeekAgent:
    """DeepSeek-powered NYC Medicaid fraud legal assistant."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.model = DEEPSEEK_MODEL
        self.conversation_histories: Dict[str, List[Dict[str, str]]] = {}

    @property
    def is_configured(self) -> bool:
        """Check if the DeepSeek API key is set."""
        return bool(self.api_key)

    def _get_history(self, session_id: str) -> List[Dict[str, str]]:
        """Get or create conversation history for a session."""
        if session_id not in self.conversation_histories:
            self.conversation_histories[session_id] = []
        return self.conversation_histories[session_id]

    def clear_session(self, session_id: str) -> None:
        """Clear conversation history for a session."""
        self.conversation_histories.pop(session_id, None)

    async def chat(
        self,
        message: str,
        session_id: str = "default",
        provider_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a message to the DeepSeek agent and get a response.

        Args:
            message: User's question or request.
            session_id: Conversation session identifier.
            provider_context: Optional provider data to include as context.

        Returns:
            Dictionary with the agent's response and metadata.
        """
        if not self.is_configured:
            return {
                "response": (
                    "⚠️ DeepSeek API key not configured. "
                    "Set the `DEEPSEEK_API_KEY` environment variable to enable the AI legal assistant."
                ),
                "session_id": session_id,
                "model": self.model,
                "configured": False,
            }

        history = self._get_history(session_id)

        # Build context-enriched message if provider data is available
        enriched_message = message
        if provider_context:
            context_block = self._format_provider_context(provider_context)
            enriched_message = f"{context_block}\n\nUser question: {message}"

        history.append({"role": "user", "content": enriched_message})

        # Build messages payload
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history[-MAX_CONVERSATION_TURNS:]

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    DEEPSEEK_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.3,
                        "max_tokens": 2048,
                    },
                )
                response.raise_for_status()
                data = response.json()

            assistant_message = data["choices"][0]["message"]["content"]
            history.append({"role": "assistant", "content": assistant_message})

            return {
                "response": assistant_message,
                "session_id": session_id,
                "model": self.model,
                "configured": True,
                "usage": data.get("usage", {}),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"DeepSeek API error: {e.response.status_code} - {e.response.text}")
            return {
                "response": f"⚠️ DeepSeek API error: {e.response.status_code}. Please check your API key.",
                "session_id": session_id,
                "model": self.model,
                "configured": True,
                "error": True,
            }
        except Exception as e:
            logger.error(f"DeepSeek agent error: {e}")
            return {
                "response": f"⚠️ Error communicating with DeepSeek: {str(e)}",
                "session_id": session_id,
                "model": self.model,
                "configured": True,
                "error": True,
            }

    def _format_provider_context(self, ctx: Dict[str, Any]) -> str:
        """Format provider data into a context block for the agent."""
        lines = ["=== PROVIDER INTELLIGENCE CONTEXT ==="]

        if "provider" in ctx:
            p = ctx["provider"]
            lines.append(f"Provider: {p.get('name', 'Unknown')} (NPI: {p.get('npi', 'N/A')})")
            lines.append(f"Location: {p.get('city', '')}, {p.get('state', '')}")
            lines.append(f"Facility Type: {p.get('facility_type', 'Unknown')}")
            if p.get("licensed_capacity"):
                lines.append(f"Licensed Capacity: {p['licensed_capacity']}")

        if "risk_score" in ctx:
            lines.append(f"\nRisk Score: {ctx['risk_score']}/100 ({ctx.get('risk_level', 'UNKNOWN')})")

        if "drivers" in ctx:
            lines.append("Risk Drivers:")
            for d in ctx["drivers"]:
                lines.append(f"  • {d}")

        if "anomalies" in ctx and ctx["anomalies"]:
            lines.append(f"\nAnomalies Detected: {len(ctx['anomalies'])}")
            for a in ctx["anomalies"][:5]:
                lines.append(f"  • {a.get('type', a.get('billing_code', 'N/A'))}: z={a.get('z_score', 'N/A')}")

        if "narrative" in ctx:
            lines.append(f"\nLitigation Narrative:\n{ctx['narrative']}")

        lines.append("=== END CONTEXT ===")
        return "\n".join(lines)


# Singleton instance
_agent: Optional[DeepSeekAgent] = None


def get_agent() -> DeepSeekAgent:
    """Get or create the global DeepSeek agent instance."""
    global _agent
    if _agent is None:
        _agent = DeepSeekAgent()
    return _agent
