"""
Ryzon-specific configuration constants for Meta Ads MCP.

Activated when RYZON_MODE environment variable is set to "1", "true", or "yes".
When active, these defaults are auto-applied to creation functions.
Explicit parameter values always override these defaults.
"""

import os


def is_ryzon_mode() -> bool:
    """Check if Ryzon client profile is active."""
    return os.environ.get("RYZON_MODE", "").strip().lower() in ("1", "true", "yes")


# Account identifiers
RYZON_ACCOUNT_ID = "act_1094748267242607"
RYZON_PAGE_ID = "503034229903027"
RYZON_INSTAGRAM_ACTOR_ID = "17841402429257855"
RYZON_PIXEL_ID = "1692231597657974"
RYZON_APP_ID = "2806336879449701"

# DSA compliance (required for EU markets)
RYZON_DSA_BENEFICIARY = "Ryzon GmbH"
RYZON_DSA_PAYOR = "Ryzon GmbH"

# Excluded audiences
RYZON_EXCLUDED_AUDIENCES = [
    {"id": "6607160126046", "name": "F0_Negative_Audience"}
]

# Default targeting base
RYZON_DEFAULT_TARGETING = {
    "age_min": 18,
    "age_max": 65,
    "targeting_automation": {"advantage_audience": 1}
}

# Standard UTM parameters with Meta dynamic placeholders
RYZON_UTM_TAGS = (
    "utm_source=facebook"
    "&utm_medium=paid_social"
    "&utm_campaign={{campaign.name}}"
    "&utm_content={{ad.name}}"
    "&utm_term={{adset.name}}"
    "&klar_source=meta"
    "&klar_adid={{ad.id}}"
)

# Creative features spec — ALL Advantage+ optimizations disabled
RYZON_CREATIVE_FEATURES_SPEC = {
    "image_touchups": {"enroll_status": "OPT_OUT"},
    "text_optimizations": {"enroll_status": "OPT_OUT"},
    "inline_comment": {"enroll_status": "OPT_OUT"},
    "add_text_overlay": {"enroll_status": "OPT_OUT"},
    "music": {"enroll_status": "OPT_OUT"},
    "3d_animation": {"enroll_status": "OPT_OUT"},
    "image_animation": {"enroll_status": "OPT_OUT"},
    "image_templates": {"enroll_status": "OPT_OUT"},
    "catalog_automation": {"enroll_status": "OPT_OUT"},
    "enhance_cta": {"enroll_status": "OPT_OUT"},
    "text_generation": {"enroll_status": "OPT_OUT"},
    "profile_card": {"enroll_status": "OPT_OUT"},
    "site_extensions": {"enroll_status": "OPT_OUT"},
    "media_liquidity": {"enroll_status": "OPT_OUT"},
    "cv_transformation": {"enroll_status": "OPT_OUT"},
    "standard_enhancements": {"enroll_status": "OPT_OUT"},
    "translate_text": {"enroll_status": "OPT_OUT"},
}

# Standard tracking specs (applied to every ad)
RYZON_STANDARD_TRACKING_SPECS = [
    {"action.type": ["offsite_conversion"], "fb_pixel": ["1692231597657974"]},
    {"action.type": ["commerce_event"], "page": ["503034229903027"]},
    {"action.type": ["app_custom_event"], "application": ["2806336879449701"]},
    {"action.type": ["mobile_app_install"], "application": ["2806336879449701"]},
    {"action.type": ["onsite_conversion"]},
    {
        "action.type": ["onsite_conversion"],
        "conversion_id": [
            "1016350596141424", "2001207199873349", "2211337513561241",
            "827620174248220G", "883842997878932312", "892327596441502",
            "927567698587314G", "973222559346350G", "239243539390508G",
            "284347524828371S2"
        ]
    },
    {"action.type": ["onsite_conversion"], "conversion_id": ["2405645808063328"]},
]

# Additional tracking spec for Lead campaigns
RYZON_LEAD_TRACKING_SPEC = {
    "action.type": ["leadgen_quality_conversion"],
    "fb_pixel": ["1692231597657974"]
}
