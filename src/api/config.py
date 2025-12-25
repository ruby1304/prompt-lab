"""
API Configuration

This module manages configuration settings for the API layer.
Configuration can be loaded from environment variables or config files.
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
from pathlib import Path


class APISettings(BaseSettings):
    """
    API configuration settings.
    
    Settings can be overridden via environment variables with the prefix API_.
    For example: API_HOST=0.0.0.0 API_PORT=8080
    """
    
    # Server settings
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False  # Auto-reload on code changes (development only)
    workers: int = 1  # Number of worker processes
    
    # CORS settings
    cors_origins: List[str] = ["*"]  # Allowed origins for CORS
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    # API settings
    api_prefix: str = "/api/v1"  # API route prefix
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"
    
    # Workspace settings
    workspace_root: Optional[Path] = None
    agents_dir: Optional[Path] = None
    pipelines_dir: Optional[Path] = None
    data_dir: Optional[Path] = None
    config_dir: Optional[Path] = None
    
    # Logging
    log_level: str = "INFO"
    
    # Rate limiting (future)
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds
    
    # Authentication (future)
    auth_enabled: bool = False
    auth_secret_key: Optional[str] = None
    
    class Config:
        env_prefix = "API_"
        case_sensitive = False


# Global settings instance
settings = APISettings()


def get_settings() -> APISettings:
    """
    Get the API settings instance.
    
    Returns:
        APISettings: The API settings
    """
    return settings
