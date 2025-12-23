"""Configuration management for the real-time orders system."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration class."""
    
    # Database settings
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "realtime_orders")
    
    # Server settings
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
    
    # Polling settings
    CHANGE_LOG_POLL_INTERVAL: float = float(os.getenv("CHANGE_LOG_POLL_INTERVAL", "0.5"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @property
    def database_url(self) -> str:
        """Get the database connection URL."""
        return f"mysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    def validate(self) -> None:
        """Validate required configuration."""
        required_fields = ["DB_HOST", "DB_USER", "DB_NAME"]
        missing_fields = []
        
        for field in required_fields:
            if not getattr(self, field):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Missing required configuration: {', '.join(missing_fields)}")

# Global configuration instance
config = Config()