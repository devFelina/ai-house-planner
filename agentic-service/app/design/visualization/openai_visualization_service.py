import json
import uuid
import logging
from datetime import datetime
try:
    import openai
    from openai import AuthenticationError, BadRequestError, PermissionDeniedError, RateLimitError
except ImportError:
    openai = None
    AuthenticationError = PermissionDeniedError = RateLimitError = BadRequestError = Exception

from app.config import ENABLE_OPENAI

logger = logging.getLogger(__name__)

MAX_PROMPT_CHARS = 4000


def _style_guidance(house_style: str | None) -> tuple[str, str]:
    """Return a safe display label and visual-only guidance for a supported style."""
    normalized = str(house_style or "").strip().lower()
    if normalized == "modern":
        return (
            "Modern Family Home",
            "Apply a modern family-home visual style using contemporary finishes, "
            "clean materials, practical modern furniture, an open and airy visual "
            "character, modern kitchen styling, and natural lighting. These visual "
            "enhancements must not alter the architecture.",
        )
    return (
        "Simple Family Home",
        "Apply a simple practical family-home visual style using modest finishes, "
        "comfortable everyday furnishings, and a functional cozy appearance. These "
        "visual enhancements must not alter the architecture.",
    )


def _plot_label(land_size_category: str | None) -> str:
    normalized = str(land_size_category or "").strip().lower()
    return {
        "small": "Small plot (10–20 perches)",
        "medium": "Medium plot (20–35 perches)",
    }.get(normalized, "Unspecified plot category")


def _prompt_number(value) -> str:
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "0.0"


def _build_visualization_prompt(
    rooms: list[dict],
    expected_bedrooms: int | None,
    expected_bathrooms: int | None,
    land_size_category: str | None,
    house_style: str | None,
) -> str:
    """Build a bounded prompt while retaining every architectural constraint."""
    room_summary = {}
    room_details = []
    for room in rooms:
        room_type = str(room.get("room_type", "Room")).replace("_", " ").title()
        room_summary[room_type] = room_summary.get(room_type, 0) + 1
        name = str(room.get("name") or room_type)
        room_details.append(
            f"{name} | {_prompt_number(room.get('width'))}ft x "
            f"{_prompt_number(room.get('length'))}ft | "
            f"x={_prompt_number(room.get('x'))} | y={_prompt_number(room.get('y'))}"
        )

    actual_bedrooms = sum(
        1 for room in rooms if "bedroom" in str(room.get("room_type", "")).lower()
    )
    actual_bathrooms = sum(
        1 for room in rooms if "bath" in str(room.get("room_type", "")).lower()
    )
    bedroom_count = expected_bedrooms if expected_bedrooms is not None else actual_bedrooms
    bathroom_count = expected_bathrooms if expected_bathrooms is not None else actual_bathrooms
    style_label, style_text = _style_guidance(house_style)
    summary_text = "\n".join(f"{name} x{count}" for name, count in room_summary.items())

    one_bathroom_rules = ""
    if bathroom_count == 1:
        one_bathroom_rules = (
            "\n- Exactly one bathroom."
            "\n- No ensuite."
            "\n- No guest toilet."
            "\n- No additional washroom."
        )

    # Keep invariant constraints before the variable room list. Only room-detail
    # lines are shortened when the provider prompt limit is reached.
    prefix = (
        "ROLE\n"
        "You are an architectural visualization renderer, not an architectural designer.\n\n"
        "AUTHORITATIVE DESIGN\n"
        "The attached blueprint and the provided deterministic layout are the source of truth.\n"
        "Your task is to enhance appearance only, not redesign the house.\n\n"
        "USER REQUIREMENTS\n"
        f"- Plot: {_plot_label(land_size_category)}\n"
        f"- Bedrooms: {bedroom_count}\n"
        f"- Bathrooms: {bathroom_count}\n"
        f"- House style: {style_label}\n"
        "- Floors: exactly 1\n\n"
        "MUST PRESERVE\n"
        "- Keep the house exactly single-floor.\n"
        "- Keep the exact bedroom count.\n"
        "- Keep the exact bathroom count.\n"
        "- Keep the same room set.\n"
        "- Preserve room boundaries and relative room positions.\n"
        "- Preserve room dimensions as represented by the blueprint.\n"
        "- Preserve the overall footprint and spatial arrangement from the blueprint.\n"
        "- Preserve all doors and openings shown in the blueprint.\n\n"
        "MUST NOT ADD OR CHANGE\n"
        "- Do not add extra rooms or remove rooms.\n"
        "- Do not add another floor or stairs.\n"
        "- Do not add extra bathrooms, guest toilets, or ensuites unless present.\n"
        "- Do not add garages, swimming pools, balconies, terraces, or detached structures unless present.\n"
        "- Do not move walls, resize rooms, or change the building footprint.\n"
        "- Do not ignore the blueprint."
        f"{one_bathroom_rules}\n\n"
        "STYLE GUIDANCE\n"
        f"{style_text}\n\n"
        "VISUAL OUTPUT\n"
        "Create a realistic orthographic top-down furnished residential floor-plan visualization.\n"
        "Avoid perspective distortion, aerial exterior views, and dollhouse cutaway views.\n"
        "Add furniture only inside existing rooms, without obscuring walls, doors, openings, "
        "or important layout structure.\n\n"
        "ROOM SUMMARY\n"
        f"{summary_text}\n\n"
        "LAYOUT DETAILS\n"
    )
    available = MAX_PROMPT_CHARS - len(prefix)
    if available <= 0:
        return prefix[:MAX_PROMPT_CHARS]

    included = []
    used = 0
    for line in room_details:
        addition = line + "\n"
        if used + len(addition) > available:
            break
        included.append(line)
        used += len(addition)
    return prefix + "\n".join(included)


