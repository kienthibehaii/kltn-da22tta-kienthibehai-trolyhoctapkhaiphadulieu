# reliability/config.py - Reliability Configuration
"""
Configuration for production reliability system
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class ReliabilityConfig:
    """Reliability system configuration"""
    
    # Redis Configuration
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", None)
    REDIS_ENABLED: bool = REDIS_URL is not None
    
    # Cache Configuration
    MEMORY_CACHE_SIZE: int = 1000
    TRANSLATION_CACHE_TTL: int = 86400  # 24 hours
    EMBEDDING_CACHE_TTL: int = 604800   # 7 days
    RESPONSE_CACHE_TTL: int = 3600      # 1 hour
    
    # Rate Limiting
    GEMINI_FLASH_RPM: int = 15  # Requests per minute
    GEMINI_FLASH_RPD: int = 1500  # Requests per day
    GEMINI_PRO_RPM: int = 2
    GEMINI_PRO_RPD: int = 50
    TRANSLATION_RPM: int = 10
    
    # Circuit Breaker
    CIRCUIT_BREAKER_THRESHOLD: int = 5
    CIRCUIT_BREAKER_TIMEOUT: int = 60  # seconds
    
    # Retry Configuration
    MAX_RETRY_ATTEMPTS: int = 3
    INITIAL_RETRY_DELAY: float = 1.0
    MAX_RETRY_DELAY: float = 60.0
    RETRY_EXPONENTIAL_BASE: float = 2.0
    
    # Timeout Configuration
    TRANSLATION_TIMEOUT: int = 30  # seconds
    RETRIEVAL_TIMEOUT: int = 10
    GENERATION_TIMEOUT: int = 60
    TOTAL_REQUEST_TIMEOUT: int = 180
    
    # API Keys
    PRIMARY_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    BACKUP_API_KEYS: list = [
        os.getenv(f"GOOGLE_API_KEY_BACKUP_{i}")
        for i in range(1, 6)
        if os.getenv(f"GOOGLE_API_KEY_BACKUP_{i}")
    ]
    
    # Monitoring
    ENABLE_MONITORING: bool = True
    MAX_TRACES: int = 1000
    SLOW_REQUEST_THRESHOLD: float = 10.0  # seconds
    
    # Alerting
    ERROR_RATE_THRESHOLD: float = 0.1  # 10%
    QUOTA_WARNING_THRESHOLD: float = 0.9  # 90%
    
    # Graceful Degradation
    ENABLE_FALLBACK: bool = True
    ENABLE_SEARCH_ONLY_MODE: bool = True
    ENABLE_CACHED_RESPONSES: bool = True
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.PRIMARY_API_KEY:
            raise ValueError("GOOGLE_API_KEY is required")
        
        if cls.REDIS_ENABLED:
            print(f"✅ Redis enabled: {cls.REDIS_URL}")
        else:
            print("⚠️ Redis disabled, using in-memory cache only")
        
        print(f"✅ Primary API key configured")
        print(f"✅ {len(cls.BACKUP_API_KEYS)} backup API keys configured")
    
    @classmethod
    def get_summary(cls) -> dict:
        """Get configuration summary"""
        return {
            "redis_enabled": cls.REDIS_ENABLED,
            "cache_sizes": {
                "memory": cls.MEMORY_CACHE_SIZE,
                "translation_ttl": cls.TRANSLATION_CACHE_TTL,
                "response_ttl": cls.RESPONSE_CACHE_TTL
            },
            "rate_limits": {
                "gemini_flash_rpm": cls.GEMINI_FLASH_RPM,
                "gemini_flash_rpd": cls.GEMINI_FLASH_RPD,
                "translation_rpm": cls.TRANSLATION_RPM
            },
            "timeouts": {
                "translation": cls.TRANSLATION_TIMEOUT,
                "retrieval": cls.RETRIEVAL_TIMEOUT,
                "generation": cls.GENERATION_TIMEOUT,
                "total": cls.TOTAL_REQUEST_TIMEOUT
            },
            "api_keys": {
                "primary": "configured" if cls.PRIMARY_API_KEY else "missing",
                "backups": len(cls.BACKUP_API_KEYS)
            },
            "features": {
                "monitoring": cls.ENABLE_MONITORING,
                "fallback": cls.ENABLE_FALLBACK,
                "search_only": cls.ENABLE_SEARCH_ONLY_MODE,
                "caching": cls.ENABLE_CACHED_RESPONSES
            }
        }


# Validate on import
try:
    ReliabilityConfig.validate()
except Exception as e:
    print(f"⚠️ Configuration validation failed: {e}")
