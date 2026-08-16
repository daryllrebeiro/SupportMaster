"""Conservative redaction for telemetry and audit payloads."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


_SENSITIVE_KEY = re.compile(
    r"(?:pass(word)?|secret|token|api[_-]?key|auth(?:orization)?|cookie|private[_-]?key|credential)",
    re.IGNORECASE,
)
_SECRET_TEXT = re.compile(
    r"(?i)(bearer\s+|(?:api[_-]?key|token|password|secret)\s*[:=]\s*)([^\s,;]+)"
)


class Redactor:
    """Redact known secret fields and common inline credential patterns."""

    def __init__(self, *, replacement: str = "[REDACTED]", max_string_length: int = 8_000) -> None:
        self.replacement = replacement
        self.max_string_length = max_string_length

    def text(self, value: str) -> str:
        redacted = _SECRET_TEXT.sub(lambda match: f"{match.group(1)}{self.replacement}", value)
        if len(redacted) > self.max_string_length:
            return redacted[: self.max_string_length] + "...[TRUNCATED]"
        return redacted

    def value(self, value: Any, *, key: str | None = None) -> Any:
        if key and _SENSITIVE_KEY.search(key):
            return self.replacement
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, Mapping):
            return {str(k): self.value(v, key=str(k)) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.value(item) for item in value]
        if isinstance(value, set):
            return [self.value(item) for item in sorted(value, key=str)]
        return value

    def mapping(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return self.value(value)
