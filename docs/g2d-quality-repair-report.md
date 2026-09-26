# G2D deterministic quality and circulation repair

## Baseline and pre-edit study

HEAD `0dc1d74` (G2C committed). Branch Dev diverged from origin by 4 local / 5 remote commits. Six pre-existing untracked scratch files were preserved; implementation used a clean detached worktree. Python 3.11.15; baseline `python -m pytest tests/`: **211 passed in 27.81s**.

Actual baseline flow: `plan_spatial_program` → provider `generate_json` (one call) → Pydantic `SpatialProgram.model_validate` → `_validate_spatial_program` → `generate_geometry` → `LayoutSolver.generate` → `_build_result` → room-only `validate_geometry(design=None)` → `finish_generative_layout` → return. Full geometry/privacy and architectural quality were external caller responsibilities, not generation gates. `design_validation_service` is the separate workflow coverage/foundation/budget/preferences validator; it does not certify circulation and is unchanged.

The baseline finishing fallback attaches a room to any shared-wall neighbor, including private rooms. A connected door graph therefore does not imply privacy-safe circulation. Architectural quality also expects topology metadata which this path did not supply.

## Failure classification (recorded before implementation)

Classification concerns repair ownership, not a promise every program can be repaired. Exhausted bounded geometry search returns failure; program changes require a future planning/user step.

| Class | Existing failure codes / conditions | Policy |
|---|---|---|
| GEOMETRY_REPAIRABLE | invalid_dimensions, area_mismatch, room_overlap, impossible_dimensions, minimum_dimensions, aspect_ratio, building_bounds, opening_bounds, disconnected_layout, footprint_compactness, unsupported_upper_room, stair_shaft_mismatch, invalid_connection, entrance, entrance_access, accessibility, privacy_access, window_exterior, required_adjacency | Rebuild placement/finishing within original room and plot constraints. Invalid numeric data is rejected, never silently patched. |
| GEOMETRY_REPAIRABLE | excessive_circulation, long_hallway (length/aspect/footprint share/dead end), public_zone_separation, bedroom_spine, remote_bathrooms, bathroom_circulation_access, private_or_corridor_entrance, remote_entrance, dispersed_wet_core, wasted_voids, unnecessary_voids, poor_room_proportions, topology_mismatch, bedroom_public_privacy, minimum_quality_score | Reserve compact circulation, change bounded placement branch, then rerun full gates. Topology must describe actual geometry. |
| GEOMETRY_REPAIRABLE | program_upper_landing_connection, preference_utility_service_zone, program_balcony, program_veranda; finishing ROOM_UNREACHABLE, NO_VALID_ENTRANCE_WALL, missing required exterior window / HIGH adjacency | Reposition existing rooms/core or reserve circulation; never drop requested features. Unsupported combinations fail. |
| PROGRAM_REPAIRABLE | no_rooms, missing_room, bedroom_count, floor_count, floor_utilisation, spatial_program, preference_bedroom_count, preference_bathroom_count, preference_floor_count, preference_home_office/utility/balcony/veranda/dining, program_stair_required, program_stair_forbidden_single_floor, stair_requirement, stair_forbidden | Validate contract. Python owns required multi-floor stairs/circulation only; requested habitable rooms and counts cannot change. |
| NOT_SAFE_TO_AUTO_REPAIR | duplicate_room_id; coverage_ratio / ground_footprint when minima cannot fit; terrain_foundation mismatch; requested attached bathroom/accessibility/parking/open-plan semantics absent from contract | Reject ambiguous IDs, impossible constraints or unsupported preferences. No changes to land, counts, terrain, minimums or user requirements. Geometric coverage excess may be solved only within existing minima. |

Long paths, disconnected circulation, dead ends, poor zoning, inaccessible stairs, excessive voids, poor compactness, bad entrances, separated wet cores and adjacency failures are covered by the codes above. `quality_metrics` also reports dead_end_hallways, single_use_hallways, exterior_wall_ratio and longest_access_chain; these are diagnostics, not independent hard gates. Workflow budget/terrain/coverage/preferences checks remain separate and are not bypassed by G2D.

## Original 4B3B reproduction

Equivalent fixture from the pre-existing scratch reproduction: 4 bedrooms, 3 bathrooms, 2 floors, 80 × 80 ft plot, default setbacks; no hallway supplied. Placement + finishing took 213 ms in this run. Full geometry fails privacy for two bedrooms and two bathrooms. Quality: 59 / ARCHITECTURALLY_POOR; bathroom_circulation_access, bedroom_public_privacy, poor_room_proportions, topology_mismatch, unnecessary_voids.

Original SpatialProgram, coordinates, openings, connections, graph and validation results are retained in `agentic-service/tests/fixtures/g2d_4b3b_baseline.json`. Circulation graph is the door graph restricted to living/dining/stairs: the upper staircase has no landing/hallway and private bridges serve the remaining rooms.


