# Copyright 2025 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the search tool's argument hardening.

These cover the Ryzon fork's hardening of the `search` tool so that
list-typed parameters (`fields`, `conditions`, `orderings`) tolerate the
string-encoded forms that some MCP clients send, instead of failing
pydantic validation with a `list_type` error.
"""

import asyncio
import json
import unittest

from mcp.server.fastmcp.utilities.func_metadata import func_metadata
from pydantic import ValidationError

from ads_mcp.tools import search as search_mod


class TestCoerceStrList(unittest.TestCase):
    """The `_coerce_str_list` normalization helper."""

    def test_none_stays_none(self):
        self.assertIsNone(search_mod._coerce_str_list(None))

    def test_real_list_passes_through(self):
        self.assertEqual(
            search_mod._coerce_str_list(["a", "b"]), ["a", "b"]
        )

    def test_json_array_string_becomes_list(self):
        self.assertEqual(
            search_mod._coerce_str_list('["a", "b"]'), ["a", "b"]
        )

    def test_bare_string_becomes_single_element_list(self):
        self.assertEqual(
            search_mod._coerce_str_list("metrics.clicks"), ["metrics.clicks"]
        )

    def test_single_quoted_condition_is_not_split_on_commas(self):
        # A condition with commas inside IN(...) must survive as ONE element.
        cond = "geographic_view.country_criterion_id IN (2276, 2040, 2756)"
        self.assertEqual(search_mod._coerce_str_list(cond), [cond])


class TestBuildQuery(unittest.TestCase):
    """The `_build_query` GAQL builder normalizes its list args."""

    def test_list_args_build_expected_gaql(self):
        query = search_mod._build_query(
            fields=["metrics.clicks", "metrics.impressions"],
            resource="campaign",
            conditions=["segments.date = '2026-05-25'"],
            orderings=["metrics.clicks DESC"],
            limit=10,
        )
        self.assertEqual(
            query,
            "SELECT metrics.clicks,metrics.impressions FROM campaign"
            " WHERE segments.date = '2026-05-25'"
            " ORDER BY metrics.clicks DESC LIMIT 10",
        )

    def test_json_string_conditions_build_same_gaql_as_list(self):
        conds = [
            "segments.date BETWEEN '2026-05-25' AND '2026-05-31'",
            "geographic_view.country_criterion_id IN (2276, 2040)",
        ]
        from_list = search_mod._build_query(
            fields=["metrics.clicks"], resource="campaign", conditions=conds
        )
        from_json_string = search_mod._build_query(
            fields=["metrics.clicks"],
            resource="campaign",
            conditions=json.dumps(conds),
        )
        self.assertEqual(from_list, from_json_string)


class TestSearchToolValidationBoundary(unittest.TestCase):
    """The MCP boundary: FastMCP must not reject string-encoded args.

    This exercises the exact validation path FastMCP uses on a tool call
    (`pre_parse_json` + pydantic `model_validate`) against the real
    `search` function signature.
    """

    def _validate(self, arguments):
        meta = func_metadata(search_mod.search)
        pre_parsed = meta.pre_parse_json(arguments)
        # Raises ValidationError if the signature rejects the input.
        return meta.arg_model.model_validate(pre_parsed)

    def test_bare_string_condition_is_accepted(self):
        # A non-JSON bare string is the form a current mcp cannot recover
        # via pre_parse_json, so the un-widened List[str] signature rejects
        # it. After widening, validation must accept it.
        args = {
            "customer_id": "1234567890",
            "fields": ["metrics.clicks"],
            "resource": "campaign",
            "conditions": "segments.date DURING LAST_7_DAYS",
        }
        try:
            self._validate(args)
        except ValidationError as e:
            self.fail(f"search rejected a string condition: {e}")


if __name__ == "__main__":
    unittest.main()
