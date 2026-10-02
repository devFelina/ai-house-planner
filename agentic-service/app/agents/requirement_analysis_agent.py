"""
Requirement Analysis Agent — LangGraph node.

Converts a free-text natural language prompt into a structured preferences dict
that is merged into WorkflowState.input_data.preferences before design selection.

Rules:
- Only extracts requirements, never generates room layouts or coordinates.
- Uses OpenAIProvider exclusively.
- Existing explicit user preferences always take priority over AI-inferred values.
- If no prompt is present, state is returned unchanged.
- Provider failures are logged and the node exits gracefully (state unchanged).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.providers.openai_provider import OpenAIProvider
from app.providers.base_provider import ProviderError
from app.schemas.workflow_state import ExecutionLogEntry, WorkflowState
from app.services.ai_guard import execute_once
from app.orchestration.tool_governance import (
    ToolAuthorizationError,
    assert_tool_allowed,
    mark_tool_authorization_failure,
)
from app.orchestration.tool_audit import (
    log_tool_failure,
    log_tool_success,
    start_tool_timer,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Structured output schema — OpenAI Structured Outputs mode
# ---------------------------------------------------------------------------

class ExtractedRequirements(BaseModel):
    """Strict schema for LLM output. All fields are nullable so the model
    only populates what it can clearly infer from the text."""
    bedrooms: int | None = Field(None, description="Number of bedrooms (1-8)")
    bathrooms: int | None = Field(None, description="Number of bathrooms (1-6)")
    floors: int | None = Field(None, description="Number of floors (1-3)")
    architecturalStyle: str | None = Field(None, description="e.g. 'modern minimalist', 'tropical', 'conventional'")
    homeOffice: bool | None = Field(None, description="Requires a home office room")
    accessibility: bool | None = Field(None, description="Requires wheelchair-accessible layout")
    separateDining: bool | None = Field(None, description="Requires a separate dining room")
    parkingRequired: bool | None = Field(None, description="Requires a parking space")
    masterEnsuite: bool | None = Field(None, description="Requires a master bedroom with ensuite bathroom")


# ---------------------------------------------------------------------------
# System prompt — strictly scoped to extraction, no geometry
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a house requirement extraction assistant for a Sri Lankan housing platform.

Your ONLY job is to extract structured house requirements from the user's description.

STRICT RULES:
- Return ONLY a JSON object matching the provided schema.
- Do NOT generate room layouts, coordinates, or dimensions.
- Do NOT select or recommend a house plan.
- Do NOT invent requirements that are not clearly implied by the text.
- If a requirement is ambiguous or not mentioned, return null for that field.
- Floors must be 1, 2, or 3 only. Bedrooms 1-8. Bathrooms 1-6.
- Architectural style must be one of: conventional, modern minimalist, tropical,
  contemporary, colonial, bungalow, mediterranean, or null if unclear.
"""


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

_provider = OpenAIProvider()


def requirement_analysis_node(state: WorkflowState) -> WorkflowState:
    """
    LangGraph node. Reads state.input_data.natural_language_prompt.
    If present, calls OpenAI to extract structured requirements and merges
    them into state.input_data.preferences. Explicit preferences take priority.
    Returns state unchanged if prompt is absent or provider is unavailable.
    """
    if not state.input_data:
        return state

    prompt = (state.input_data.natural_language_prompt or "").strip()
    if not prompt:
        logger.info("[RequirementAnalysis] No natural language prompt — skipping.")
        return state

    print(f"[Requirement Analysis] Processing prompt ({len(prompt)} chars)")
    existing = dict(state.input_data.preferences or {})
    tool_input = {
        "prompt_present": True,
        "prompt_chars": len(prompt),
        "explicit_preference_keys": sorted(existing),
    }

    try:
        assert_tool_allowed("requirement_analysis", "requirement_extractor")
        started_at = start_tool_timer()
        raw, _ = execute_once(
            state.workflow_id,
            "requirement_analysis",
            lambda: _provider.generate_json(
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=f"Extract house requirements from this description:\n\n{prompt}",
                schema=ExtractedRequirements,
                max_tokens=400,
                purpose="requirement_analysis",
            ),
        )
    except ToolAuthorizationError as exc:
        return mark_tool_authorization_failure(
            state, "RequirementAnalysisAgent", "requirement_extractor", exc
        )
    except ProviderError as exc:
        log_tool_failure(
            state=state,
            agent_name="requirement_analysis",
            tool_name="requirement_extractor",
            started_at=started_at,
            input_summary=tool_input,
            error=exc,
        )
        logger.warning("[RequirementAnalysis] Provider unavailable (%s) — state unchanged.", exc)
        state.execution_log.append(ExecutionLogEntry(
            agent_name="RequirementAnalysisAgent",
            action="Natural language extraction skipped — provider error",
            result=str(exc),
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        ))
        return state
    except Exception as exc:
        log_tool_failure(
            state=state,
            agent_name="requirement_analysis",
            tool_name="requirement_extractor",
            started_at=started_at,
            input_summary=tool_input,
            error=exc,
        )
        logger.error("[RequirementAnalysis] Unexpected error: %s", exc)
        state.execution_log.append(ExecutionLogEntry(
            agent_name="RequirementAnalysisAgent",
            action="Natural language extraction failed",
            result=str(exc),
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        ))
        return state

    # Map AI camelCase output keys → preference keys used by prepare_inputs()
    _KEY_MAP = {
        "bedrooms": "bedrooms",
        "bathrooms": "bathrooms",
        "floors": "floors",
        "architecturalStyle": "style",
        "homeOffice": "home_office",
        "accessibility": "accessibility",
        "separateDining": "separate_dining",
        "parkingRequired": "parking_required",
        "masterEnsuite": "master_ensuite",
    }

    ai_preferences: dict[str, Any] = {}
    for ai_key, pref_key in _KEY_MAP.items():
        value = raw.get(ai_key)
        if value is not None:
            ai_preferences[pref_key] = value

    # Merge: AI inferences form the base; existing explicit preferences override
    merged = {**ai_preferences, **existing}   # existing keys win

    state.input_data.preferences = merged

    inferred_count = sum(1 for k in ai_preferences if k not in existing)
    log_tool_success(
        state=state,
        agent_name="requirement_analysis",
        tool_name="requirement_extractor",
        started_at=started_at,
        input_summary=tool_input,
        output_summary={
            "extracted_keys": sorted(ai_preferences),
            "fields_extracted": len(ai_preferences),
            "inferences_applied": inferred_count,
            "explicit_overrides": len(ai_preferences) - inferred_count,
        },
    )
    print(
        f"[Requirement Analysis] Extracted {len(ai_preferences)} fields, "
        f"{inferred_count} new inferences applied, "
        f"{len(ai_preferences) - inferred_count} overridden by explicit preferences."
    )

    state.execution_log.append(ExecutionLogEntry(
        agent_name="RequirementAnalysisAgent",
        action=f"Extracted requirements from natural language prompt ({inferred_count} inferences applied)",
        result=f"merged_preferences={list(merged.keys())}",
        created_at_utc=datetime.now(timezone.utc).isoformat(),
    ))

    return state