## Final policy and implementation

Bedrooms, bathrooms and offices cannot be mandatory bridges to unrelated rooms. An attached bathroom may retain the validator's existing explicit `bedroom_1` / `bathroom_attached` convention. Every upper room must be independently reachable from a landing/public node directly connected to its floor's staircase, with unrelated private rooms and the stair itself removed from the onward traversal. Private-to-private HIGH adjacency doors may exist only when both rooms also have circulation access; no private room is required for passage. Optional stair-to-room doors do not replace the required landing route.

Python owns circulation feasibility. GPT can request a hallway/foyer, but Python may reserve one when actual access/privacy validation fails, an upper landing is missing, or circulation/zoning quality rejects the direct arrangement. A count of bedrooms alone does not force insertion. Existing foyer/hallway intent is reused. A successful direct-access candidate gets an alternative placement branch for quality comparison, without automatic hallway insertion.

A generated hallway is attributed in metadata with `owner=PYTHON`, `generated_reason=CIRCULATION_REQUIRED`, room ID, floor and role (`hallway` / `landing_hallway`). The original SpatialProgram is copied, never rewritten as if GPT requested the addition. Existing RoomRules supply 3.5 ft hallway width and 6 × 10 ft stair minimums. The bounded reservation uses 20/22/23 ft room-bank widths, shortens multi-floor hallway frontage to actual door-connection needs, and checks existing quality limits. The same short upper hallway supplies the landing; no new room schema is introduced. These are conceptual planning rules, not building-code certification.

Geometry search first tries the existing placement solver. Repairs partition rooms into rectangles around a reserved circulation strip before final placement/finishing. Ground rooms are re-solved against the shared core to support the complete upper footprint. Deterministic alternatives vary bank width, room grouping/order, partition direction and target-area rank; small target adjustments respect requested minimum areas, RoomRules, and a 125% target-area upper bound in the reservation solver. The footprint rotates before finishing to the plot's effective entrance side. No finished coordinate patches occur.

Bounds: at most **4 complete finished candidates**, 350,000 placement evaluations per original solver, 500 original backtracks, 128 room partitions per floor/width, 10 non-core rooms per floor for reservation, 2,500 recursive states per bank solve, **180,000 recursive states across the entire reservation search**, 20 retained floor options, and three reservation widths. Area ranks remain represented so tight candidates do not crowd out solutions meeting the circulation-area limit. Search is deterministic and uses no random seeds.

Every complete candidate is finished, fully geometry-validated (`design=...`, including doors/privacy/stairs/windows), checked for requested room identity/count/minimum area, separately checked for private passage and upper landing reachability, and then quality-scored only if geometry passes. HIGH adjacency means an actual retained door, not merely a possible shared wall. Required exterior windows are gated. Existing topology families describe the generated footprint, with the existing topology validator confirming that description; no catalogue plan is substituted and no quality threshold is relaxed.

Selection reuses `GEOMETRICALLY_INVALID`, `ARCHITECTURALLY_POOR`, and `VALID_HIGH_QUALITY`. Highest quality score among passing candidates wins; ties use the lower candidate index. If none passes, `GenerationFailure.failures` contains the evaluation log, rejection reasons, repairs and counters. A poor candidate is never returned as success or persisted.

Metadata includes all requested G2D fields, prior selected-candidate fields, original placement metadata, per-candidate geometry/circulation/quality failures, search limits, generated-space provenance and recursive-state counts. `repair_attempts` counts completed alternative placements that reach candidate evaluation; raw partial partition nodes are reported separately. Rejection counters can overlap (a geometric/privacy rejection can also be counted as circulation rejection). `total_geometry_ms` measures placement/search; `total_finishing_ms` finishing; `total_quality_ms` includes full geometry certification, circulation checks and architectural scoring. `generation_ms` measures total deterministic processing.

Geometry fingerprints reuse the existing hash of geometry, connections and entrances. A minimal `topology_fingerprint` adds a coordinate-independent hash of room IDs/types/floors, connections and entrance-room IDs for the same SpatialProgram. This supports future G4 exclusion without implementing Generate Another or graph-isomorphism/diversity infrastructure. IDs remain significant in the topology hash; it is not a cross-program canonical graph hash.

Additional precise classification names: `preference_master_ensuite`, `preference_open_plan`, `preference_accessibility`, and `preference_parking` are NOT_SAFE_TO_AUTO_REPAIR when the necessary user semantics are unavailable. The dynamic quality feature codes are `preference_home_office`, `preference_utility`, `preference_balcony`, `preference_veranda`, `preference_dining`. `no_rooms` also exists in architectural quality. New G2D contract/repair failures (`minimum_area`, invalid IDs/references/minimum-target relationships, missing reservation, HIGH_ADJACENCY_UNSATISFIED, NO_EXTERIOR_WINDOW, PRIVATE_PASS_THROUGH, STAIR_ACCESS_POOR, UPPER_CIRCULATION_DISCONNECTED) fail closed within the same ownership policy.

