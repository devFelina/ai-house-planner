# Conceptual design pipeline

This university planner generates conceptual layouts for review. It does not provide construction drawings, structural calculations, or Sri Lankan building-code approval. Existing cost-estimation and approval components remain separate.

## Request compatibility

`POST /workflows/start` keeps `submission_id`, optional `budget_lkr`, `land_size_perches`, `manual_terrain_type`, and `preferences`. Two optional fields are added: `plot_constraints` and `design_seed`. Plot fields and the seed can also be supplied inside `preferences` by older clients.

```json
{
  "submission_id": "00000000-0000-0000-0000-000000000123",
  "land_size_perches": 15,
  "manual_terrain_type": "flat",
  "design_seed": 123,
  "plot_constraints": {
    "plot_width_ft": 45,
    "plot_length_ft": 90,
    "road_side": "south",
    "north_direction": "top",
    "slope_direction": null,
    "setbacks": {"front": 10, "rear": 7, "left": 5, "right": 5}
  },
  "preferences": {
    "bedrooms": 3,
    "bathrooms": 2,
    "floors": 1,
    "style": "Tropical Modernism",
    "open_plan": true,
    "garden_priority": true
  }
}
```

The room count bounds are 1–8 bedrooms, 1–6 bathrooms, and 1–3 floors. Unsupported or infeasible combinations return a failed workflow; search failure does not prove that a professional could not design a house on that plot.

A missing pair of dimensions is estimated at a 1:1.3 width-to-length ratio. One supplied dimension determines the other from land area. `dimensions_estimated` identifies these cases. The buildable rectangle uses road-relative setbacks, with its own southwest origin. Room coordinates are architectural feet, east along +X and north along +Y. `north_direction` retains source-plan orientation metadata; generated coordinates use the canonical compass convention. Road side controls rotation and entrance access. Slope direction influences hillside orientation. Setbacks are conceptual assignment defaults.

The existing 65% **total floor area** assignment limit remains unchanged. `maximum_ground_footprint` is separately capped by both that limit and the setback rectangle. `ground_footprint_sqft` sums ground-floor room/circulation areas; `total_built_up_area_sqft` sums all floors. This is not an official coverage/FAR calculation.

## Architecture and decisions

1. `design/models.py`, `room_rules.py`, and `plot_constraints.py` normalize requirements and conceptual limits.
2. `spatial_program.py` allocates public/private/service spaces to specific floors, creates required/preferred adjacency relationships and an abstract circulation graph.
3. `topology_registry.py` supplies suitability and zoning rules without final coordinates. Nine implemented families are LINEAR, COMPACT_RECTANGLE, L_SHAPE, T_SHAPE, CENTRAL_CORE, SPLIT_ZONE, DUPLEX_STACKED, HILLSIDE_STEPPED, and COASTAL_RAISED_COMPACT. L/T wings provide garden relationships; a fully enclosed courtyard topology is not implemented.
4. In production, Gemini creates each complete room arrangement, including zoning, floor allocation, dimensions, coordinates, doors, windows, connections, and entrances. It receives eligible high-level concept families as design guidance, but no finished coordinate template.
5. Three independent AI candidates are requested. Each candidate gets at most three attempts; exact schema or deterministic validation failures are returned to Gemini for revision. Valid candidates are fingerprinted, scored, deduplicated, and the highest-scoring geometry is selected. If Gemini is configured but fails to produce a valid candidate, the workflow fails safely.
6. `geometry_validator.py` is the final authority. Production calls pass the entire design and plot. It checks geometry, connected access, physically adjacent door pairs, exterior-only windows, entrances, stairs, room proportions, and terrain/foundation compatibility. Legacy room-only calls cannot certify openings or accessibility without full design metadata.
7. `quality_metrics.py` calculates usable area, circulation area and ratio, per-floor bounding boxes, compactness, estimated internal void, hallway length/use, access-chain length, wet-zone spacing, bathroom-to-bedroom-cluster distance, exterior-wall opportunity, and extreme proportions. `scoring.py` ranks valid candidates with configurable weights: circulation 20, adjacency 15, privacy 15, room proportions 15, plot utilisation 10, exterior walls 10, terrain 10, and preferences 5. Wet-zone efficiency is included in adjacency quality and is also reported separately.
8. The LangGraph design node revalidates before persistence. Failure clears the attempted design, sets `failed`, skips downstream approval, and reports failure through the gateway status endpoint.

