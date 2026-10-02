"""Best-effort persistence for sanitized governed-tool audit events."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from typing import Any

import requests

from app.config import ASPNET_API_URL, INTERNAL_API_KEY
from app.schemas.workflow_state import ExecutionLogEntry


logger = logging.getLogger(__name__)

AUDIT_ACTIONS = frozenset({
    "tool_call_succeeded",
    "tool_call_failed",
    "tool_authorization_denied",
})
MAX_ATTEMPTS = 2
REQUEST_TIMEOUT_SECONDS = 10
RETRY_DELAY_SECONDS = 0.1


def _serialize_event(entry: ExecutionLogEntry) -> dict[str, Any]:
    return {
        "agentName": entry.agent_name,
        "action": entry.action,
        "toolCalled": entry.tool_called,
        "durationMs": entry.duration_ms,
        "result": entry.result,
        "eventStatus": entry.event_status,
        "inputSummary": entry.input_summary,
        "outputSummary": entry.output_summary,
        "errorType": entry.error_type,
        "errorSummary": entry.error_summary,
        "createdAtUtc": entry.created_at_utc,
    }


def build_tool_audit_payload(
    execution_log: Iterable[ExecutionLogEntry],
) -> dict[str, list[dict[str, Any]]]:
    """Return only granular tool audit events in the internal API contract."""
    return {
        "entries": [
            _serialize_event(entry)
            for entry in execution_log
            if entry.action in AUDIT_ACTIONS
        ]
    }


def persist_tool_audit_log(
    workflow_id: object,
    execution_log: Iterable[ExecutionLogEntry],
) -> bool:
    """Persist the complete audit list with bounded retry; never raise."""
    payload = build_tool_audit_payload(execution_log)
    if not payload["entries"]:
        return True

    endpoint = (
        f"{ASPNET_API_URL.rstrip('/')}/internal/workflows/"
        f"{workflow_id}/tool-audit-log"
    )
    headers = {
        "X-Internal-API-Key": INTERNAL_API_KEY,
        "Content-Type": "application/json",
    }

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.patch(
                endpoint,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if response.ok:
                return True
            logger.warning(
                "Tool audit persistence failed (attempt %d/%d, HTTP %s).",
                attempt,
                MAX_ATTEMPTS,
                response.status_code,
            )
        except requests.RequestException as exc:
            logger.warning(
                "Tool audit persistence failed (attempt %d/%d, %s).",
                attempt,
                MAX_ATTEMPTS,
                type(exc).__name__,
            )

        if attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_DELAY_SECONDS)

    return False
