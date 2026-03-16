"""
Confluence MCP Tools
Search and retrieve Confluence pages via Atlassian REST API.
"""

import base64
import json
import logging
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone

import httpx
from mcp import types

from atlassian_mcp.config import get_settings

logger = logging.getLogger(__name__)


# =============================================
# Auth / URL Helpers
# =============================================


def _get_auth_headers() -> dict:
    settings = get_settings()
    if not settings.ATLASSIAN_EMAIL or not settings.ATLASSIAN_API_TOKEN:
        return {}
    credentials = base64.b64encode(
        f"{settings.ATLASSIAN_EMAIL}:{settings.ATLASSIAN_API_TOKEN}".encode()
    ).decode()
    return {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _get_base_url() -> str:
    return get_settings().ATLASSIAN_CONFLUENCE_SITE_URL.rstrip("/")


# =============================================
# Tool Definitions
# =============================================

TOOLS = [
    types.Tool(
        name="confluence_search_pages",
        description="Search Confluence pages using CQL.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": 'CQL query or search text (e.g. \'type=page AND text~"search term"\')',
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 10, max: 25)",
                },
            },
            "required": ["query"],
        },
    ),
    types.Tool(
        name="confluence_get_page",
        description="Get Confluence page content by page ID. If the response image_count is 1 or more, call confluence_get_page_images to view attached images.",
        inputSchema={
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "Confluence page ID",
                },
            },
            "required": ["page_id"],
        },
    ),
    types.Tool(
        name="confluence_get_page_images",
        description="Get local file paths for images attached to a Confluence page. Call confluence_get_page first to download the images.",
        inputSchema={
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "Confluence page ID",
                },
            },
            "required": ["page_id"],
        },
    ),
    types.Tool(
        name="confluence_get_recent_updates",
        description="Get recently updated Confluence pages.",
        inputSchema={
            "type": "object",
            "properties": {
                "hours": {
                    "type": "integer",
                    "description": "Time range in hours to look back (default: 24)",
                },
            },
            "required": [],
        },
    ),
]


# =============================================
# Tool Handlers
# =============================================


