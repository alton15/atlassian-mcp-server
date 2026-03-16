# Atlassian MCP Server

[Korean / 한국어](README.ko.md)

MCP (Model Context Protocol) server that provides Jira and Confluence tools for Claude Desktop and Claude Code. Connect your Atlassian workspace directly to Claude for searching issues, reading pages, and more.

## Features

This server exposes 7 tools across two Atlassian products:

**Jira (3 tools)**
- `jira_search_issues` -- Search issues using JQL queries
- `jira_get_issue` -- Get detailed information for a specific issue by key
- `jira_get_my_issues` -- List issues assigned to the current user

**Confluence (4 tools)**
- `confluence_search_pages` -- Search pages using CQL queries
- `confluence_get_page` -- Get page content by page ID (with image download)
- `confluence_get_page_images` -- Get local file paths for downloaded page images
- `confluence_get_recent_updates` -- List recently updated pages

## Setup

### Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- An Atlassian Cloud account with API token

### Install

```bash
git clone https://github.com/alton15/atlassian-mcp-server.git
cd atlassian-mcp-server
uv sync
```

### Environment Variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description | Example |
|---|---|---|
| `ATLASSIAN_EMAIL` | Your Atlassian account email | `user@example.com` |
| `ATLASSIAN_API_TOKEN` | Atlassian API token | `ATATT3x...` |
| `ATLASSIAN_JIRA_SITE_URL` | Your Jira Cloud URL | `https://your-domain.atlassian.net` |
| `ATLASSIAN_CONFLUENCE_SITE_URL` | Your Confluence Cloud URL | `https://your-domain.atlassian.net` |

### Creating an Atlassian API Token

1. Go to [Atlassian API Token Management](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click "Create API token"
3. Give it a label and copy the generated token
4. Store it in your `.env` file as `ATLASSIAN_API_TOKEN`

## Usage

### Claude Code

```bash
claude mcp add atlassian-mcp-server -- uv run --directory /path/to/atlassian-mcp-server python -m atlassian_mcp.server
```

### Claude Desktop

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "atlassian-mcp-server": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/atlassian-mcp-server",
        "python",
        "-m",
        "atlassian_mcp.server"
      ]
    }
  }
}
```

Replace `/path/to/atlassian-mcp-server` with the actual path to your cloned repository.

## Available Tools

### jira_search_issues

Search Jira issues using JQL.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `jql` | string | Yes | JQL query string |
| `max_results` | integer | No | Maximum results to return (default: 10, max: 50) |

### jira_get_issue

Get detailed information for a single Jira issue.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `issue_key` | string | Yes | Jira issue key (e.g. `PROJ-123`) |

Returns summary, status, priority, assignee, reporter, description, last 5 comments, and custom fields.

### jira_get_my_issues

Get issues assigned to the authenticated user.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `status_filter` | string | No | Filter by status (e.g. `In Progress`). Empty returns all non-Done issues. |

### confluence_search_pages

Search Confluence pages using CQL.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | string | Yes | CQL query or search text |
| `max_results` | integer | No | Maximum results to return (default: 10, max: 25) |

### confluence_get_page

Get Confluence page content by ID. Images attached to the page are automatically downloaded to a temporary directory.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `page_id` | string | Yes | Confluence page ID |

### confluence_get_page_images

Get local file paths for images that were downloaded by `confluence_get_page`. Call `confluence_get_page` first.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `page_id` | string | Yes | Confluence page ID |

### confluence_get_recent_updates

Get Confluence pages updated within a given time window.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `hours` | integer | No | Hours to look back (default: 24) |

## License

MIT
