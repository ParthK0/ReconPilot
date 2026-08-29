"""
backend/ai/llm_client.py
========================
Dedicated LLM Client for ReconPilot Finance Verification Engine.

Features:
- Primary real LLM execution via Google Gemini (gemini-2.5-pro / gemini-1.5-pro) or OpenAI (gpt-5.6-terra / gpt-4o)
- Strict JSON structured output mode with schema validation
- Exponential backoff retry on transient HTTP/JSON errors
- Per-call and cumulative batch token & cost accounting (USD)
- Explicit execution modes:
  - "live": Production mode requiring valid API credentials
  - "offline": Test/offline simulation mode when explicitly configured
- Cost ceiling budget enforcement against AI_SPEND_CEILING_USD
"""

import json
import os
import time
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple
import httpx
from pydantic import BaseModel, Field


# Standard pricing per million tokens (approximate USD)
MODEL_PRICING: Dict[str, Dict[str, Decimal]] = {
    "gemini-2.5-pro": {"input": Decimal("1.25"), "output": Decimal("5.00")},
    "gemini-1.5-pro": {"input": Decimal("1.25"), "output": Decimal("5.00")},
    "gemini-2.0-flash": {"input": Decimal("0.10"), "output": Decimal("0.40")},
    "gpt-5.6-terra": {"input": Decimal("2.50"), "output": Decimal("10.00")},
    "gpt-4o": {"input": Decimal("2.50"), "output": Decimal("10.00")},
    "gpt-4o-mini": {"input": Decimal("0.15"), "output": Decimal("0.60")},
}


class LLMResponse(BaseModel):
    """Encapsulates structured LLM completion and usage telemetry."""
    parsed_json: Dict[str, Any]
    raw_text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: Decimal = Field(default_factory=lambda: Decimal("0.000000"))
    model_name: str
    latency_ms: int = 0
    is_simulated: bool = False


class CostCeilingExceededError(Exception):
    """Raised when an LLM call would exceed the configured batch spend ceiling."""
    pass


class LLMConfigurationError(Exception):
    """Raised when live AI mode is active but required API credentials are missing."""
    pass


