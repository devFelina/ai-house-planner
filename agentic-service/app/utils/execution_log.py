"""
app/utils/execution_log.py
==========================
Centralised helper that converts a WorkflowState's existing execution_log
list into the simplified timeline format the frontend expects, then PATCHes
it to the ASP.NET Core internal API.

Format pushed to ASP.NET:
[
    {"agent": "coordinator",            "status": "completed", "message": "Workflow initialised"},
    {"agent": "requirement_analysis",   "status": "completed", "message": "Requirements extracted"},
    ...
]

Rules:
- One entry per workflow node (agent_name field on ExecutionLogEntry).
- Uses only data already recorded in state.execution_log — NO new AI calls.
- If the HTTP call fails the function logs a warning and returns silently so
  the workflow itself is never blocked.
"""
from __future__ import annotations

import json
import logging

import requests

from app.config import ASPNET_API_URL, INTERNAL_API_KEY
from app.schemas.workflow_state import WorkflowState

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────
# Agent-name → canonical display label mapping.
# Keeps the frontend label stable regardless of internal refactors.
# ──────────────────────────────────────────────────────────────────
_AGENT_LABELS: dict[str, str] = {
    "CoordinatorAgent":           "coordinator",
    "RequirementAnalysisAgent":   "requirement_analysis",
    "LandAnalysisAgent":          "land_analysis",
    "DesignAgent":                "design",
    "ConstructionPlanningAgent":  "construction_planning",
    "CostEstimationAgent":        "cost_estimation",
    "ValidationAgent":            "validation",
    "RenderingAgent":             "rendering",
}


def _build_timeline(state: WorkflowState) -> list[dict]:
    """
    Collapse the granular ExecutionLogEntry list into one entry per agent.
    The *last* entry for each agent wins (captures the final action/result).
    Order is preserved by first occurrence.
    """
    seen: dict[str, dict] = {}  # agent-label → latest entry dict
    order: list[str] = []       # preserves insertion order

    for entry in state.execution_log:
        raw_name = entry.agent_name if hasattr(entry, "agent_name") else entry.get("agent_name", "")
        label = _AGENT_LABELS.get(raw_name, raw_name.lower())
        action = entry.action if hasattr(entry, "action") else entry.get("action", "")
        result = entry.result if hasattr(entry, "result") else entry.get("result", "")

        # Determine status: if result looks like a failure, mark failed
        status = "failed" if any(
            kw in str(result).lower() for kw in ("fail", "error", "exception")
        ) else "completed"

        if label not in seen:
            order.append(label)

        seen[label] = {
            "agent":   label,
            "status":  status,
            "message": action,
        }

    return [seen[label] for label in order]


def push_execution_log(state: WorkflowState) -> None:
    """
    Build the simplified timeline from state.execution_log and PATCH it to
    the ASP.NET Core internal API endpoint:

        PATCH /api/v1/internal/workflows/{workflow_id}/execution-log

    Failures are non-fatal — a warning is logged and the function returns.
    """
    if not state.execution_log:
        logger.debug("[ExecutionLog] No entries to push for workflow %s", state.workflow_id)
        return

    timeline = _build_timeline(state)

    try:
        response = requests.patch(
            f"{ASPNET_API_URL}/internal/workflows/{state.workflow_id}/execution-log",
            data=json.dumps(timeline),
            headers={
                "X-Internal-API-Key": INTERNAL_API_KEY,
                "Content-Type": "application/json",
            },
            timeout=8,
        )
        if response.ok:
            logger.info(
                "[ExecutionLog] Pushed %d entries for workflow %s",
                len(timeline), state.workflow_id,
            )
        else:
            logger.warning(
                "[ExecutionLog] PATCH failed for workflow %s: %s %s",
                state.workflow_id, response.status_code, response.text[:200],
            )
    except requests.RequestException as exc:
        logger.warning(
            "[ExecutionLog] Could not reach ASP.NET for workflow %s: %s",
            state.workflow_id, exc,
        )
