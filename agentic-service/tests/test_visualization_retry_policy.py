from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from app.design.visualization import openai_visualization_service as module


def _layout():
    return {"rooms": [{"room_type": "bedroom", "name": "Bedroom", "width": 10, "length": 10, "x": 0, "y": 0}]}


def _status_error(error_type, status: int, message: str, code: str):
    response = httpx.Response(
        status,
        request=httpx.Request("POST", "https://api.openai.test/v1/images/edits"),
    )
    return error_type(message, response=response, body={"error": {"code": code}})


@pytest.fixture
def service(monkeypatch):
    fake_openai = Mock()
    monkeypatch.setattr(module, "openai", fake_openai)
    monkeypatch.setattr(module, "ENABLE_OPENAI", True)
    monkeypatch.setattr("app.services.ai_guard_db.check_daily_limit", lambda: None)
    monkeypatch.setattr("app.services.ai_guard_db.log_ai_cost", lambda *_args: None)
    monkeypatch.setattr("app.design.visualization.layout_renderer.render_blueprint", lambda _layout: b"png")
    return module.OpenAIVisualizationService(api_key="test-key", workflow_id="workflow-test"), fake_openai


def test_successful_edit_uses_one_image_api_call(service):
    visualization, fake_openai = service
    fake_openai.images.edit.return_value = SimpleNamespace(
        data=[SimpleNamespace(url="https://example.test/image.png", b64_json=None)]
    )

    result = visualization.generate_visualization(_layout())

    assert result["status"] == "validated"
    fake_openai.images.edit.assert_called_once()
    fake_openai.images.generate.assert_not_called()


def test_edit_incompatibility_allows_one_generate_fallback(service):
    visualization, fake_openai = service
    fake_openai.images.edit.side_effect = _status_error(
        module.BadRequestError, 400, "Image edit is unsupported for this input", "unsupported_operation"
    )
    fake_openai.images.generate.return_value = SimpleNamespace(
        data=[SimpleNamespace(url="https://example.test/image.png", b64_json=None)]
    )

    result = visualization.generate_visualization(_layout())

    assert result["status"] == "validated"
    fake_openai.images.edit.assert_called_once()
    fake_openai.images.generate.assert_called_once()


def test_rate_limit_does_not_fallback_to_generate(service):
    visualization, fake_openai = service
    fake_openai.images.edit.side_effect = _status_error(
        module.RateLimitError, 429, "Organization spend limit exceeded", "insufficient_quota"
    )

    result = visualization.generate_visualization(_layout())

    assert result["status"] == "failed"
    fake_openai.images.edit.assert_called_once()
    fake_openai.images.generate.assert_not_called()


def test_unrelated_bad_request_does_not_fallback_to_generate(service):
    visualization, fake_openai = service
    fake_openai.images.edit.side_effect = _status_error(
        module.BadRequestError, 400, "Invalid request parameter", "invalid_request_error"
    )

    result = visualization.generate_visualization(_layout())

    assert result["status"] == "failed"
    fake_openai.images.edit.assert_called_once()
    fake_openai.images.generate.assert_not_called()


@pytest.mark.parametrize("error_type,status", [
    (module.AuthenticationError, 401),
    (module.PermissionDeniedError, 403),
])
def test_auth_and_permission_errors_do_not_fallback(service, error_type, status):
    visualization, fake_openai = service
    fake_openai.images.edit.side_effect = _status_error(
        error_type, status, "Access denied", "access_denied"
    )

    result = visualization.generate_visualization(_layout())

    assert result["status"] == "failed"
    fake_openai.images.edit.assert_called_once()
    fake_openai.images.generate.assert_not_called()
