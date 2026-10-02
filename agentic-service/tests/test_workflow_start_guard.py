from uuid import uuid4

import pytest
from fastapi import BackgroundTasks

from app.api.routers import workflow_routes


@pytest.fixture(autouse=True)
def clear_running_workflows():
    workflow_routes._running_workflows.clear()
    yield
    workflow_routes._running_workflows.clear()


def _request(workflow_id):
    return workflow_routes.StartWorkflowRequest(
        workflow_id=workflow_id,
        submission_id=uuid4(),
        land_size_category="medium",
        land_size_perches=25,
        bedrooms=2,
        bathrooms=1,
        house_type="modern",
    )


def test_same_workflow_is_scheduled_only_once_while_running():
    workflow_id = uuid4()
    first_tasks = BackgroundTasks()
    second_tasks = BackgroundTasks()

    first = workflow_routes.start_workflow(_request(workflow_id), first_tasks, api_key="test")
    duplicate = workflow_routes.start_workflow(_request(workflow_id), second_tasks, api_key="test")

    assert first["duplicate"] is False
    assert duplicate["duplicate"] is True
    assert len(first_tasks.tasks) == 1
    assert len(second_tasks.tasks) == 0


def test_running_guard_is_released_when_execution_finishes(monkeypatch):
    workflow_id = uuid4()
    request = _request(workflow_id)
    tasks = BackgroundTasks()
    workflow_routes.start_workflow(request, tasks, api_key="test")
    monkeypatch.setattr(workflow_routes.app_graph, "invoke", lambda _state: None)

    workflow_routes.execute_workflow(tasks.tasks[0].args[0])

    assert str(workflow_id) not in workflow_routes._running_workflows
    next_tasks = BackgroundTasks()
    restarted = workflow_routes.start_workflow(request, next_tasks, api_key="test")
    assert restarted["duplicate"] is False
    assert len(next_tasks.tasks) == 1