Gemini receives the plot, eligible concepts, program/adjacency, preferences, notable features, the prior design during revisions, and homeowner feedback. Its strict JSON is the complete proposed `DesignResult`. Python overwrites deterministic terrain, foundation, floor-count, area, plot, and program metadata, then independently validates and scores the result. Gemini never decides whether its own geometry is valid.

For ordinary-width plots, an AI candidate above 15% circulation or with a hallway longer than 32 ft is returned for bounded revision with exact measurements. Narrow plots may retain higher circulation when necessary; the result records the exception and still receives the full score penalty. These are configurable conceptual quality thresholds, not statutory requirements.

When `GOOGLE_API_KEY` is absent, `geometry_engine.py` and `candidate_generator.py` provide a deterministic procedural demo fallback. Responses identify this with `generation_mode: procedural_demo_fallback` and state that Gemini did not create the geometry. A seed makes fallback output reproducible. The production path continues to call Gemini even when a seed is supplied; the seed is context for diversity and traceability, not a switch that bypasses AI.

## Preferences

Existing `architecturalStyle` and `style_preference` keys are accepted as aliases for `style`. Modern/contemporary styles favor open/public-zone families; tropical styles favor garden wings. Style influences selection, while `open_plan` additionally changes target area and creates wide public-room connections. `dining_required`, `master_bedroom`, `attached_bathroom`, `home_office`, `balcony`, `bathrooms`, `garden_priority`, and `accessibility` affect the program, sizing, plot reservation, or score. Unknown preference keys are reported in `candidate_summary.unhandled_preferences`.

The public intake also accepts optional orientation, entrance side, setbacks, veranda, utility/laundry, parking, space priority, and the default `space_efficient` circulation preference. Legacy aliases such as `master_ensuite`, `separate_dining`, and `parking_required` are normalized in Python. Missing fields retain the previous defaults.

An attached bathroom is currently an additional ensuite to the requested common bathroom count. A balcony on a single-floor request is omitted with an explicit note. Parking reserves an 18 ft front strip outside the building; it is a conceptual space reservation, not vehicle swept-path design. Accessibility widens circulation and places a bedroom on the ground floor; upper floors still use stairs and no universal-access compliance is asserted.

Vision remains classification-only. Missing/failed vision returns `unknown`, and a design requires manual terrain classification. Foundation mapping remains flat → slab, hillside → stepped, coastal → raised. Terrain-specific concepts make no structural feasibility claims.

## Responses and rendering

Existing room fields and JSON layout storage remain intact. Optional metadata includes family, seed, score, geometry fingerprint, footprint, connections, entrances, plot constraints, program, and candidate summary. A database migration adds a unique `(WorkflowStateId, Version)` index. Public gateway responses add corresponding optional metadata. Openings are matched by room type, floor, and coordinates so hallways/stairs on different floors remain distinct. Public room IDs use source layout IDs when available so connections and entrances resolve consistently; relational database IDs remain independent across revisions.

React and Flutter fit the displayed floor using room bounds. They support irregular rectangular compositions, circulation colors, entry markers, stair treads, and optional openings. Default rendering selects the first floor rather than overlaying all floors. Both existing review screens retain floor selection. The React intake now accepts optional measured plot dimensions and road side.

## Verification

```sh
cd agentic-service
GOOGLE_API_KEY='' venv/bin/python -m pytest -q
```

```sh
cd HousePlanner-Web
npm test
npm run build
```

```sh
dotnet test HousePlanner.API.Tests/HousePlanner.API.Tests.csproj --no-restore
cd mobile
flutter test test/floor_plan_painter_test.dart
```

Python unit tests stub paid APIs and gateway persistence. Tests cover diversity, exact floor/bedroom allocation, plot aspect ratios, preferences, deterministic fallback seeds, malformed geometry and connections, bounded AI failure, and workflow failure routing. Gateway tests cover optional metadata, repeated room-type openings, immutable revisions, unknown callback rejection, and public failure status. Viewer tests cover offset geometry and floor separation. Flutter must be installed to execute its tests.
