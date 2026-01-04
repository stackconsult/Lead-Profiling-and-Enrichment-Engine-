"""
Production-ready configuration management.
Validates required environment variables and provides configuration access.
"""
from __future__ import annotations

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class AppConfig:
    """Application configuration with validation"""
    
    # Environment
    env: str
    python_env: str
    is_production: bool
    is_development: bool
    
    # API
    api_token: str
    host: str
    port: int
    
    # Valkey/Redis
    valkey_host: str
    valkey_port: int
    valkey_url: Optional[str]
    
    # Render-specific
    render_service_id: Optional[str]
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Load configuration from environment variables"""
        
        # Environment detection
        env = os.getenv("ENV", "development")
        python_env = os.getenv("PYTHON_ENV", "development")
        render_service_id = os.getenv("RENDER_SERVICE_ID")
        
        is_production = (
            render_service_id or
            env == "production" or
            python_env == "production"
        )
        
        is_development = not is_production
        
        # Validate required variables
        api_token = os.getenv("API_TOKEN")
        if not api_token:
            raise ValueError("CRITICAL: API_TOKEN environment variable is required")
        
        # API Configuration
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8000"))
        
        # Valkey Configuration
        valkey_host = os.getenv("VALKEY_HOST", "localhost")
        valkey_port = int(os.getenv("VALKEY_PORT", "6379"))
        valkey_url = os.getenv("VALKEY_URL")
        
        if is_production and not valkey_url and (valkey_host == "localhost" or valkey_host == "127.0.0.1"):
            raise ValueError(
                "CRITICAL: In production, VALKEY_URL must be set to a real Redis/Valkey instance, "
                "not localhost. Current: VALKEY_HOST=localhost"
            )
        
        return cls(
            env=env,
            python_env=python_env,
            is_production=is_production,
            is_development=is_development,
            api_token=api_token,
            host=host,
            port=port,
            valkey_host=valkey_host,
            valkey_port=valkey_port,
            valkey_url=valkey_url,
            render_service_id=render_service_id
        )
    
    def validate_for_startup(self) -> None:
        """Validate configuration for application startup"""
        if self.is_production:
            if not self.valkey_url and (self.valkey_host in ["localhost", "127.0.0.1"]):
                raise ValueError(
                    "CRITICAL: Production startup requires real Valkey/Redis instance. "
                    f"Current: {self.valkey_host}:{self.valkey_port}"
                )
            
            if self.api_token == "your-api-token-here" or self.api_token == "test-token-123":
                raise ValueError(
                    "CRITICAL: Production startup requires real API token. "
                    "Current token appears to be a placeholder."
                )


# Global configuration instance
config = AppConfig.from_env()