async def search_pages(query: str, max_results: int = 10) -> str:
    base_url = _get_base_url()
    if not base_url:
        return json.dumps(
            {"error": "ATLASSIAN_CONFLUENCE_SITE_URL is not configured."}
        )

    max_results = min(max_results, 25)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/wiki/rest/api/content/search",
                headers=_get_auth_headers(),
                params={"cql": query, "limit": max_results, "expand": "version,space"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        pages = []
        for result in data.get("results", []):
            page_id = result.get("id", "")
            space_key = (result.get("space") or {}).get("key", "")
            pages.append(
                {
                    "id": page_id,
                    "title": result.get("title", ""),
                    "url": f"{base_url}/wiki/spaces/{space_key}/pages/{page_id}",
                    "space": space_key,
                    "last_modified": (result.get("version") or {}).get("when", ""),
                    "last_author": (result.get("version") or {}).get("by", {}).get(
                        "displayName", ""
                    ),
                }
            )

        return json.dumps(
            {
                "total": data.get("totalSize", data.get("size", 0)),
                "count": len(pages),
                "pages": pages,
            },
            ensure_ascii=False,
            indent=2,
        )

    except httpx.HTTPStatusError as e:
        return json.dumps(
            {"error": f"Confluence API error: {e.response.status_code}"}
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


async def get_page(page_id: str) -> str:
    base_url = _get_base_url()
    if not base_url:
        return json.dumps(
            {"error": "ATLASSIAN_CONFLUENCE_SITE_URL is not configured."}
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/wiki/api/v2/pages/{page_id}",
                headers=_get_auth_headers(),
                params={"body-format": "storage"},
                timeout=30.0,
            )
            response.raise_for_status()
            page = response.json()

            attachments_resp = await client.get(
                f"{base_url}/wiki/api/v2/pages/{page_id}/attachments",
                headers=_get_auth_headers(),
                timeout=30.0,
            )
            attachments_resp.raise_for_status()
            attachments_data = attachments_resp.json()

        space_id = page.get("spaceId", "")
        body_html = (page.get("body") or {}).get("storage", {}).get("value", "")

        body_text = re.sub(r"<[^>]+>", "", body_html)
        body_text = re.sub(r"\s+", " ", body_text).strip()
        if len(body_text) > 5000:
            body_text = body_text[:5000] + "... (truncated)"

        parent_id = page.get("parentId", "")
        version = page.get("version", {})

        # Download image attachments to tmp folder
        image_attachments = [
            att
            for att in attachments_data.get("results", [])
            if att.get("mediaType", "").startswith("image/")
        ]

        if image_attachments:
            tmp_dir = os.path.join(
                tempfile.gettempdir(), "confluence_images", page_id
            )
            os.makedirs(tmp_dir, exist_ok=True)

            async with httpx.AsyncClient(follow_redirects=True) as client:
                for att in image_attachments:
                    download_link = att.get("downloadLink", "")
                    if not download_link:
                        continue
                    title = att.get("title", "")
                    download_url = f"{base_url}/wiki{download_link}"
                    local_path = os.path.join(tmp_dir, title)
                    try:
                        img_resp = await client.get(
                            download_url,
                            headers=_get_auth_headers(),
                            timeout=60.0,
                        )
                        img_resp.raise_for_status()
                        with open(local_path, "wb") as f:
                            f.write(img_resp.content)
                    except Exception as e:
                        logger.warning(f"Failed to download image ({title}): {e}")

        hint = None
        if image_attachments:
            hint = (
                f"This page has {len(image_attachments)} attached image(s). "
                "Call confluence_get_page_images to get their local file paths."
            )

        result = {
            "id": page.get("id", ""),
            "title": page.get("title", ""),
            "url": f"{base_url}/wiki/pages/{page_id}",
            "spaceId": space_id,
            "content": body_text,
            "version": version.get("number", 0),
            "last_modified": version.get("createdAt", ""),
            "last_author": version.get("authorId", ""),
            "parentId": parent_id,
            "image_count": len(image_attachments),
            "hint": hint,
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.HTTPStatusError as e:
        return json.dumps(
            {"error": f"Confluence API error: {e.response.status_code}"}
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


async def get_page_images(page_id: str) -> str:
    tmp_dir = os.path.join(tempfile.gettempdir(), "confluence_images", page_id)
    if not os.path.isdir(tmp_dir):
        return json.dumps(
            {
                "error": "No downloaded images found. Call confluence_get_page first.",
                "page_id": page_id,
            }
        )

    images = []
    for filename in sorted(os.listdir(tmp_dir)):
        file_path = os.path.join(tmp_dir, filename)
        if os.path.isfile(file_path):
            images.append(
                {
                    "title": filename,
                    "local_path": file_path,
                    "fileSize": os.path.getsize(file_path),
                }
            )

    return json.dumps(
        {"page_id": page_id, "count": len(images), "images": images},
        ensure_ascii=False,
        indent=2,
    )


async def get_recent_updates(hours: int = 24) -> str:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M")
    cql = f'lastmodified >= "{cutoff_str}" ORDER BY lastmodified DESC'
    return await search_pages(query=cql, max_results=20)


async def handle_tool(name: str, arguments: dict) -> str:
    """Route tool calls to the appropriate handler."""
    if name == "confluence_search_pages":
        return await search_pages(
            query=arguments["query"],
            max_results=arguments.get("max_results", 10),
        )
    elif name == "confluence_get_page":
        return await get_page(page_id=arguments["page_id"])
    elif name == "confluence_get_page_images":
        return await get_page_images(page_id=arguments["page_id"])
    elif name == "confluence_get_recent_updates":
        return await get_recent_updates(hours=arguments.get("hours", 24))
    else:
        return json.dumps({"error": f"Unknown confluence tool: {name}"})
