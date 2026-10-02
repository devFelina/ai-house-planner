"""Sanitized, in-memory audit events for governed tool executions."""

from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from typing import Any

from app.schemas.workflow_state import ExecutionLogEntry, WorkflowState
from app.utils.tool_audit_persistence import persist_tool_audit_log


MAX_STRING_LENGTH = 200
MAX_ERROR_SUMMARY_LENGTH = 160
MAX_KEY_LENGTH = 80
MAX_COLLECTION_ITEMS = 50
MAX_NESTING_DEPTH = 4

_REDACTED = "[REDACTED]"
_REDACTED_BINARY = "[REDACTED_BINARY]"
_REDACTED_URL = "[REDACTED_URL]"
_UNSUPPORTED = "[UNSUPPORTED]"

_SENSITIVE_KEYS = frozenset({
    "apikey",
    "authorization",
    "token",
    "accesstoken",
    "refreshtoken",
    "secret",
    "password",
    "xinternalapikey",
    "connectionstring",
})

_ERROR_SUMMARIES = {
    "PricingLookupError": "Pricing service unavailable or returned invalid data.",
    "GenerationFailure": "Geometry generation failed validation.",
    "ProviderTimeoutError": "Provider request timed out.",
    "ProviderAuthenticationError": "Provider authentication failed.",
    "ProviderRateLimitError": "Provider rate limit reached.",
    "ProviderQuotaError": "Provider quota exceeded.",
    "ProviderUnavailableError": "Provider unavailable.",
    "ProviderMalformedResponseError": "Provider returned invalid data.",
    "ProviderError": "Provider request failed.",
    "CostCalculationError": "Cost calculation failed validation.",
    "ValueError": "Tool input or output validation failed.",
}


def start_tool_timer() -> float:
    """Return a monotonic timestamp for measuring one logical tool call."""
    return time.perf_counter()


def _duration_ms(started_at: float) -> int:
    """Return non-negative elapsed whole milliseconds from a monotonic start."""
    return max(0, int((time.perf_counter() - started_at) * 1000))


def _normalized_key(key: str) -> str:
    return "".join(character for character in key.casefold() if character.isalnum())


def _is_sensitive_key(key: str) -> bool:
    normalized = _normalized_key(key)
    return (
        normalized in _SENSITIVE_KEYS
        or normalized.endswith("apikey")
        or normalized.endswith("password")
        or normalized.endswith("secret")
        or normalized.endswith("accesstoken")
        or normalized.endswith("refreshtoken")
        or normalized.endswith("connectionstring")
    )


def _bounded_string(value: str) -> str:
    stripped = value.strip()
    if stripped.casefold().startswith(("http://", "https://")):
        return _REDACTED_URL
    return stripped[:MAX_STRING_LENGTH]


def _sanitize_value(value: Any, *, depth: int) -> Any:
    if depth > MAX_NESTING_DEPTH:
        return _UNSUPPORTED
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        return _bounded_string(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return _REDACTED_BINARY
    if isinstance(value, (list, tuple)):
        return [
            _sanitize_value(item, depth=depth + 1)
            for item in value[:MAX_COLLECTION_ITEMS]
        ]
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= MAX_COLLECTION_ITEMS:
                break
            if not isinstance(key, str):
                continue
            safe_key = key[:MAX_KEY_LENGTH]
            sanitized[safe_key] = (
                _REDACTED
                if _is_sensitive_key(key)
                else _sanitize_value(item, depth=depth + 1)
            )
        return sanitized
    return _UNSUPPORTED


def sanitize_summary(summary: dict[str, Any] | None) -> dict[str, Any] | None:
    """Validate an explicitly built summary without inspecting arbitrary objects."""
    if summary is None:
        return None
    return _sanitize_value(summary, depth=0)


def sanitize_tool_error(error: Exception) -> tuple[str, str]:
    """Return a safe exception type and controlled, bounded summary."""
    error_type = type(error).__name__[:MAX_KEY_LENGTH] or "Exception"
    class_names = [base.__name__ for base in type(error).__mro__]
    summary = next(
        (_ERROR_SUMMARIES[name] for name in class_names if name in _ERROR_SUMMARIES),
        "Tool execution failed.",
    )
    return error_type, summary[:MAX_ERROR_SUMMARY_LENGTH]


def log_tool_success(
    *,
    state: WorkflowState,
    agent_name: str,
    tool_name: str,
    started_at: float,
    input_summary: dict[str, Any] | None = None,
    output_summary: dict[str, Any] | None = None,
) -> None:
    """Append exactly one sanitized successful tool-call event."""
    state.execution_log.append(ExecutionLogEntry(
        agent_name=agent_name,
        action="tool_call_succeeded",
        tool_called=tool_name,
        duration_ms=_duration_ms(started_at),
        result="success",
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        event_status="succeeded",
        input_summary=sanitize_summary(input_summary),
        output_summary=sanitize_summary(output_summary),
        error_type=None,
        error_summary=None,
    ))
    persist_tool_audit_log(state.workflow_id, state.execution_log)


def log_tool_failure(
    *,
    state: WorkflowState,
    agent_name: str,
    tool_name: str,
    started_at: float,
    input_summary: dict[str, Any] | None,
    error: Exception,
    output_summary: dict[str, Any] | None = None,
) -> None:
    """Append exactly one sanitized failed tool-call event."""
    error_type, error_summary = sanitize_tool_error(error)
    state.execution_log.append(ExecutionLogEntry(
        agent_name=agent_name,
        action="tool_call_failed",
        tool_called=tool_name,
        duration_ms=_duration_ms(started_at),
        result="failed",
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        event_status="failed",
        input_summary=sanitize_summary(input_summary),
        output_summary=sanitize_summary(output_summary),
        error_type=error_type,
        error_summary=error_summary,
    ))
    persist_tool_audit_log(state.workflow_id, state.execution_log)
