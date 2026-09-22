from __future__ import annotations
import json
import re
from urllib.parse import urlparse
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

class AIClient:
    """
    Enterprise AI Client for Azure AI Luna with built-in SSRF protection,
    credential redaction in exception handling, prompt injection defense,
    and HTTP connection pooling.
    """
    def __init__(self, endpoint: str, api_key: str, model: str = "hack-fest-gpt-5.6-luna"):
        self.raw_endpoint = endpoint.strip()
        self.endpoint = self._validate_and_format_endpoint(self.raw_endpoint)
        self.raw_key = api_key.strip()
        self.api_key = self.raw_key if self.raw_key.startswith("Bearer ") else f"Bearer {self.raw_key}"
        self.model = model.strip() or "hack-fest-gpt-5.6-luna"
        self._cached_client: ChatCompletionsClient | None = None

    @staticmethod
    def _validate_and_format_endpoint(url: str) -> str:
        """
        CWE-918: Mitigate SSRF by enforcing strict HTTP/HTTPS URL schemas
        and rejecting malicious protocols (file://, gopher://, ftp://).
        """
        if not url:
            raise ValueError("Endpoint URL cannot be empty.")
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid URL protocol '{parsed.scheme}'. Only HTTPS and HTTP endpoints are permitted.")
        if not parsed.netloc:
            raise ValueError("Invalid endpoint URL: missing host/domain.")
        return url.rstrip("/") + "/"

    def _client(self) -> ChatCompletionsClient:
        """Reuse existing client instance to benefit from HTTP connection pooling."""
        if self._cached_client is None:
            self._cached_client = ChatCompletionsClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key),
                api_version="2025-03-01-preview",
                connection_timeout=10,
                read_timeout=15
            )
        return self._cached_client

    def _redact_secrets(self, msg: str) -> str:
        """
        CWE-200 / CWE-522: Scrub Bearer tokens, API keys, and Authorization headers
        from error strings before exposing them to logs or UI notifications.
        """
        if not msg:
            return ""
        scrubbed = str(msg)
        if self.raw_key and len(self.raw_key) > 4:
            scrubbed = scrubbed.replace(self.raw_key, "[REDACTED_KEY]")
            scrubbed = scrubbed.replace(self.api_key, "[REDACTED_KEY]")
        # Redact generic Bearer patterns
        scrubbed = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]{8,}", r"\1[REDACTED_TOKEN]", scrubbed, flags=re.IGNORECASE)
        # Redact api-key header values
        scrubbed = re.sub(r"(api[-_]key[:=]\s*)[A-Za-z0-9_\-\.]{8,}", r"\1[REDACTED_KEY]", scrubbed, flags=re.IGNORECASE)
        return scrubbed

    @staticmethod
    def usage(response) -> dict[str, int]:
        u = getattr(response, "usage", None)
        return {
            "Prompt Tokens": getattr(u, "prompt_tokens", 0) or 0,
            "Completion Tokens": getattr(u, "completion_tokens", 0) or 0,
            "Total Tokens": getattr(u, "total_tokens", 0) or 0
        }

    def test_connection(self) -> tuple[bool, str, dict[str, int]]:
        try:
            r = self._client().complete(
                messages=[UserMessage(content="Reply only with OK")],
                model=self.model,
                headers={"Authorization": self.api_key}
            )
            content = r.choices[0].message.content if r.choices else "OK"
            return True, content, self.usage(r)
        except Exception as exc:
            msg = self._redact_secrets(str(exc))
            if "timed out" in msg.lower() or "connection" in msg.lower():
                msg = f"{msg}\n\nNote: The host resolves to an internal network (10.x.x.x). Please ensure your corporate VPN (GlobalProtect/AnyConnect) is connected."
            return False, msg, {"Prompt Tokens": 0, "Completion Tokens": 0, "Total Tokens": 0}

    def recommend(self, prompt: str) -> tuple[str, dict[str, int]]:
        try:
            r = self._client().complete(
                messages=[
                    SystemMessage(content="You standardize client shipment data. Return concise JSON only."),
                    UserMessage(content=prompt)
                ],
                model=self.model,
                headers={"Authorization": self.api_key}
            )
            content = r.choices[0].message.content if r.choices else "{}"
            return content, self.usage(r)
        except Exception as exc:
            raise RuntimeError(self._redact_secrets(str(exc))) from None

    def recommend_classification(self, samples_dict: dict[str, list[str]]) -> tuple[dict, dict[str, int]]:
        """
        Classifies columns with Prompt Injection defense:
        - Strict JSON encoding of inputs so malicious column names cannot break prompt grammar.
        - Truncation of values to prevent prompt bloating and token exhaustion attacks.
        """
        safe_samples = {}
        for col, vals in samples_dict.items():
            safe_col = str(col)[:80]
            safe_vals = [str(v)[:80] for v in (vals or [])[:4]]
            safe_samples[safe_col] = safe_vals

        prompt_lines = [
            "Classify each of the following dataset columns into one of the canonical NielsenIQ (NIQ) fields:",
            "Allowed Fields: Country, Region, Channel, City/State, Category, Brand, SKU, Fact, Time Period, Ignore",
            "",
            "Definitions:",
            "- Country: Country or sovereign market name/code.",
            "- Region: Macro geographical area, sales zone, territory.",
            "- Channel: Trade type or distribution channel (e.g., E-commerce, Modern Trade, Traditional Trade).",
            "- City/State: Specific city, state, province, or destination location.",
            "- Category: High-level product category, product group, department.",
            "- Brand: Brand name, brand description.",
            "- SKU: Unique product ID, material code, item number, barcode.",
            "- Fact: Measure type (e.g. Sales Value, Units, Volume, Price).",
            "- Time Period: Specific time period metric in wide columns (e.g. JAN_2026, 2026_WK01).",
            "- Ignore: Transactional date, row counters, or non-hierarchical client metadata.",
            "",
            "Columns and sample values provided as JSON payload below:",
            json.dumps(safe_samples, ensure_ascii=True, indent=2),
            "",
            'Respond ONLY with valid JSON mapping each column name to an object with "field", "confidence" (0.0-1.0), and "reason". Example:',
            '{"COLUMN_X": {"field": "Region", "confidence": 0.95, "reason": "Zone description"}}'
        ]
        prompt = "\n".join(prompt_lines)
        try:
            content, usage = self.recommend(prompt)
            clean_json = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.IGNORECASE)
            clean_json = re.sub(r"\s*```$", "", clean_json.strip())
            parsed = json.loads(clean_json)
            if not isinstance(parsed, dict):
                return {}, {"Prompt Tokens": 0, "Completion Tokens": 0, "Total Tokens": 0}
            return parsed, usage
        except Exception:
            return {}, {"Prompt Tokens": 0, "Completion Tokens": 0, "Total Tokens": 0}
