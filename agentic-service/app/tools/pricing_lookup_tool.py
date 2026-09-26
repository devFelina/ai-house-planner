"""
Pricing lookup tool for Cost Estimation Service (Component C).

Fetches current pricing data from ASP.NET Core internal API:
GET /api/v1/internal/pricing

Protected by X-Internal-API-Key header.
Does not access PostgreSQL directly or invent fallback prices.
"""
import logging

import requests
from pydantic import ValidationError

from app.config import ASPNET_API_URL, INTERNAL_API_KEY, PRICING_VERIFY_TLS
from app.schemas.pricing_data import PricingItem

logger = logging.getLogger(__name__)


class PricingLookupError(Exception):
    """Raised when pricing lookup fails due to network, auth, parsing, or empty data."""


def pricing_lookup_tool(
    api_url: str | None = None,
    api_key: str | None = None,
    timeout: int = 10,
    region: str | None = None,
    quality_level: str | None = None,
) -> list[PricingItem]:
    """
    Fetch current pricing catalog from ASP.NET backend.

    Args:
        api_url: Optional base URL override (defaults to ASPNET_API_URL).
        api_key: Optional API key override (defaults to INTERNAL_API_KEY).
        timeout: Request timeout in seconds (default: 10s).

    Returns:
        List[PricingItem]: List of validated pricing items.

    Raises:
        PricingLookupError: If backend is unavailable, times out, returns non-2xx,
                            returns invalid/malformed JSON, or returns empty collection.
    """
    base_url = (api_url or ASPNET_API_URL).rstrip("/")
    endpoint = f"{base_url}/internal/pricing"
    key = api_key if api_key is not None else INTERNAL_API_KEY

    headers = {
        "X-Internal-API-Key": key,
        "Accept": "application/json",
    }

    logger.info("Fetching pricing data from %s", endpoint)
    print(f"[Pricing Tool] Fetching pricing data from {endpoint}...")

    try:
        response = requests.get(
            endpoint,
            headers=headers,
            params={
                "region": region or "Sri Lanka",
                "qualityLevel": quality_level or "Standard",
            },
            timeout=timeout,
            verify=PRICING_VERIFY_TLS
        )
    except requests.exceptions.Timeout as e:
        msg = f"Pricing service request timed out after {timeout}s: {e}"
        logger.error(msg)
        print(f"[Pricing Tool] Error: {msg}")
        raise PricingLookupError(msg) from e
    except requests.exceptions.ConnectionError as e:
        msg = f"Unable to connect to pricing backend at {endpoint}: {e}"
        logger.error(msg)
        print(f"[Pricing Tool] Error: {msg}")
        raise PricingLookupError(msg) from e
    except requests.exceptions.RequestException as e:
        msg = f"HTTP request to pricing backend failed: {e}"
        logger.error(msg)
        print(f"[Pricing Tool] Error: {msg}")
        raise PricingLookupError(msg) from e

    if response.status_code != 200:
        msg = f"Pricing backend returned status {response.status_code}: {response.text}"
        logger.error(msg)
        print(f"[Pricing Tool] Error: {msg}")
        raise PricingLookupError(msg)

    try:
        data = response.json()
    except Exception as e:
        msg = f"Failed to parse pricing JSON response: {e}"
        logger.error(msg)
        print(f"[Pricing Tool] Error: {msg}")
        raise PricingLookupError(msg) from e

    if not isinstance(data, list):
        msg = f"Expected list of pricing items from backend, received {type(data).__name__}"
        logger.error(msg)
        print(f"[Pricing Tool] Error: {msg}")
        raise PricingLookupError(msg)

    if len(data) == 0:
        msg = "Pricing collection is empty. No pricing rows available."
        logger.error(msg)
        print(f"[Pricing Tool] Error: {msg}")
        raise PricingLookupError(msg)

    try:
        items = [PricingItem.model_validate(item) for item in data]
    except ValidationError as e:
        msg = f"Pricing response failed schema validation: {e}"
        logger.error(msg)
        print(f"[Pricing Tool] Error: {msg}")
        raise PricingLookupError(msg) from e

    active_items = [item for item in items if item.is_active]
    if not active_items:
        raise PricingLookupError("Pricing collection contains no active pricing rows.")

    logger.info("Successfully loaded %d active pricing items", len(active_items))
    print(f"[Pricing Tool] Successfully loaded {len(active_items)} active pricing items.")
    return active_items


# Alias for flexible importing
fetch_pricing_data = pricing_lookup_tool
