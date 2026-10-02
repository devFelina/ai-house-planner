import pytest

from app.orchestration.tool_governance import (
    AGENT_TOOL_ALLOWLIST,
    KNOWN_TOOLS,
    ToolAuthorizationError,
    assert_tool_allowed,
    is_tool_allowed,
)


ALLOWED_PAIRS = (
    ("requirement_analysis", "requirement_extractor"),
    ("land_analysis", "terrain_classifier"),
    ("design", "geometry_generator"),
    ("visualization", "visualization_generator"),
    ("construction_planning", "construction_scheduler"),
    ("cost_estimation", "pricing_lookup"),
)

EXPECTED_AGENTS = {
    "requirement_analysis",
    "land_analysis",
    "design",
    "visualization",
    "construction_planning",
    "cost_estimation",
    "validation",
}

EXPECTED_TOOLS = {
    "requirement_extractor",
    "terrain_classifier",
    "geometry_generator",
    "visualization_generator",
    "construction_scheduler",
    "pricing_lookup",
}


@pytest.mark.parametrize(("agent_name", "tool_name"), ALLOWED_PAIRS)
def test_allowed_pairs_pass(agent_name, tool_name):
    assert assert_tool_allowed(agent_name, tool_name) is None
    assert is_tool_allowed(agent_name, tool_name) is True


def test_validation_has_no_tools():
    assert AGENT_TOOL_ALLOWLIST["validation"] == frozenset()


@pytest.mark.parametrize(
    ("agent_name", "tool_name"),
    (
        ("design", "pricing_lookup"),
        ("cost_estimation", "geometry_generator"),
        ("visualization", "terrain_classifier"),
        ("requirement_analysis", "visualization_generator"),
    ),
)
def test_cross_agent_access_is_denied(agent_name, tool_name):
    with pytest.raises(ToolAuthorizationError, match="is not allowed"):
        assert_tool_allowed(agent_name, tool_name)
    assert is_tool_allowed(agent_name, tool_name) is False


def test_unknown_agent_is_denied():
    with pytest.raises(ToolAuthorizationError, match="Unknown agent 'fake_agent'"):
        assert_tool_allowed("fake_agent", "pricing_lookup")
    assert is_tool_allowed("fake_agent", "pricing_lookup") is False


def test_unknown_tool_is_denied():
    with pytest.raises(ToolAuthorizationError, match="Unknown tool 'shell_command'"):
        assert_tool_allowed("design", "shell_command")
    assert is_tool_allowed("design", "shell_command") is False


def test_registry_contains_exactly_the_workflow_agents():
    assert set(AGENT_TOOL_ALLOWLIST) == EXPECTED_AGENTS


def test_known_tools_contains_exactly_the_governed_inventory():
    assert KNOWN_TOOLS == frozenset(EXPECTED_TOOLS)


def test_policy_collections_are_immutable_sets():
    assert isinstance(KNOWN_TOOLS, frozenset)
    assert all(isinstance(tools, frozenset) for tools in AGENT_TOOL_ALLOWLIST.values())


@pytest.mark.parametrize(
    "infrastructure_name",
    (
        "persist_workflow_plan_state",
        "persist_design",
        "persist_cost",
        "execution_log",
        "requests",
        "httpx",
        "blueprint_renderer",
    ),
)
def test_infrastructure_is_not_a_known_tool(infrastructure_name):
    assert infrastructure_name not in KNOWN_TOOLS
