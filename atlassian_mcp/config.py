"""
Settings for Atlassian MCP Server (Pydantic BaseSettings).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Atlassian API configuration loaded from environment variables."""

    ATLASSIAN_EMAIL: str = ""
    ATLASSIAN_API_TOKEN: str = ""
    ATLASSIAN_JIRA_SITE_URL: str = ""  # e.g. https://your-domain.atlassian.net
    ATLASSIAN_CONFLUENCE_SITE_URL: str = ""  # e.g. https://your-domain.atlassian.net

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
