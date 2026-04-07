"""export_figma_frames tool — export Figma frames as PNG and upload to GCS."""

import json
import os
import re
import asyncio
from fnmatch import fnmatch
from typing import Optional

import httpx

from .config import config
from .gcs import DAM_META_PREFIX, upload_blob
from .server import mcp_server
from .utils import logger, now_iso

FIGMA_API_BASE = "https://api.figma.com/v1"
MAX_IDS_PER_REQUEST = 5
MAX_RETRIES = 2
RETRY_WAIT_SECONDS = 30


def _get_figma_token() -> str | None:
    return os.environ.get("FIGMA_PAT")


def _extract_file_key(figma_url: str) -> str | None:
    """Extract file key from a Figma URL."""
    match = re.search(r"/design/([a-zA-Z0-9]+)", figma_url)
    if match:
        return match.group(1)
    match = re.search(r"/file/([a-zA-Z0-9]+)", figma_url)
    if match:
        return match.group(1)
    return None


def _sanitize_filename(name: str) -> str:
    """Sanitize a frame name into a safe filename."""
    return re.sub(r"[^\w\-.]", "_", name)


async def _figma_get(client: httpx.AsyncClient, url: str, token: str) -> dict:
    """Make a GET request to Figma API with retry on 429."""
    for attempt in range(MAX_RETRIES + 1):
        resp = await client.get(url, headers={"X-Figma-Token": token})
        if resp.status_code == 429:
            if attempt < MAX_RETRIES:
                wait = RETRY_WAIT_SECONDS * (attempt + 1)
                logger.warning(f"Figma rate limited, waiting {wait}s (attempt {attempt + 1})")
                await asyncio.sleep(wait)
                continue
            raise httpx.HTTPStatusError(
                f"Figma rate limited after {MAX_RETRIES + 1} attempts. Wait a few minutes and try again.",
                request=resp.request,
                response=resp,
            )
        resp.raise_for_status()
        return resp.json()
    return {}


def _find_matching_frames(node: dict, pattern: str, results: list, depth: int = 0) -> None:
    """Recursively find frames/components matching a name pattern."""
    name = node.get("name", "")
    node_type = node.get("type", "")

    if node_type in ("FRAME", "COMPONENT", "COMPONENT_SET", "INSTANCE"):
        if fnmatch(name, pattern) or name == pattern:
            results.append({
                "id": node["id"],
                "name": name,
                "type": node_type,
            })

    for child in node.get("children", []):
        _find_matching_frames(child, pattern, results, depth + 1)