## Measured results

Three serial local runs per fixture, after rendering/font-cache initialization and without concurrent pytest load. Milliseconds include deterministic generation/finishing/validation, excluding GPT and rendering.

| Fixture | Min ms | Typical (median) ms | Worst ms | Complete candidates | Repair attempts | Selected index | Quality |
|---|---:|---:|---:|---:|---:|---:|---|
| single | 851.0 | 856.8 | 862.8 | 2 | 1 | 1 | 97.05 / VALID_HIGH_QUALITY |
| 4b3b | 2532.7 | 2542.9 | 2543.4 | 3 | 2 | 2 | 87.02 / VALID_HIGH_QUALITY |
| no_hall | 111.4 | 111.5 | 111.8 | 4 | 3 | 1 | 97.90 / VALID_HIGH_QUALITY |
| live_gpt | 1690.8 | 1693.8 | 1697.9 | 4 | 3 | 1 | 93.57 / VALID_HIGH_QUALITY |
| rejected_3b2b | 2608.9 | 2612.9 | 3061.6 | 1 | 0 | None | Structured search-limit failure |

The larger regression exceeds the previous sub-second geometry scale: approximately 2.5 seconds versus the original 213 ms reproduction. The candidate count and partial searches are bounded. This is an explicit latency tradeoff, not a claim that G2D remains sub-second. A concurrent renderer/test run observed 3.704 seconds on 4B3B; final serial 4B3B worst was 2.543 seconds. A larger rejected 3B2B fixture initially took 22.052 seconds during development; the new deterministic total-node budget reduces it to 2.609–3.062 seconds. Its structured failure records RESERVATION_NODE_LIMIT_EXCEEDED. The node budget is tested directly. Broader performance still needs review before production.

The one real request used the unchanged prompt and provider: **961 input + 775 output = 1,736 tokens**, `gpt-4o`, HTTP 200, finish reason `stop`, provider latency **10,046 ms** (wall measurement 10,047.07 ms). Automatic approval initially blocked the network action; the user explicitly approved it and exactly one request was then sent. Its saved program exposed HIGH adjacency failures during development. All subsequent iterations replayed that same program locally, making zero further GPT calls. Final saved-response replay passes at **93.57**, with all three HIGH ADJACENT doors satisfied, four complete candidates and three repair attempts. Original prompt and provider architecture are unchanged. No candidate coordinates are sent to GPT.

Final live-program replay stage timing: geometry/search **1673.556 ms**, finishing **5.335 ms**, validation/quality **11.296 ms**, total **1690.502 ms**.

## Renderer inspection

Used the existing `rendering_service.rendering_node` locally without running/integrating the workflow. Images and finished JSON/door graphs are in `/private/tmp/g2d-artifacts/`, outside Git.

- `single.png`: two bedrooms independently open onto the transverse hallway; living and bathroom connect to it. Kitchen connects through the public room. Brown doors and blue exterior windows are visible; no stairs.
- `4b3b.png`: stairs align across floors and directly meet each hallway. The upper three bedrooms and two bathrooms each have hallway access. Ground bedroom retains independent access, and the entrance opens into living. Window openings lie on exterior segments. Short exterior recesses remain beside the hall; validation includes upper structural support.
- `live_gpt.png`: both stair/landing connections are visible. The requested bedroom/bathroom adjacency doors are present along with independent hallway access, so they do not create mandatory private bridges. Kitchen/dining adjacency is visible.
- Staircases are rendered as labeled rectangles; the existing renderer has no stair-tread detail. This smoke check confirms modeled spaces and openings, not construction documentation.

## Final requested checklist

