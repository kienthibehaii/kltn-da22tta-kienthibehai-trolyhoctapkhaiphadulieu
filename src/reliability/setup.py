# reliability/setup.py - Initialize Reliability System
"""
Setup and initialize all reliability components
"""

import logging
from .config import ReliabilityConfig
from .cache_manager import init_cache
from .api_key_manager import init_api_keys
from .rate_limiter import rate_limiter
from .monitoring import monitoring

logger = logging.getLogger(__name__)


def setup_reliability_system():
    """
    Initialize complete reliability system
    
    Returns:
        dict with all initialized components
    """
    logger.info("="*60)
    logger.info("  🚀 INITIALIZING RELIABILITY SYSTEM")
    logger.info("="*60)
    
    # 1. Initialize cache
    logger.info("\n1. Initializing cache system...")
    cache_manager = init_cache(redis_url=ReliabilityConfig.REDIS_URL)
    logger.info("✅ Cache system initialized")
    
    # 2. Initialize API key manager
    logger.info("\n2. Initializing API key manager...")
    api_key_mgr = init_api_keys()
    logger.info(f"✅ API key manager initialized with {len(api_key_mgr.keys)} keys")
    
    # 3. Rate limiter is already initialized
    logger.info("\n3. Rate limiter ready")
    logger.info("✅ Rate limiting configured")
    
    # 4. Monitoring is already initialized
    logger.info("\n4. Monitoring system ready")
    logger.info("✅ Monitoring and alerting configured")
    
    # 5. Print configuration summary
    logger.info("\n5. Configuration Summary:")
    config_summary = ReliabilityConfig.get_summary()
    for category, values in config_summary.items():
        logger.info(f"\n   {category.upper()}:")
        if isinstance(values, dict):
            for key, value in values.items():
                logger.info(f"     - {key}: {value}")
        else:
            logger.info(f"     - {values}")
    
    logger.info("\n" + "="*60)
    logger.info("  ✅ RELIABILITY SYSTEM READY")
    logger.info("="*60)
    
    return {
        "cache_manager": cache_manager,
        "api_key_manager": api_key_mgr,
        "rate_limiter": rate_limiter,
        "monitoring": monitoring,
        "config": ReliabilityConfig
    }


def get_system_status():
    """Get current system status"""
    from .api_key_manager import api_key_manager
    from .cache_manager import cache_manager
    
    status = {
        "api_keys": api_key_manager.get_status() if api_key_manager else {},
        "rate_limiter": rate_limiter.get_status(),
        "cache": cache_manager.get_stats() if cache_manager else {},
        "monitoring": monitoring.get_dashboard(),
        "config": ReliabilityConfig.get_summary()
    }
    
    return status


# Auto-setup on import (optional)
# Uncomment to auto-initialize
# reliability_system = setup_reliability_system()
