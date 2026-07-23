# enterprise/src/core/config.py - Enterprise Configuration Management
"""
Centralized configuration management for enterprise RAG system

Features:
- Environment-based configuration
- Validation with Pydantic
- Secret management
- Multi-environment support
"""

from typing import Optional, List
from pydantic import BaseSettings, Field, validator
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings with validation"""
    
    # Application
    APP_NAME: str = "Enterprise RAG System"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # API
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8501"]
    
    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database - MongoDB
    MONGODB_URL: str = Field(..., env="MONGODB_URL")
    MONGODB_DB_NAME: str = Field(default="rag_enterprise", env="MONGODB_DB_NAME")
    MONGODB_MAX_POOL_SIZE: int = 100
    MONGODB_MIN_POOL_SIZE: int = 10
    
    # Database - PostgreSQL (for analytics)
    POSTGRES_URL: Optional[str] = Field(None, env="POSTGRES_URL")
    POSTGRES_POOL_SIZE: int = 20
    
    # Vector Database - ChromaDB
    CHROMA_HOST: str = Field(default="localhost", env="CHROMA_HOST")
    CHROMA_PORT: int = Field(default=8000, env="CHROMA_PORT")
    CHROMA_COLLECTION: str = "rag_documents"
    
    # Vector Database - Qdrant (alternative)
    QDRANT_URL: Optional[str] = Field(None, env="QDRANT_URL")
    QDRANT_API_KEY: Optional[str] = Field(None, env="QDRANT_API_KEY")
    QDRANT_COLLECTION: str = "rag_documents"
    
    # Cache - Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
    
    # Cache - Memcached
    MEMCACHED_SERVERS: List[str] = ["localhost:11211"]
    
    # Queue - Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    
    # Queue - RabbitMQ (alternative)
    RABBITMQ_URL: Optional[str] = Field(None, env="RABBITMQ_URL")
    
    # Storage - S3/MinIO
    S3_ENDPOINT: Optional[str] = Field(None, env="S3_ENDPOINT")
    S3_ACCESS_KEY: Optional[str] = Field(None, env="S3_ACCESS_KEY")
    S3_SECRET_KEY: Optional[str] = Field(None, env="S3_SECRET_KEY")
    S3_BUCKET: str = "rag-documents"
    S3_REGION: str = "us-east-1"
    
    # Storage - Local
    LOCAL_STORAGE_PATH: str = "./storage"
    UPLOAD_MAX_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # AI Models - Gemini
    GEMINI_API_KEY: str = Field(..., env="GEMINI_API_KEY")
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TEMPERATURE: float = 0.1
    GEMINI_MAX_TOKENS: int = 2048
    
    # AI Models - HuggingFace
    HF_API_KEY: Optional[str] = Field(None, env="HF_API_KEY")
    HF_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    HF_RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # RAG Configuration
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K_RETRIEVAL: int = 20
    TOP_K_RERANK: int = 5
    SIMILARITY_THRESHOLD: float = 0.7
    
    # Performance
    MAX_WORKERS: int = 4
    BATCH_SIZE: int = 32
    CACHE_TTL: int = 3600  # 1 hour
    ENABLE_ASYNC: bool = True
    ENABLE_LAZY_LOADING: bool = True
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    RATE_LIMIT_PER_DAY: int = 10000
    
    # Monitoring - Prometheus
    PROMETHEUS_PORT: int = 9090
    ENABLE_METRICS: bool = True
    
    # Monitoring - Grafana
    GRAFANA_URL: Optional[str] = Field(None, env="GRAFANA_URL")
    GRAFANA_API_KEY: Optional[str] = Field(None, env="GRAFANA_API_KEY")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = "json"  # json or text
    LOG_FILE: Optional[str] = "./logs/app.log"
    
    # Feature Flags
    ENABLE_MULTI_QUERY: bool = True
    ENABLE_QUERY_EXPANSION: bool = True
    ENABLE_CONTEXTUAL_COMPRESSION: bool = True
    ENABLE_STREAMING: bool = True
    ENABLE_EXPORT: bool = True
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v.upper()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


class DevelopmentSettings(Settings):
    """Development environment settings"""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    ENABLE_METRICS: bool = False


class StagingSettings(Settings):
    """Staging environment settings"""
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ENABLE_METRICS: bool = True


class ProductionSettings(Settings):
    """Production environment settings"""
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    ENABLE_METRICS: bool = True
    CORS_ORIGINS: List[str] = []  # Must be explicitly set


@lru_cache()
def get_settings() -> Settings:
    """
    Get settings based on environment
    Cached for performance
    """
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        return ProductionSettings()
    elif env == "staging":
        return StagingSettings()
    else:
        return DevelopmentSettings()


# Global settings instance
settings = get_settings()


# Export
__all__ = ["settings", "get_settings", "Settings"]
