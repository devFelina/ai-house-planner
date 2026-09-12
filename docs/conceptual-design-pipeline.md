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
4. `geometry_engine.py` sizes room banks and creates circulation branches, rotates the complete building to fit the plot, aligns stairs across floors, and emits matching door openings and exterior windows. Smaller bounded size variants are searched if the target sizes fail. Long circulation is divided into connected segments.
5. `candidate_generator.py` seeks up to five valid candidates, preferring different eligible families. Each family has three bounded size attempts. Where fewer than three families fit, additional deterministic variants are tried. Constrained plots may return fewer than three valid concepts, with actual counts and rejected reasons disclosed.
6. `geometry_validator.py` is the final authority. Production calls pass the entire design and plot. Legacy room-only calls retain dimension/area/overlap/count checks and gain component/bounds/aspect/floor checks, but cannot certify door accessibility without connection and entrance metadata.
7. `scoring.py` scores only valid candidates and picks the maximum, with stable tie-breaking. The named weights are circulation 25, adjacency 20, privacy 15, efficiency 15, plot utilisation 10, terrain 10, and preferences 5. Exterior exposure is a soft score, not a hard regulatory requirement.
8. The LangGraph design node revalidates before persistence. Failure clears the attempted design, sets `failed`, skips downstream approval, and reports failure through the gateway status endpoint.

Gemini receives the plot, eligible concepts, program/adjacency, preferences, notable features, and revision feedback. Strict JSON may contain only preferred eligible families and a rationale. It cannot submit room geometry, alter hard requirements, or decide validity. Invalid advice/API failure uses the same procedural pipeline. The existing configured Gemini model is retained; no live paid call is needed for tests or an offline demo.

An explicit `design_seed` bypasses remote advice and guarantees reproducible candidate geometry, IDs, and scores for the same request. Without a seed, a stable request-derived seed generates sizes while Gemini can affect eligible family search order. Free-text revision feedback requires AI interpretation; offline results disclose when it was not interpreted. Changing structured preferences works offline.

## Preferences

Existing `architecturalStyle` and `style_preference` keys are accepted as aliases for `style`. Modern/contemporary styles favor open/public-zone families; tropical styles favor garden wings. Style influences selection, while `open_plan` additionally changes target area and creates wide public-room connections. `dining_required`, `master_bedroom`, `attached_bathroom`, `home_office`, `balcony`, `bathrooms`, `garden_priority`, and `accessibility` affect the program, sizing, plot reservation, or score. Unknown preference keys are reported in `candidate_summary.unhandled_preferences`.

An attached bathroom is currently an additional ensuite to the requested common bathroom count. A balcony on a single-floor request is omitted with an explicit note. Parking reserves an 18 ft front strip outside the building; it is a conceptual space reservation, not vehicle swept-path design. Accessibility widens circulation and places a bedroom on the ground floor; upper floors still use stairs and no universal-access compliance is asserted.

Vision remains classification-only. Missing/failed vision returns `unknown`, and a design requires manual terrain classification. Foundation mapping remains flat → slab, hillside → stepped, coastal → raised. Terrain-specific concepts make no structural feasibility claims.

## Responses and rendering

Existing room fields and JSON layout storage remain intact. Optional metadata includes family, seed, score, footprint, connections, entrances, plot constraints, program, and candidate summary. No database migration is needed. Public gateway responses add corresponding optional metadata. Openings are matched by room type, floor, and coordinates so hallways/stairs on different floors remain distinct. Public room IDs use source layout IDs when available so connections and entrances resolve consistently; relational database IDs remain independent across revisions.

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

Python unit tests stub paid APIs and gateway persistence. Tests cover diversity, exact floor/bedroom allocation, plot aspect ratios, preferences, deterministic seeds, malformed geometry and connections, API failure, invalid final advice, and workflow failure routing. Gateway tests cover optional metadata, repeated room-type openings, and public failure status. Viewer tests cover offset geometry and floor separation. Flutter must be installed to execute its tests.
