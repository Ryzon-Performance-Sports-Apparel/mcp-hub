"""
Ryzon default injection helpers.

Each apply_* function merges Ryzon defaults into parameters when RYZON_MODE is active.
Explicit user-provided values always take precedence over defaults.
When RYZON_MODE is off, all functions return parameters unchanged.
"""

import copy
from typing import Any, Dict, List, Optional

from .ryzon_config import (
    RYZON_ACCOUNT_ID,
    RYZON_CREATIVE_FEATURES_SPEC,
    RYZON_DSA_BENEFICIARY,
    RYZON_DSA_PAYOR,
    RYZON_EXCLUDED_AUDIENCES,
    RYZON_INSTAGRAM_ACTOR_ID,
    RYZON_PAGE_ID,
    RYZON_STANDARD_TRACKING_SPECS,
    RYZON_UTM_TAGS,
    is_ryzon_mode,
)


def apply_ryzon_campaign_defaults(
    account_id: str,
    status: str = "PAUSED",
) -> tuple:
    """Apply Ryzon defaults to campaign creation parameters.

    Returns (account_id, status) with Ryzon defaults merged in.
    """
    if not is_ryzon_mode():
        return account_id, status

    if not account_id:
        account_id = RYZON_ACCOUNT_ID
    status = "PAUSED"

    return account_id, status


def apply_ryzon_adset_defaults(
    account_id: str,
    targeting: Optional[Dict[str, Any]],
    dsa_beneficiary: Optional[str],
    dsa_payor: Optional[str],
) -> tuple:
    """Apply Ryzon defaults to ad set creation parameters.

    Returns (account_id, targeting, dsa_beneficiary, dsa_payor) with defaults merged.
    """
    if not is_ryzon_mode():
        return account_id, targeting, dsa_beneficiary, dsa_payor

    if not account_id:
        account_id = RYZON_ACCOUNT_ID

    if not dsa_beneficiary:
        dsa_beneficiary = RYZON_DSA_BENEFICIARY
    if not dsa_payor:
        dsa_payor = RYZON_DSA_PAYOR

    # Ensure advantage_audience is always 1 in Ryzon mode
    if targeting:
        targeting = copy.deepcopy(targeting)
        if "targeting_automation" not in targeting:
            targeting["targeting_automation"] = {"advantage_audience": 1}
        elif targeting["targeting_automation"].get("advantage_audience") is None:
            targeting["targeting_automation"]["advantage_audience"] = 1
    # If no targeting provided, the existing default in create_adset will apply;
    # we override advantage_audience after that block in the integration code.

    # Inject excluded audiences if not already present
    if targeting and "excluded_custom_audiences" not in targeting:
        targeting["excluded_custom_audiences"] = copy.deepcopy(RYZON_EXCLUDED_AUDIENCES)

    return account_id, targeting, dsa_beneficiary, dsa_payor


def apply_ryzon_creative_defaults(
    account_id: str,
    page_id: Optional[Any],
    instagram_actor_id: Optional[str],
    creative_features_spec: Optional[Dict[str, Any]],
    url_tags: Optional[str],
) -> tuple:
    """Apply Ryzon defaults to ad creative creation parameters.

    Returns (account_id, page_id, instagram_actor_id, creative_features_spec, url_tags).
    """
    if not is_ryzon_mode():
        return account_id, page_id, instagram_actor_id, creative_features_spec, url_tags

    if not account_id:
        account_id = RYZON_ACCOUNT_ID
    if not page_id:
        page_id = RYZON_PAGE_ID
    if not instagram_actor_id:
        instagram_actor_id = RYZON_INSTAGRAM_ACTOR_ID
    if not creative_features_spec:
        creative_features_spec = copy.deepcopy(RYZON_CREATIVE_FEATURES_SPEC)
    if not url_tags:
        url_tags = RYZON_UTM_TAGS

    return account_id, page_id, instagram_actor_id, creative_features_spec, url_tags


def apply_ryzon_ad_defaults(
    account_id: str,
    status: str,
    tracking_specs: Optional[List[Dict[str, Any]]],
) -> tuple:
    """Apply Ryzon defaults to ad creation parameters.

    Returns (account_id, status, tracking_specs) with defaults merged.
    """
    if not is_ryzon_mode():
        return account_id, status, tracking_specs

    if not account_id:
        account_id = RYZON_ACCOUNT_ID
    status = "PAUSED"
    if tracking_specs is None:
        tracking_specs = copy.deepcopy(RYZON_STANDARD_TRACKING_SPECS)

    return account_id, status, tracking_specs
