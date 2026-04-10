"""
Unit Tests for Ryzon Default Injection.

Validates that Ryzon-specific defaults are correctly applied when RYZON_MODE
is active and that they don't interfere when RYZON_MODE is off.
"""

import json
import os
import pytest
from unittest.mock import AsyncMock, patch

from meta_ads_mcp.core.ryzon_config import (
    RYZON_ACCOUNT_ID,
    RYZON_CREATIVE_FEATURES_SPEC,
    RYZON_DSA_BENEFICIARY,
    RYZON_DSA_PAYOR,
    RYZON_INSTAGRAM_ACTOR_ID,
    RYZON_PAGE_ID,
    RYZON_STANDARD_TRACKING_SPECS,
    RYZON_UTM_TAGS,
    is_ryzon_mode,
)
from meta_ads_mcp.core.ryzon_defaults import (
    apply_ryzon_ad_defaults,
    apply_ryzon_adset_defaults,
    apply_ryzon_campaign_defaults,
    apply_ryzon_creative_defaults,
)


class TestIsRyzonMode:
    """Test the RYZON_MODE environment variable toggle."""

    def test_off_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            assert not is_ryzon_mode()

    def test_on_with_1(self):
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            assert is_ryzon_mode()

    def test_on_with_true(self):
        with patch.dict(os.environ, {"RYZON_MODE": "true"}):
            assert is_ryzon_mode()

    def test_on_with_yes(self):
        with patch.dict(os.environ, {"RYZON_MODE": "yes"}):
            assert is_ryzon_mode()

    def test_off_with_0(self):
        with patch.dict(os.environ, {"RYZON_MODE": "0"}):
            assert not is_ryzon_mode()

    def test_off_with_empty(self):
        with patch.dict(os.environ, {"RYZON_MODE": ""}):
            assert not is_ryzon_mode()


class TestCampaignDefaults:
    """Test apply_ryzon_campaign_defaults."""

    def test_no_change_when_off(self):
        with patch.dict(os.environ, {}, clear=True):
            account_id, status = apply_ryzon_campaign_defaults("act_custom", "ACTIVE")
            assert account_id == "act_custom"
            assert status == "ACTIVE"

    def test_fills_account_id(self):
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            account_id, status = apply_ryzon_campaign_defaults("", "PAUSED")
            assert account_id == RYZON_ACCOUNT_ID

    def test_forces_paused(self):
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            account_id, status = apply_ryzon_campaign_defaults("act_custom", "ACTIVE")
            assert status == "PAUSED"

    def test_explicit_account_preserved(self):
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            account_id, status = apply_ryzon_campaign_defaults("act_other", "ACTIVE")
            assert account_id == "act_other"


class TestAdsetDefaults:
    """Test apply_ryzon_adset_defaults."""

    def test_no_change_when_off(self):
        with patch.dict(os.environ, {}, clear=True):
            account_id, targeting, dsa_b, dsa_p = apply_ryzon_adset_defaults(
                "act_x", {"age_min": 25}, None, None
            )
            assert dsa_b is None
            assert dsa_p is None

    def test_fills_dsa_fields(self):
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            _, _, dsa_b, dsa_p = apply_ryzon_adset_defaults(
                "act_x", None, None, None
            )
            assert dsa_b == RYZON_DSA_BENEFICIARY
            assert dsa_p == RYZON_DSA_PAYOR

    def test_explicit_dsa_preserved(self):
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            _, _, dsa_b, dsa_p = apply_ryzon_adset_defaults(
                "act_x", None, "Custom GmbH", "Custom GmbH"
            )
            assert dsa_b == "Custom GmbH"
            assert dsa_p == "Custom GmbH"

    def test_advantage_audience_injected_for_custom_targeting(self):
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            _, targeting, _, _ = apply_ryzon_adset_defaults(
                "act_x",
                {"age_min": 25, "geo_locations": {"countries": ["DE"]}},
                None, None
            )
            assert targeting["targeting_automation"]["advantage_audience"] == 1

    def test_excluded_audiences_injected(self):
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            _, targeting, _, _ = apply_ryzon_adset_defaults(
                "act_x",
                {"age_min": 18, "geo_locations": {"countries": ["DE"]}},
                None, None
            )
            assert "excluded_custom_audiences" in targeting
            assert targeting["excluded_custom_audiences"][0]["id"] == "6607160126046"

    def test_existing_excluded_audiences_not_overwritten(self):
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            custom_exclusions = [{"id": "999", "name": "Custom"}]
            _, targeting, _, _ = apply_ryzon_adset_defaults(
                "act_x",
                {"age_min": 18, "excluded_custom_audiences": custom_exclusions},
                None, None
            )
            assert targeting["excluded_custom_audiences"] == custom_exclusions

    def test_targeting_not_mutated(self):
        """Ensure the original targeting dict is not mutated."""
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            original = {"age_min": 25}
            _, targeting, _, _ = apply_ryzon_adset_defaults("act_x", original, None, None)
            assert "targeting_automation" not in original
            assert "targeting_automation" in targeting