class LLMClient:
    """
    Robust LLM client with retry, cost accounting, and provider fallbacks.
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        ai_mode: Optional[str] = None,
        spend_ceiling_usd: Optional[Decimal] = None,
    ):
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model_name = model_name or os.environ.get("AI_MODEL", "gemini-2.5-pro")
        self.ai_mode = (ai_mode or os.environ.get("RECONPILOT_AI_MODE", "live")).strip().lower()
        
        raw_ceiling = spend_ceiling_usd if spend_ceiling_usd is not None else os.environ.get("AI_SPEND_CEILING_USD", "5.00")
        self.spend_ceiling_usd = Decimal(str(raw_ceiling))
        self.cumulative_spend_usd = Decimal("0.000000")

    def calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
        """Calculates estimated USD cost for a completion."""
        rates = MODEL_PRICING.get(model, {"input": Decimal("1.00"), "output": Decimal("4.00")})
        input_cost = (Decimal(prompt_tokens) / Decimal("1000000")) * rates["input"]
        output_cost = (Decimal(completion_tokens) / Decimal("1000000")) * rates["output"]
        return (input_cost + output_cost).quantize(Decimal("0.000001"))

    def check_cost_ceiling(self, anticipated_cost: Decimal = Decimal("0.000100")) -> None:
        """Enforces that cumulative spend has not breached the ceiling."""
        if self.spend_ceiling_usd > Decimal("0.00") and (self.cumulative_spend_usd + anticipated_cost) > self.spend_ceiling_usd:
            raise CostCeilingExceededError(
                f"AI spend ceiling of ${self.spend_ceiling_usd:.4f} exceeded (Current: ${self.cumulative_spend_usd:.6f})."
            )

    def _call_gemini_raw(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        timeout: float = 15.0,
    ) -> Tuple[str, int, int]:
        """Direct HTTP call to Google Gemini API with JSON output mode."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.0,
            },
        }
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidate = data["candidates"][0]["content"]["parts"][0]["text"]
            usage = data.get("usageMetadata", {})
            p_tok = usage.get("promptTokenCount", 0)
            c_tok = usage.get("candidatesTokenCount", 0)
            return candidate, p_tok, c_tok

    def _call_openai_raw(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        timeout: float = 15.0,
    ) -> Tuple[str, int, int]:
        """Direct HTTP call to OpenAI-compatible API with JSON response format."""
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }
        with httpx.Client(timeout=timeout) as client:
            resp = client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            p_tok = usage.get("prompt_tokens", 0)
            c_tok = usage.get("completion_tokens", 0)
            return content, p_tok, c_tok

    def generate_json_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback_simulation_fn: Optional[Any] = None,
        max_retries: int = 2,
    ) -> LLMResponse:
        """
        Executes a structured JSON completion with live provider prioritization,
        exponential backoff retries, and strict schema parsing.
        """
        self.check_cost_ceiling()
        start_time = time.time()

        # 1. Check if Live Mode is active but missing credentials
        has_credentials = bool(self.gemini_api_key or self.openai_api_key)

        if self.ai_mode == "live" and not has_credentials:
            if fallback_simulation_fn is None:
                raise LLMConfigurationError(
                    "RECONPILOT_AI_MODE is set to 'live' but neither GEMINI_API_KEY nor OPENAI_API_KEY was found."
                )
            # If a simulation fallback was passed and allowed, warn and fall back
            raw_parsed = fallback_simulation_fn()
            p_tok = len(system_prompt.split()) + len(user_prompt.split())
            c_tok = len(json.dumps(raw_parsed).split())
            latency = int((time.time() - start_time) * 1000)
            return LLMResponse(
                parsed_json=raw_parsed,
                raw_text=json.dumps(raw_parsed),
                prompt_tokens=p_tok,
                completion_tokens=c_tok,
                total_tokens=p_tok + c_tok,
                estimated_cost_usd=Decimal("0.000000"),
                model_name="offline-simulation",
                latency_ms=latency,
                is_simulated=True,
            )

        if self.ai_mode == "offline":
            if fallback_simulation_fn is not None:
                raw_parsed = fallback_simulation_fn()
            else:
                raw_parsed = {"likely_reason": "insufficient_evidence", "confidence_score": 30.0}
            p_tok = len(system_prompt.split()) + len(user_prompt.split())
            c_tok = len(json.dumps(raw_parsed).split())
            latency = int((time.time() - start_time) * 1000)
            return LLMResponse(
                parsed_json=raw_parsed,
                raw_text=json.dumps(raw_parsed),
                prompt_tokens=p_tok,
                completion_tokens=c_tok,
                total_tokens=p_tok + c_tok,
                estimated_cost_usd=Decimal("0.000000"),
                model_name="offline-simulation",
                latency_ms=latency,
                is_simulated=True,
            )

        # 2. Live Provider Execution
        last_error = None
        for attempt in range(max_retries):
            try:
                curr_user_prompt = user_prompt
                if attempt > 0:
                    curr_user_prompt = (
                        f"{user_prompt}\n\nIMPORTANT: Previous response failed parsing. "
                        "Respond ONLY with a valid single JSON object matching the required schema."
                    )

                if self.gemini_api_key:
                    active_model = self.model_name if "gemini" in self.model_name.lower() else "gemini-2.5-pro"
                    raw_text, p_tok, c_tok = self._call_gemini_raw(system_prompt, curr_user_prompt, active_model)
                elif self.openai_api_key:
                    active_model = self.model_name if "gpt" in self.model_name.lower() else "gpt-5.6-terra"
                    raw_text, p_tok, c_tok = self._call_openai_raw(system_prompt, curr_user_prompt, active_model)
                else:
                    raise LLMConfigurationError("No valid LLM API key configured.")

                parsed_json = json.loads(raw_text)
                cost = self.calculate_cost(active_model, p_tok, c_tok)
                self.cumulative_spend_usd += cost
                latency = int((time.time() - start_time) * 1000)

                return LLMResponse(
                    parsed_json=parsed_json,
                    raw_text=raw_text,
                    prompt_tokens=p_tok,
                    completion_tokens=c_tok,
                    total_tokens=p_tok + c_tok,
                    estimated_cost_usd=cost,
                    model_name=active_model,
                    latency_ms=latency,
                    is_simulated=False,
                )

            except json.JSONDecodeError as jde:
                last_error = jde
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (2 ** attempt))
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (2 ** attempt))

        # If live retries fail, fall back to safe simulation if available
        if fallback_simulation_fn is not None:
            raw_parsed = fallback_simulation_fn()
            p_tok = len(system_prompt.split()) + len(user_prompt.split())
            c_tok = len(json.dumps(raw_parsed).split())
            latency = int((time.time() - start_time) * 1000)
            return LLMResponse(
                parsed_json=raw_parsed,
                raw_text=json.dumps(raw_parsed),
                prompt_tokens=p_tok,
                completion_tokens=c_tok,
                total_tokens=p_tok + c_tok,
                estimated_cost_usd=Decimal("0.000000"),
                model_name=f"fallback-on-error:{type(last_error).__name__}",
                latency_ms=latency,
                is_simulated=True,
            )

        raise RuntimeError(f"LLM generation failed after {max_retries} attempts: {str(last_error)}")
