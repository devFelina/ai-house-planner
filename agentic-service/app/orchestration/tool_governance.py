"""Deny-by-default authorization policy for workflow agent tools."""

from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.workflow_state import ExecutionLogEntry, WorkflowState
from app.utils.tool_audit_persistence import persist_tool_audit_log


AGENT_TOOL_ALLOWLIST: dict[str, frozenset[str]] = {
    "requirement_analysis": frozenset({
        "requirement_extractor",
    }),
    "land_analysis": frozenset({
        "terrain_classifier",
    }),
    "design": frozenset({
        "geometry_generator",
    }),
    "visualization": frozenset({
        "visualization_generator",
    }),
    "construction_planning": frozenset({
        "construction_scheduler",
    }),
    "cost_estimation": frozenset({
        "pricing_lookup",
    }),
    "validation": frozenset(),
}

KNOWN_TOOLS = frozenset({
    "requirement_extractor",
    "terrain_classifier",
    "geometry_generator",
    "visualization_generator",
    "construction_scheduler",
    "pricing_lookup",
})


class ToolAuthorizationError(PermissionError):
    """Raised when an agent is not authorized to invoke a governed tool."""


def is_tool_allowed(agent_name: str, tool_name: str) -> bool:
    """Return whether a known agent may invoke a known governed tool."""
    if agent_name not in AGENT_TOOL_ALLOWLIST or tool_name not in KNOWN_TOOLS:
        return False
    return tool_name in AGENT_TOOL_ALLOWLIST[agent_name]


def assert_tool_allowed(agent_name: str, tool_name: str) -> None:
    """Raise ``ToolAuthorizationError`` unless the exact pair is authorized."""
    if agent_name not in AGENT_TOOL_ALLOWLIST:
        raise ToolAuthorizationError(f"Unknown agent '{agent_name}'")
    if tool_name not in KNOWN_TOOLS:
        raise ToolAuthorizationError(f"Unknown tool '{tool_name}'")
    if tool_name not in AGENT_TOOL_ALLOWLIST[agent_name]:
        raise ToolAuthorizationError(
            f"Agent '{agent_name}' is not allowed to use tool '{tool_name}'"
        )


def mark_tool_authorization_failure(
    state: WorkflowState,
    agent_name: str,
    tool_name: str,
    error: ToolAuthorizationError,
) -> WorkflowState:
    """Fail a workflow safely and record only sanitized authorization details."""
    state.status = "failed"
    state.execution_log.append(
        ExecutionLogEntry(
            agent_name=agent_name,
            action="tool_authorization_denied",
            tool_called=tool_name,
            result=str(error),
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        )
    )
    persist_tool_audit_log(state.workflow_id, state.execution_log)
    return state