def _is_edit_incompatibility(error: BadRequestError) -> bool:
    """Allow generate fallback only when the edit-specific input/feature is incompatible."""
    code = str(getattr(error, "code", "") or "").lower()
    param = str(getattr(error, "param", "") or "").lower()
    message = str(error).lower()
    if code in {
        "invalid_image",
        "invalid_image_format",
        "unsupported_image",
        "unsupported_model",
        "unsupported_operation",
    }:
        return True
    if param in {"image", "mask"} and any(
        marker in message for marker in ("invalid", "format", "unsupported", "not supported")
    ):
        return True
    return "edit" in message and any(
        marker in message for marker in ("unsupported", "not supported", "unavailable", "incompatible")
    )


class OpenAIVisualizationService:
    def __init__(self, api_key: str = None, workflow_id: str | None = None):
        self.api_key = api_key
        self.workflow_id = workflow_id
        if self.api_key and openai:
            openai.api_key = self.api_key

    def generate_visualization(
        self,
        layout_json: dict,
        expected_bedrooms: int = None,
        expected_bathrooms: int = None,
        land_size_category: str = None,
        house_style: str = None,
    ) -> dict:
        # ---- Kill switch -------------------------------------------------
        if not ENABLE_OPENAI:
            logger.warning("[Visualization] ENABLE_OPENAI=false — no image API call made.")
            return {
                "visualization_id": str(uuid.uuid4()),
                "image_url": None,
                "model": "gpt-image-1",
                "status": "disabled",
                "error": "OpenAI globally disabled (ENABLE_OPENAI=false).",
                "timestamp": datetime.utcnow().isoformat(),
            }

        # ---- Daily spend cap ---------------------------------------------
        try:
            from app.services.ai_guard_db import check_daily_limit, DailyLimitExceeded
            check_daily_limit()
        except Exception as exc:
            if "DailyLimitExceeded" in type(exc).__name__ or "limit" in str(exc).lower():
                logger.warning("[Visualization] Daily limit reached — skipping image generation.")
                return {
                    "visualization_id": str(uuid.uuid4()),
                    "image_url": None,
                    "model": "gpt-image-1",
                    "status": "failed",
                    "error": str(exc),
                    "timestamp": datetime.utcnow().isoformat(),
                }

        from app.design.visualization.layout_renderer import render_blueprint
        rooms = layout_json.get("rooms", [])

        # ---- Validation before saving -------------------------------------
        if expected_bedrooms is not None and expected_bathrooms is not None:
            actual_bedrooms = sum(1 for r in rooms if 'bedroom' in str(r.get("room_type", "")).lower())
            actual_bathrooms = sum(1 for r in rooms if 'bath' in str(r.get("room_type", "")).lower())
            
            print("\n[VISUALIZATION VALIDATION]")
            print("Expected:")
            print(f"Bedrooms:{expected_bedrooms}")
            print(f"Bathrooms:{expected_bathrooms}")
            print("Input layout:")
            print(f"Bedrooms:{actual_bedrooms}")
            print(f"Bathrooms:{actual_bathrooms}\n")
            
            if actual_bedrooms != expected_bedrooms or actual_bathrooms != expected_bathrooms:
                logger.error("[Visualization] Room mismatch validation failed.")
                return {
                    "visualization_id": str(uuid.uuid4()),
                    "image_url": None,
                    "model": "gpt-image-1",
                    "status": "failed",
                    "error": "Generated layout failed room requirement validation.",
                    "timestamp": datetime.utcnow().isoformat(),
                }

        img_bytes = render_blueprint(layout_json)
        print("EXPECTED_ROOM_LAYOUT:")
        print(json.dumps({
            "bedrooms": actual_bedrooms if expected_bedrooms is not None else 0,
            "bathrooms": actual_bathrooms if expected_bathrooms is not None else 0,
            "rooms": rooms
        }, indent=1))

        prompt = _build_visualization_prompt(
            rooms,
            expected_bedrooms,
            expected_bathrooms,
            land_size_category,
            house_style,
        )
        try:
            if not self.api_key or not openai:
                raise ValueError("OpenAI API key or library missing.")

            char_count = len(prompt)
            print(
                f"[AI Request] purpose=visualization workflow={self.workflow_id or 'n/a'} "
                f"characters={char_count} estimated_tokens={char_count // 4}"
            )
            print("[Visualization Agent] Sending prompt to OpenAI gpt-image-1")
            logger.info("[Visualization Agent] Sending prompt to OpenAI")

            try:
                response = openai.images.edit(
                    model="gpt-image-1",
                    image=img_bytes,
                    prompt=prompt,
                    n=1,
                    size="1024x1024",
                    quality="medium",
                )
            except BadRequestError as exc:
                if not _is_edit_incompatibility(exc):
                    logger.warning(
                        "[Visualization] Non-retryable OpenAI bad-request error; fallback suppressed."
                    )
                    raise
                logger.info(
                    "[Visualization] Image edit is incompatible; using one fresh-generation fallback."
                )
                response = openai.images.generate(
                    model="gpt-image-1",
                    prompt=prompt,
                    n=1,
                    size="1024x1024",
                    quality="medium",
                )
            except (RateLimitError, AuthenticationError, PermissionDeniedError):
                logger.warning(
                    "[Visualization] Non-retryable OpenAI quota/auth/permission error; fallback suppressed."
                )
                raise

            image = response.data[0]
            image_url = getattr(image, "url", None)
            image_b64 = getattr(image, "b64_json", None)
            if not image_url and not image_b64:
                raise ValueError("OpenAI image response contained neither a URL nor image data.")

            # ---- Cost logging for image generation -----------------------
            try:
                from app.services.ai_guard_db import log_ai_cost
                log_ai_cost(self.workflow_id, "visualization", "gpt-image-1", 0, 0)
            except Exception:
                pass

            print("[Visualization] Image generated successfully")
            logger.info("[Visualization] Image generated successfully")

            return {
                "visualization_id": str(uuid.uuid4()),
                "image_url": image_url,
                "image_b64": image_b64,
                "model": "gpt-image-1",
                "prompt": prompt,
                "status": "validated",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error("[Visualization Agent] AI visualization failed (%s).", type(e).__name__)
            return {
                "visualization_id": str(uuid.uuid4()),
                "image_url": None,
                "model": "gpt-image-1",
                "prompt": prompt,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