@mcp_server.tool()
async def export_figma_frames(
    figma_url: str,
    frame_names: str,
    folder: str = "figma-exports",
    scale: int = 2,
    campaign: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> str:
    """Export frames from a Figma file as PNG and upload to GCS.

    Finds frames matching the given names/pattern, exports them as flattened PNG
    images via the Figma API, and uploads to the DAM GCS bucket.

    Args:
        figma_url: Full Figma file URL (e.g. https://www.figma.com/design/ABC123/...)
        frame_names: Comma-separated frame names or glob pattern (e.g. "Hero_1, Hero_2" or "Hero_*")
        folder: GCS folder prefix for uploads (default: "figma-exports")
        scale: Export scale factor (default: 2 for 2x resolution)
        campaign: Campaign name to tag assets with
        tags: Additional tags for the exported assets
    """
    error = config.validate()
    if error:
        return json.dumps({"error": error}, indent=2)

    token = _get_figma_token()
    if not token:
        return json.dumps(
            {"error": "FIGMA_PAT environment variable not set. Get a token from Figma > Settings > Personal Access Tokens."},
            indent=2,
        )

    file_key = _extract_file_key(figma_url)
    if not file_key:
        return json.dumps(
            {"error": f"Could not extract file key from URL: {figma_url}"},
            indent=2,
        )

    # Parse frame name patterns
    patterns = [p.strip() for p in frame_names.split(",") if p.strip()]

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Get file structure
        logger.info(f"Fetching Figma file structure for {file_key}")
        try:
            file_data = await _figma_get(
                client,
                f"{FIGMA_API_BASE}/files/{file_key}?depth=2",
                token,
            )
        except httpx.HTTPStatusError as e:
            return json.dumps({"error": f"Figma API error: {e.response.status_code} {e.response.text}"}, indent=2)

        # Step 2: Find matching frames
        matching_frames = []
        document = file_data.get("document", {})
        for pattern in patterns:
            _find_matching_frames(document, pattern, matching_frames)

        # Deduplicate by ID
        seen_ids = set()
        unique_frames = []
        for frame in matching_frames:
            if frame["id"] not in seen_ids:
                seen_ids.add(frame["id"])
                unique_frames.append(frame)
            else:
                logger.warning(f"Duplicate frame: {frame['name']} (id: {frame['id']})")

        if not unique_frames:
            return json.dumps(
                {"error": f"No frames found matching: {frame_names}", "patterns": patterns},
                indent=2,
            )

        logger.info(f"Found {len(unique_frames)} matching frames")

        # Step 3: Export frames as PNG (batch by MAX_IDS_PER_REQUEST)
        exported = []
        errors = []

        for i in range(0, len(unique_frames), MAX_IDS_PER_REQUEST):
            batch = unique_frames[i : i + MAX_IDS_PER_REQUEST]
            ids_param = ",".join(f["id"] for f in batch)

            try:
                export_data = await _figma_get(
                    client,
                    f"{FIGMA_API_BASE}/images/{file_key}?ids={ids_param}&format=png&scale={scale}",
                    token,
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 400:
                    # Render timeout — try one at a time with lower scale
                    logger.warning("Batch export failed, retrying individually at 1x scale")
                    for frame in batch:
                        try:
                            single_data = await _figma_get(
                                client,
                                f"{FIGMA_API_BASE}/images/{file_key}?ids={frame['id']}&format=png&scale=1",
                                token,
                            )
                            image_url = single_data.get("images", {}).get(frame["id"])
                            if image_url:
                                export_data = {"images": {frame["id"]: image_url}}
                            else:
                                errors.append(f"{frame['name']}: no image URL returned")
                                continue
                        except Exception as ex:
                            errors.append(f"{frame['name']}: {ex}")
                            continue
                else:
                    for frame in batch:
                        errors.append(f"{frame['name']}: export failed ({e.response.status_code})")
                    continue

            images = export_data.get("images", {})

            # Step 4: Download and upload each frame
            for frame in batch:
                image_url = images.get(frame["id"])
                if not image_url:
                    errors.append(f"{frame['name']}: no image URL in export response")
                    continue

                try:
                    img_resp = await client.get(image_url, timeout=30.0)
                    img_resp.raise_for_status()
                    image_bytes = img_resp.content

                    filename = f"{_sanitize_filename(frame['name'])}.png"
                    folder_clean = folder.strip("/")
                    blob_name = f"{folder_clean}/{filename}" if folder_clean else filename

                    metadata = {
                        f"{DAM_META_PREFIX}original_filename": filename,
                        f"{DAM_META_PREFIX}upload_source": "figma_export",
                        f"{DAM_META_PREFIX}campaign": campaign or "",
                        f"{DAM_META_PREFIX}tags": ",".join(tags) if tags else "",
                        f"{DAM_META_PREFIX}created_at": now_iso(),
                        f"{DAM_META_PREFIX}figma_file_key": file_key,
                        f"{DAM_META_PREFIX}figma_node_id": frame["id"],
                        f"{DAM_META_PREFIX}figma_frame_name": frame["name"],
                    }

                    upload_blob(blob_name, image_bytes, "image/png", metadata)
                    exported.append({
                        "frame_name": frame["name"],
                        "asset_id": blob_name,
                        "size_bytes": len(image_bytes),
                    })
                    logger.info(f"Exported: {frame['name']} → {blob_name} ({len(image_bytes)} bytes)")

                except Exception as e:
                    errors.append(f"{frame['name']}: download/upload failed: {e}")
                    logger.error(f"Failed to export {frame['name']}: {e}")

    return json.dumps(
        {
            "status": "completed",
            "frames_found": len(unique_frames),
            "frames_exported": len(exported),
            "exported": exported,
            "errors": errors,
        },
        indent=2,
    )
