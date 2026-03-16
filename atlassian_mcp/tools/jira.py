"""
Jira MCP Tools
Search and retrieve Jira issues via Atlassian REST API.
"""

import base64
import json
import logging

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
    return get_settings().ATLASSIAN_JIRA_SITE_URL.rstrip("/")


# =============================================
# Tool Definitions
# =============================================

TOOLS = [
    types.Tool(
        name="jira_search_issues",
        description="Search Jira issues using JQL.",
        inputSchema={
            "type": "object",
            "properties": {
                "jql": {
                    "type": "string",
                    "description": "JQL query (e.g. 'project = PROJ AND status != Done ORDER BY updated DESC')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 10, max: 50)",
                },
            },
            "required": ["jql"],
        },
    ),
    types.Tool(
        name="jira_get_issue",
        description="Get detailed information for a Jira issue by key.",
        inputSchema={
            "type": "object",
            "properties": {
                "issue_key": {
                    "type": "string",
                    "description": "Jira issue key (e.g. PROJ-123)",
                },
            },
            "required": ["issue_key"],
        },
    ),
    types.Tool(
        name="jira_get_my_issues",
        description="Get Jira issues assigned to the current user.",
        inputSchema={
            "type": "object",
            "properties": {
                "status_filter": {
                    "type": "string",
                    "description": "Status filter (e.g. 'In Progress', 'To Do'). Empty returns all non-Done issues.",
                },
            },
            "required": [],
        },
    ),
]


# =============================================
# Tool Handlers
# =============================================


async def search_issues(jql: str, max_results: int = 10) -> str:
    base_url = _get_base_url()
    if not base_url:
        return json.dumps({"error": "ATLASSIAN_JIRA_SITE_URL is not configured."})

    max_results = min(max_results, 50)
    fields = "summary,status,priority,assignee,reporter,created,updated,description,issuetype,project"

    try:
        issues = []
        next_page_token = None

        async with httpx.AsyncClient() as client:
            while len(issues) < max_results:
                params = {
                    "jql": jql,
                    "maxResults": max_results - len(issues),
                    "fields": fields,
                }
                if next_page_token:
                    params["nextPageToken"] = next_page_token

                response = await client.get(
                    f"{base_url}/rest/api/3/search/jql",
                    headers=_get_auth_headers(),
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                for issue in data.get("issues", []):
                    f = issue.get("fields", {})
                    key = issue.get("key", "")
                    issues.append(
                        {
                            "key": key,
                            "url": f"{base_url}/browse/{key}",
                            "summary": f.get("summary", ""),
                            "status": (f.get("status") or {}).get("name", ""),
                            "priority": (f.get("priority") or {}).get("name", ""),
                            "assignee": (f.get("assignee") or {}).get(
                                "displayName", ""
                            ),
                            "reporter": (f.get("reporter") or {}).get(
                                "displayName", ""
                            ),
                            "type": (f.get("issuetype") or {}).get("name", ""),
                            "project": (f.get("project") or {}).get("key", ""),
                            "created": f.get("created", ""),
                            "updated": f.get("updated", ""),
                        }
                    )

                next_page_token = data.get("nextPageToken")
                if not next_page_token:
                    break

        return json.dumps(
            {"count": len(issues), "issues": issues},
            ensure_ascii=False,
            indent=2,
        )

    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"Jira API error: {e.response.status_code}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def get_issue(issue_key: str) -> str:
    base_url = _get_base_url()
    if not base_url:
        return json.dumps({"error": "ATLASSIAN_JIRA_SITE_URL is not configured."})

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/rest/api/3/issue/{issue_key}",
                headers=_get_auth_headers(),
                timeout=30.0,
            )
            response.raise_for_status()
            issue = response.json()

        fields = issue.get("fields", {})

        # ADF -> plain text
        description = ""
        desc_field = fields.get("description")
        if desc_field and isinstance(desc_field, dict):
            for block in desc_field.get("content", []):
                for inner in block.get("content", []):
                    if inner.get("type") == "text":
                        description += inner.get("text", "")
                description += "\n"
        elif isinstance(desc_field, str):
            description = desc_field

        comments = []
        for comment in (fields.get("comment") or {}).get("comments", [])[-5:]:
            author = (comment.get("author") or {}).get("displayName", "")
            body = ""
            body_field = comment.get("body")
            if body_field and isinstance(body_field, dict):
                for block in body_field.get("content", []):
                    for inner in block.get("content", []):
                        if inner.get("type") == "text":
                            body += inner.get("text", "")
                    body += "\n"
            elif isinstance(body_field, str):
                body = body_field
            comments.append(
                {
                    "author": author,
                    "body": body.strip(),
                    "created": comment.get("created", ""),
                }
            )

        result = {
            "key": issue.get("key", ""),
            "url": f"{base_url}/browse/{issue.get('key', '')}",
            "summary": fields.get("summary", ""),
            "status": (fields.get("status") or {}).get("name", ""),
            "priority": (fields.get("priority") or {}).get("name", ""),
            "assignee": (fields.get("assignee") or {}).get("displayName", ""),
            "reporter": (fields.get("reporter") or {}).get("displayName", ""),
            "type": (fields.get("issuetype") or {}).get("name", ""),
            "project": (fields.get("project") or {}).get("key", ""),
            "description": description.strip(),
            "comments": comments,
            "created": fields.get("created", ""),
            "updated": fields.get("updated", ""),
            "custom_fields": {
                k: v
                for k, v in fields.items()
                if k.startswith("customfield_") and v is not None and v != []
            },
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"Jira API error: {e.response.status_code}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def get_my_issues(status_filter: str = "") -> str:
    jql = "assignee = currentUser() AND status != Done ORDER BY updated DESC"
    if status_filter:
        jql = f'assignee = currentUser() AND status = "{status_filter}" ORDER BY updated DESC'
    return await search_issues(jql=jql, max_results=20)


async def handle_tool(name: str, arguments: dict) -> str:
    """Route tool calls to the appropriate handler."""
    if name == "jira_search_issues":
        return await search_issues(
            jql=arguments["jql"],
            max_results=arguments.get("max_results", 10),
        )
    elif name == "jira_get_issue":
        return await get_issue(issue_key=arguments["issue_key"])
    elif name == "jira_get_my_issues":
        return await get_my_issues(status_filter=arguments.get("status_filter", ""))
    else:
        return json.dumps({"error": f"Unknown jira tool: {name}"})