class TestCreativeDefaults:
    """Test apply_ryzon_creative_defaults."""

    def test_no_change_when_off(self):
        with patch.dict(os.environ, {}, clear=True):
            result = apply_ryzon_creative_defaults("act_x", None, None, None, None)
            assert result == ("act_x", None, None, None, None)

    def test_fills_all_defaults(self):
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            account_id, page_id, ig_id, cfs, tags = apply_ryzon_creative_defaults(
                "", None, None, None, None
            )
            assert account_id == RYZON_ACCOUNT_ID
            assert page_id == RYZON_PAGE_ID
            assert ig_id == RYZON_INSTAGRAM_ACTOR_ID
            assert tags == RYZON_UTM_TAGS
            assert cfs is not None

    def test_creative_features_spec_all_opt_out(self):
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            _, _, _, cfs, _ = apply_ryzon_creative_defaults("act_x", None, None, None, None)
            assert len(cfs) == 17
            for feature, config in cfs.items():
                assert config["enroll_status"] == "OPT_OUT", f"{feature} not OPT_OUT"

    def test_explicit_page_id_preserved(self):
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            _, page_id, _, _, _ = apply_ryzon_creative_defaults(
                "act_x", "custom_page", None, None, None
            )
            assert page_id == "custom_page"

    def test_explicit_creative_features_spec_preserved(self):
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            custom_spec = {"image_touchups": {"enroll_status": "OPT_IN"}}
            _, _, _, cfs, _ = apply_ryzon_creative_defaults(
                "act_x", None, None, custom_spec, None
            )
            assert cfs == custom_spec

    def test_explicit_url_tags_preserved(self):
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            _, _, _, _, tags = apply_ryzon_creative_defaults(
                "act_x", None, None, None, "custom_utm=test"
            )
            assert tags == "custom_utm=test"


class TestAdDefaults:
    """Test apply_ryzon_ad_defaults."""

    def test_no_change_when_off(self):
        with patch.dict(os.environ, {}, clear=True):
            account_id, status, specs = apply_ryzon_ad_defaults("act_x", "ACTIVE", None)
            assert status == "ACTIVE"
            assert specs is None

    def test_fills_tracking_specs(self):
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            _, _, specs = apply_ryzon_ad_defaults("act_x", "PAUSED", None)
            assert specs is not None
            assert len(specs) == len(RYZON_STANDARD_TRACKING_SPECS)
            assert specs[0]["action.type"] == ["offsite_conversion"]

    def test_forces_paused(self):
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            _, status, _ = apply_ryzon_ad_defaults("act_x", "ACTIVE", None)
            assert status == "PAUSED"

    def test_explicit_tracking_specs_preserved(self):
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            custom_specs = [{"action.type": ["custom"], "fb_pixel": ["123"]}]
            _, _, specs = apply_ryzon_ad_defaults("act_x", "PAUSED", custom_specs)
            assert specs == custom_specs


class TestIntegrationCreateAd:
    """Integration tests: verify defaults flow through create_ad."""

    @pytest.fixture
    def mock_api(self):
        with patch('meta_ads_mcp.core.ads.make_api_request', new_callable=AsyncMock) as mock:
            mock.return_value = {"id": "ad_123"}
            yield mock

    @pytest.mark.asyncio
    async def test_tracking_specs_auto_applied(self, mock_api):
        from meta_ads_mcp.core.ads import create_ad
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            await create_ad(
                account_id="act_1094748267242607",
                name="Test Ad",
                adset_id="adset_123",
                creative_id="creative_123",
                access_token="test_token"
            )
            call_args = mock_api.call_args
            params = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("params", {})
            assert "tracking_specs" in params

    @pytest.mark.asyncio
    async def test_no_tracking_specs_when_off(self, mock_api):
        from meta_ads_mcp.core.ads import create_ad
        with patch.dict(os.environ, {}, clear=True):
            await create_ad(
                account_id="act_1094748267242607",
                name="Test Ad",
                adset_id="adset_123",
                creative_id="creative_123",
                access_token="test_token"
            )
            call_args = mock_api.call_args
            params = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("params", {})
            assert "tracking_specs" not in params


class TestIntegrationCreateAdCreative:
    """Integration tests: verify defaults flow through create_ad_creative."""

    @pytest.fixture
    def mock_api(self):
        with patch('meta_ads_mcp.core.ads.make_api_request', new_callable=AsyncMock) as mock:
            mock.return_value = {"id": "creative_123"}
            yield mock

    @pytest.mark.asyncio
    async def test_page_id_auto_filled(self, mock_api):
        from meta_ads_mcp.core.ads import create_ad_creative
        with patch.dict(os.environ, {"RYZON_MODE": "1"}):
            result = await create_ad_creative(
                account_id="act_1094748267242607",
                image_hash="abc123",
                link_url="https://ryzon.com",
                message="Test",
                access_token="test_token"
            )
            # Should not fail with "no page ID" error since Ryzon default fills it
            result_data = json.loads(result)
            if "data" in result_data and isinstance(result_data["data"], str):
                result_data = json.loads(result_data["data"])
            assert "error" not in result_data or "page" not in result_data.get("error", "").lower()
