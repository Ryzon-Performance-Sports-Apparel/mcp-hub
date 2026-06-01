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

"""Tools for exposing the API Search method to the MCP server."""

import json
from typing import Any, Dict, List
from ads_mcp.coordinator import mcp
import ads_mcp.utils as utils


def _coerce_str_list(value: List[str] | str | None) -> List[str] | None:
    """Normalizes a list-typed argument that a client may send as a string.

    Some MCP clients serialize array arguments as JSON strings (or even bare
    strings) instead of real lists. FastMCP recovers clean JSON-array strings,
    but not every form, so the tool defends itself here.

    Rules:
        - None stays None.
        - A list is returned with its items stringified.
        - A JSON-array string is parsed into its list of items.
        - Any other string becomes a single-element list. We deliberately do
          NOT split on commas: a single condition legitimately contains commas
          (e.g. ``... IN (2276, 2040)``), and ``','.join`` / ``' AND '.join``
          of a one-element list reproduces the original string verbatim.
    """
    if value is None:
        return None
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
        # A JSON scalar (e.g. '"metrics.clicks"') -> the decoded scalar text.
        return [str(parsed)]
    return [str(item) for item in value]


def _build_query(
    fields: List[str] | str,
    resource: str,
    conditions: List[str] | str | None = None,
    orderings: List[str] | str | None = None,
    limit: int | str | None = None,
) -> str:
    """Builds a GAQL query string, normalizing string-encoded list args."""
    fields = _coerce_str_list(fields)
    conditions = _coerce_str_list(conditions)
    orderings = _coerce_str_list(orderings)

    query_parts = [f"SELECT {','.join(fields)} FROM {resource}"]

    if conditions:
        query_parts.append(f" WHERE {' AND '.join(conditions)}")

    if orderings:
        query_parts.append(f" ORDER BY {','.join(orderings)}")

    if limit:
        query_parts.append(f" LIMIT {limit}")

    return "".join(query_parts)


def search(
    customer_id: str,
    fields: List[str] | str,
    resource: str,
    conditions: List[str] | str = None,
    orderings: List[str] | str = None,
    limit: int | str = None,
) -> List[Dict[str, Any]]:
    """Fetches data from the Google Ads API using the search method

    Args:
        customer_id: The id of the customer
        fields: The fields to fetch
        resource: The resource to return fields from
        conditions: List of conditions to filter the data, combined using AND clauses
        orderings: How the data is ordered
        limit: The maximum number of rows to return

    """

    ga_service = utils.get_googleads_service("GoogleAdsService")

    query = _build_query(fields, resource, conditions, orderings, limit)
    utils.logger.info(f"ads_mcp.search query {query}")

    query_result = ga_service.search_stream(
        customer_id=customer_id, query=query
    )

    final_output: List = []
    for batch in query_result:
        for row in batch.results:
            final_output.append(
                utils.format_output_row(row, batch.field_mask.paths)
            )
    return final_output


def _search_tool_description() -> str:
    """Returns the description for the `search` tool."""
    # Add a warning that will be part of the description
    file_content = (
        "WARNING: The table of selectable fields is missing. "
        "Tool may not function correctly."
    )

    try:
        with open(utils.get_gaql_resources_filepath(), "r") as file:
            file_content = file.read()
    except FileNotFoundError:
        utils.logger.error("The specified file was not found.")

    return f"""
{search.__doc__}

### Hints
    Language Grammar can be found at https://developers.google.com/google-ads/api/docs/query/grammar
    All resources and descriptions are found at https://developers.google.com/google-ads/api/fields/v23/overview

    For Conversion issues try looking in offline_conversion_upload_conversion_action_summary

### Hint for customer_id
    should be a string of numbers without punctuation
    if presented in the form 123-456-7890 remove the hyphens and use 1234567890

### Hints for Dates
    All dates should be in the form YYYY-MM-DD and must include the dashes (-)
    Date literals from the Grammar must NEVER be used
    Date ranges should be finite and must include a start and end date

### Hints for limits
    Requests to resource change_event must specify a LIMIT of less than or equal to 10000

### Hints for conversions questions
    https://developers.google.com/google-ads/api/docs/conversions/upload-summaries 


### Hints for all fields
    What follows is a table of resources and their selectable fields (fields), filterable fields (used in the condition) and sortable fields (use in the ordering)
    Fields are comma separated, the whole field must be used, wildcards and partial fields are not allowed
    All fields must come from this table and be prefixed with the resource being searched
    {file_content}
"""


# The `search` tool requires a more complex description that's generated at
# runtime. Uses the `add_tool` method instead of an annnotation since `add_tool`
# provides the flexibility needed to generate the description while also
# including the `search` method's docstring.
mcp.add_tool(
    search,
    title="Fetches data from the Google Ads API using the search method",
    description=_search_tool_description(),
)
