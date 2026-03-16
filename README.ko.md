# Atlassian MCP Server

[English](README.md)

Claude Desktop 및 Claude Code에서 Jira와 Confluence 도구를 사용할 수 있게 해주는 MCP (Model Context Protocol) 서버입니다. Atlassian 워크스페이스를 Claude에 직접 연결하여 이슈 검색, 페이지 조회 등을 수행할 수 있습니다.

## 기능

2개의 Atlassian 제품에 걸쳐 총 7개의 도구를 제공합니다:

**Jira (3개 도구)**
- `jira_search_issues` -- JQL 쿼리로 이슈 검색
- `jira_get_issue` -- 이슈 키로 상세 정보 조회
- `jira_get_my_issues` -- 현재 사용자에게 할당된 이슈 목록 조회

**Confluence (4개 도구)**
- `confluence_search_pages` -- CQL 쿼리로 페이지 검색
- `confluence_get_page` -- 페이지 ID로 내용 조회 (이미지 자동 다운로드)
- `confluence_get_page_images` -- 다운로드된 페이지 이미지의 로컬 파일 경로 조회
- `confluence_get_recent_updates` -- 최근 업데이트된 페이지 목록 조회

## 설정

### 사전 요구 사항

- Python 3.11 이상
- [uv](https://docs.astral.sh/uv/) 패키지 매니저
- API 토큰이 있는 Atlassian Cloud 계정

### 설치

```bash
git clone https://github.com/alton15/atlassian-mcp-server.git
cd atlassian-mcp-server
uv sync
```

### 환경 변수

예시 파일을 복사한 후 값을 입력하세요:

```bash
cp .env.example .env
```

| 변수 | 설명 | 예시 |
|---|---|---|
| `ATLASSIAN_EMAIL` | Atlassian 계정 이메일 | `user@example.com` |
| `ATLASSIAN_API_TOKEN` | Atlassian API 토큰 | `ATATT3x...` |
| `ATLASSIAN_JIRA_SITE_URL` | Jira Cloud URL | `https://your-domain.atlassian.net` |
| `ATLASSIAN_CONFLUENCE_SITE_URL` | Confluence Cloud URL | `https://your-domain.atlassian.net` |

### Atlassian API 토큰 생성

1. [Atlassian API 토큰 관리](https://id.atlassian.com/manage-profile/security/api-tokens) 페이지로 이동
2. "API 토큰 만들기" 클릭
3. 라벨을 입력하고 생성된 토큰을 복사
4. `.env` 파일의 `ATLASSIAN_API_TOKEN`에 저장

## 사용법

### Claude Code

```bash
claude mcp add atlassian-mcp-server -- uv run --directory /path/to/atlassian-mcp-server python -m atlassian_mcp.server
```

### Claude Desktop

`claude_desktop_config.json`에 다음을 추가하세요:

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

`/path/to/atlassian-mcp-server`를 실제 클론한 저장소 경로로 교체하세요.

## 제공 도구

### jira_search_issues

JQL을 사용하여 Jira 이슈를 검색합니다.

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `jql` | string | 예 | JQL 쿼리 문자열 |
| `max_results` | integer | 아니오 | 최대 결과 수 (기본값: 10, 최대: 50) |

### jira_get_issue

단일 Jira 이슈의 상세 정보를 조회합니다.

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `issue_key` | string | 예 | Jira 이슈 키 (예: `PROJ-123`) |

요약, 상태, 우선순위, 담당자, 보고자, 설명, 최근 5개 댓글, 커스텀 필드를 반환합니다.

### jira_get_my_issues

인증된 사용자에게 할당된 이슈를 조회합니다.

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `status_filter` | string | 아니오 | 상태 필터 (예: `In Progress`). 비어있으면 완료되지 않은 모든 이슈 반환. |

### confluence_search_pages

CQL을 사용하여 Confluence 페이지를 검색합니다.

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `query` | string | 예 | CQL 쿼리 또는 검색 텍스트 |
| `max_results` | integer | 아니오 | 최대 결과 수 (기본값: 10, 최대: 25) |

### confluence_get_page

페이지 ID로 Confluence 페이지 내용을 조회합니다. 페이지에 첨부된 이미지는 임시 디렉토리에 자동으로 다운로드됩니다.

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `page_id` | string | 예 | Confluence 페이지 ID |

### confluence_get_page_images

`confluence_get_page`에서 다운로드한 이미지의 로컬 파일 경로를 조회합니다. 먼저 `confluence_get_page`를 호출하세요.

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `page_id` | string | 예 | Confluence 페이지 ID |

### confluence_get_recent_updates

지정된 시간 범위 내에 업데이트된 Confluence 페이지를 조회합니다.

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `hours` | integer | 아니오 | 조회할 시간 범위 (기본값: 24, 단위: 시간) |

## 라이선스

MIT
