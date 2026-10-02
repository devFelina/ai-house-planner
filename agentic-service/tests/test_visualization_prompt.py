from app.design.visualization.openai_visualization_service import (
    MAX_PROMPT_CHARS,
    _build_visualization_prompt,
)


def _rooms():
    return [
        {
            "room_id": "bed-1",
            "room_type": "bedroom",
            "name": "Bedroom 1",
            "width": 11.83216,
            "length": 14.932397,
            "x": 37.488602,
            "y": 0,
            "doors": [],
            "windows": [],
        },
        {
            "room_id": "bath-1",
            "room_type": "bathroom",
            "name": "Bathroom",
            "width": 6,
            "length": 8,
            "x": 0,
            "y": 12,
        },
    ]


def _prompt(style="modern", plot="medium", rooms=None):
    return _build_visualization_prompt(
        rooms or _rooms(),
        expected_bedrooms=1,
        expected_bathrooms=1,
        land_size_category=plot,
        house_style=style,
    )


def test_modern_style_and_medium_plot_are_propagated():
    prompt = _prompt()

    assert "House style: Modern Family Home" in prompt
    assert "contemporary finishes" in prompt
    assert "practical modern furniture" in prompt
    assert "Medium plot (20–35 perches)" in prompt


def test_simple_style_and_small_plot_are_propagated():
    prompt = _prompt(style="  SIMPLE ", plot=" SMALL ")

    assert "House style: Simple Family Home" in prompt
    assert "simple practical family-home" in prompt
    assert "modest finishes" in prompt
    assert "Small plot (10–20 perches)" in prompt


def test_unknown_style_and_plot_fall_back_without_failure():
    prompt = _prompt(style="conventional", plot="large")

    assert "House style: Simple Family Home" in prompt
    assert "Plot: Unspecified plot category" in prompt


def test_prompt_contains_single_floor_counts_authority_and_negative_constraints():
    prompt = _prompt()

    assert "blueprint and the provided deterministic layout are the source of truth" in prompt
    assert "Bedrooms: 1" in prompt
    assert "Bathrooms: 1" in prompt
    assert "Floors: exactly 1" in prompt
    assert "Do not add another floor or stairs" in prompt
    assert "Do not add extra rooms" in prompt
    assert "Do not add extra bathrooms" in prompt
    assert "garages, swimming pools, balconies" in prompt
    assert "change the building footprint" in prompt
    assert "realistic orthographic top-down" in prompt


def test_prompt_rounds_geometry_without_serializing_raw_layout():
    prompt = _prompt()

    assert "Bedroom 1 | 11.8ft x 14.9ft | x=37.5 | y=0.0" in prompt
    assert "11.83216" not in prompt
    assert "14.932397" not in prompt
    assert "37.488602" not in prompt
    assert "'room_id'" not in prompt
    assert '"doors"' not in prompt
    assert "[]" not in prompt


def test_critical_rules_survive_when_room_details_exceed_prompt_limit():
    rooms = [
        {
            "room_type": "bedroom",
            "name": f"Bedroom {index} with an intentionally long descriptive label",
            "width": 11.83216,
            "length": 14.932397,
            "x": index * 12.34567,
            "y": index * 7.65432,
        }
        for index in range(200)
    ]
    prompt = _build_visualization_prompt(rooms, 200, 0, "medium", "modern")

    assert len(prompt) <= MAX_PROMPT_CHARS
    assert "MUST PRESERVE" in prompt
    assert "MUST NOT ADD OR CHANGE" in prompt
    assert "VISUAL OUTPUT" in prompt
    assert "Bedroom 199 with an intentionally long descriptive label" not in prompt
