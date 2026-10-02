from uuid import uuid4

from app.orchestration.tool_audit import (
    MAX_ERROR_SUMMARY_LENGTH,
    MAX_STRING_LENGTH,
    log_tool_failure,
    log_tool_success,
    sanitize_summary,
    sanitize_tool_error,
    start_tool_timer,
)
from app.schemas.workflow_state import ExecutionLogEntry, WorkflowState


def _state() -> WorkflowState:
    return WorkflowState(workflow_id=uuid4())


def test_success_event_contains_expected_fields():
    state = _state()
    log_tool_success(
        state=state,
        agent_name="design",
        tool_name="geometry_generator",
        started_at=start_tool_timer(),
        input_summary={"bedrooms": 3},
        output_summary={"room_count": 8},
    )

    assert len(state.execution_log) == 1
    event = state.execution_log[0]
    assert event.action == "tool_call_succeeded"
    assert event.event_status == "succeeded"
    assert event.result == "success"
    assert event.tool_called == "geometry_generator"
    assert event.agent_name == "design"
    assert event.duration_ms >= 0
    assert event.input_summary == {"bedrooms": 3}
    assert event.output_summary == {"room_count": 8}
    assert event.error_type is None
    assert event.error_summary is None


def test_failure_event_contains_only_sanitized_error_information():
    state = _state()
    log_tool_failure(
        state=state,
        agent_name="cost_estimation",
        tool_name="pricing_lookup",
        started_at=start_tool_timer(),
        input_summary={"region": "Colombo"},
        error=ValueError("raw-value-that-must-not-be-logged"),
    )

    event = state.execution_log[0]
    assert event.action == "tool_call_failed"
    assert event.event_status == "failed"
    assert event.result == "failed"
    assert event.error_type == "ValueError"
    assert event.error_summary == "Tool input or output validation failed."
    assert "raw-value-that-must-not-be-logged" not in event.model_dump_json()


def test_unknown_exception_uses_generic_message_without_raw_secret():
    error_type, summary = sanitize_tool_error(RuntimeError("secret-data-123"))

    assert error_type == "RuntimeError"
    assert summary == "Tool execution failed."
    assert "secret-data-123" not in summary
    assert len(summary) <= MAX_ERROR_SUMMARY_LENGTH


def test_sensitive_dictionary_keys_are_redacted_recursively():
    summary = sanitize_summary({
        "region": "Colombo",
        "api_key": "super-secret",
        "Authorization": "Bearer xyz",
        "nested": {"connection_string": "postgresql://secret", "safe": True},
    })

    assert summary == {
        "region": "Colombo",
        "api_key": "[REDACTED]",
        "Authorization": "[REDACTED]",
        "nested": {"connection_string": "[REDACTED]", "safe": True},
    }
    serialized = str(summary)
    assert "super-secret" not in serialized
    assert "Bearer xyz" not in serialized
    assert "postgresql://secret" not in serialized


def test_raw_binary_is_replaced_not_stored():
    raw = b"raw-image-bytes"
    summary = sanitize_summary({"image": raw, "nested": [bytearray(raw)]})

    assert summary == {
        "image": "[REDACTED_BINARY]",
        "nested": ["[REDACTED_BINARY]"],
    }
    assert raw not in summary.values()


def test_long_strings_are_bounded_and_raw_urls_are_not_preserved():
    summary = sanitize_summary({
        "description": "x" * 10_000,
        "provider_url": "https://example.test/image.png?signature=secret",
    })

    assert len(summary["description"]) == MAX_STRING_LENGTH
    assert summary["provider_url"] == "[REDACTED_URL]"


def test_structured_safe_dictionary_is_preserved():
    summary = {
        "enabled": True,
        "count": 4,
        "ratio": 1.25,
        "optional": None,
        "labels": ["flat", "standard"],
        "nested": {"status": "succeeded"},
    }

    assert sanitize_summary(summary) == summary


def test_unsupported_object_is_replaced():
    assert sanitize_summary({"handle": object()}) == {"handle": "[UNSUPPORTED]"}


def test_old_execution_log_entry_remains_valid():
    entry = ExecutionLogEntry(
        agent_name="DesignAgent",
        action="legacy action",
        result="success",
        created_at_utc="2026-10-02T00:00:00+00:00",
    )

    assert entry.tool_called is None
    assert entry.duration_ms is None
    assert entry.event_status is None
    assert entry.input_summary is None
    assert entry.output_summary is None
    assert entry.error_type is None
    assert entry.error_summary is None