1. **Baseline tests:** 211 passed in 27.81s, Python 3.11.15; initial six untracked scratch files preserved via isolated clean worktree.
2. **Call flow:** planner (one GPT call) → schema/request validation → G2D program revalidation → bounded placement/reservation → finishing → full geometry certification → circulation/privacy gate → architectural quality → best passing result or structured failure.
3. **4B3B reproduction:** exact private-passage message reproduced for two bedrooms and two bathrooms; original score 59; complete baseline program, coordinates and graphs retained in fixture.
4. **Failure map:** pre-edit classification table above covers geometry, quality, preferences and finishing failure families.
5. **Circulation policy:** no mandatory unrelated private bridges; private spaces terminate access branches; optional adjacency doors require independent circulation access.
6. **Hallway insertion:** observed access/landing/circulation failures trigger reservation; neither bedroom count nor GPT omission alone forces a hallway.
7. **Landing policy:** reuse the short upper hallway/public landing directly connected to aligned stairs; independently traverse onward with stairs/private bridges blocked.
8. **Ownership:** Python-created circulation has explicit provenance; original GPT SpatialProgram remains unchanged.
9. **Search changes:** reserved strips, bounded rectangular room partitioning, supported upper footprint, alternative placement/area/width branches, stable finishing and full quality ranking.
10. **Complete candidates:** single=2, 4B3B=3, foyer=4, saved GPT=4; hard limit=4.
11. **Candidate evaluation:** finishing → full geometry → privacy/landing → quality; geometry-invalid candidates receive no architectural score/ranking.
12. **Selection:** best VALID_HIGH_QUALITY score, stable index tie-break; no passing candidate means GenerationFailure.
13. **Supported repairs:** reserve/reuse hallway and landing, choose another room partition/dimension/core placement, rebuild door choices on actual shared walls. No room/count/floor removal or minimum violations.
14. **Repair metadata:** original_failure, repair_strategy, repair_attempt, result; rejection counts, timings, search limits, candidate fingerprints, selected index, provenance and prior metadata retained.
15. **Extra GPT calls:** zero in G2D; one SpatialPlanner request total in the live smoke test.
16. **Token regression:** unchanged prompt/schema/provider; measured 1,736 total tokens, within the expected order of magnitude.
17. **Single-floor passage:** explicit living → bed1 → bed2 naive graph fails privacy; repaired layout passes every gate at 97.05.
18. **4B3B regression:** original fixture passes full geometry and quality at 87.02, preserving four bedrooms/three bathrooms/two floors.
19. **No unnecessary hallway:** requested foyer reused; no new hallway or additional circulation room; score 97.90.
20. **Stair/landing test:** upper rooms remain reachable from the hallway with the stair and unrelated private rooms blocked.
21. **Quality selection:** actual geometry-valid poor candidate is rejected in the 4B3B run; score/status selection tests also exclude high-scoring poor/invalid candidates.
22. **No-good-candidate result:** conflicting HIGH living/bedroom access yields structured failure; oversized requested office is never removed to force success.
23. **Visual findings:** existing renderer smoke inspected for single-floor, repaired 4B3B and saved GPT; hallway/stair/door/window findings above.
24. **Real GPT end-to-end:** one successful API response; final deterministic replay of that same response passes all gates. No repeated GPT calls during repair development.
25. **Real token count:** input 961, output 775, total 1,736; GPT latency 10.046 s.
26. **Real candidate count:** 4 complete candidates.
27. **Real repair attempts:** 3 completed deterministic alternatives.
28. **Processing time:** final serial fixture range 111.4–3,061.6 ms, including bounded failure; per-fixture min/median/max and live stage breakdown above. Concurrent worst observed 3,704 ms.
29. **Final quality:** real saved program 93.57 / VALID_HIGH_QUALITY; original regression 87.02 / VALID_HIGH_QUALITY.
30. **Full pytest:** final requested offline command in the original working directory: **230 passed in 37.99s** (baseline 211). Earlier worktree run: 229 passed in 46.72s, before adding the total-node-budget test.
31. **Compile/imports:** `python -m compileall app` passed; spatial_planner, geometry_generator, finishing, geometry_validator and architectural_quality imports passed.
32. **Diff scope:** geometry generator, finishing, new circulation/quality-search helpers, focused tests/fixtures and this report. No LangGraph, ASP.NET, React, cost, RAG, catalogue data or provider edits. No images or automatic commits.
33. **Before G3:** preserve the fail-closed contract at the workflow boundary; explicitly thread remaining requirement semantics (open-plan/accessibility/parking/ensuite) into full request-level validation; validate a wider program/plot distribution and acceptable latency. Current reservation supports one/two floors and at most ten non-core rooms per floor. The existing single-floor 3B2B raw-placement fixture now correctly returns a structured failure at the full quality boundary because this bounded search finds no passing candidate. It remains a concrete coverage limitation to resolve before claiming general production readiness. Other otherwise feasible programs can also exhaust the bounded search; failure is not proof of geometric impossibility. G3 integration is not implemented.

Existing G2A/G2B structural and raw placement tests now call `LayoutSolver` where they test placement counts, repeatability, stair alignment or support. This does not exempt `generate_geometry` from G2D gates. Dedicated new tests exercise the full public path, including failures; old geometrically successful layouts are no longer assumed to be architecturally acceptable.


Final review: 10 task files (four modified tracked files and six additions: two helpers, one test module, two JSON fixtures and this report). `git diff --check` passed. The original six untracked scratch scripts remain untouched. No staged changes, commit, merge, remote push, workflow integration or generated image was added to Git. The clean detached development worktree remains at `/private/tmp/ai-house-g2d`; task changes have been copied into the original working directory.
