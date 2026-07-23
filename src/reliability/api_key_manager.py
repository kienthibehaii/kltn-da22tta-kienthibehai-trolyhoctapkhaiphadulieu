# reliability/api_key_manager.py - API Key Rotation & Management
"""
Production API key management:
- Multiple API keys rotation
- Quota tracking per key
- Automatic failover
- Health monitoring
"""

import os
import time
from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class APIKeyInfo:
    """API key information"""
    key: str
    name: str
    quota_per_day: int
    quota_per_minute: int
    requests_today: int = 0
    requests_this_minute: int = 0
    last_reset_day: Optional[datetime] = None
    last_reset_minute: Optional[datetime] = None
    failures: int = 0
    is_healthy: bool = True
    last_used: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None


class APIKeyManager:
    """Manage multiple API keys with rotation"""
    
    def __init__(self):
        self.keys: List[APIKeyInfo] = []
        self.current_index = 0
        self.fallback_models = [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-flash-latest",
        ]
    
    def add_key(
        self,
        key: str,
        name: str,
        quota_per_day: int = 1500,
        quota_per_minute: int = 15
    ):
        """Add API key"""
        key_info = APIKeyInfo(
            key=key,
            name=name,
            quota_per_day=quota_per_day,
            quota_per_minute=quota_per_minute,
            last_reset_day=datetime.now(),
            last_reset_minute=datetime.now()
        )
        self.keys.append(key_info)
        logger.info(f"Added API key: {name}")
    
    def load_from_env(self):
        """Load API keys from environment"""
        # Load from GEMINI_API_KEY (single key)
        single_key = os.getenv("GEMINI_API_KEY")
        if single_key and single_key not in [k.key for k in self.keys]:
            self.add_key(single_key, "gemini_key_1", quota_per_day=1500, quota_per_minute=15)

        # Load from GEMINI_API_KEYS (comma-separated list, legacy)
        gemini_keys_env = os.getenv("GEMINI_API_KEYS")
        if gemini_keys_env:
            raw_keys = [k.strip() for k in gemini_keys_env.replace(';', ',').split(',') if k.strip()]
            for idx, key in enumerate(raw_keys, 1):
                if key not in [k.key for k in self.keys]:
                    self.add_key(key, f"gemini_key_{idx}", quota_per_day=1500, quota_per_minute=15)

        # Primary key
        primary_key = os.getenv("GOOGLE_API_KEY")
        if primary_key and primary_key not in [k.key for k in self.keys]:
            self.add_key(primary_key, "primary", quota_per_day=1500, quota_per_minute=15)
        
        # Backup keys
        for i in range(1, 6):
            backup_key = os.getenv(f"GOOGLE_API_KEY_BACKUP_{i}")
            if backup_key and backup_key not in [k.key for k in self.keys]:
                self.add_key(backup_key, f"backup_{i}", quota_per_day=1500, quota_per_minute=15)
        
        if not self.keys:
            logger.error("No API keys found in environment!")
    
    def _reset_quotas(self, key_info: APIKeyInfo):
        """Reset quotas if needed"""
        now = datetime.now()
        
        # Check if cooldown has expired
        if getattr(key_info, 'cooldown_until', None) and now >= key_info.cooldown_until:
            key_info.is_healthy = True
            key_info.failures = 0
            key_info.cooldown_until = None
            logger.info(f"Cooldown expired for API key {key_info.name}. Restored to healthy.")
            
        # Reset daily quota
        if key_info.last_reset_day:
            if (now - key_info.last_reset_day) >= timedelta(days=1):
                key_info.requests_today = 0
                key_info.last_reset_day = now
                key_info.is_healthy = True
                key_info.failures = 0
                key_info.cooldown_until = None
                logger.info(f"Reset daily quota for {key_info.name}")
        
        # Reset minute quota
        if key_info.last_reset_minute:
            if (now - key_info.last_reset_minute) >= timedelta(minutes=1):
                key_info.requests_this_minute = 0
                key_info.last_reset_minute = now
                # If marked unhealthy due to a quota error, restore to healthy when the minute resets
                # unless daily quota is also exceeded
                if not key_info.is_healthy and key_info.requests_today < key_info.quota_per_day:
                    if key_info.failures < 3: # Keep blocked if there were multiple hard failures
                        key_info.is_healthy = True
                        key_info.cooldown_until = None
                        logger.info(f"Restored API key {key_info.name} health after minute quota reset.")
    
    def get_available_key(self) -> Optional[APIKeyInfo]:
        """Get available API key with quota"""
        if not self.keys:
            return None
        
        # Try all keys starting from current
        for _ in range(len(self.keys)):
            key_info = self.keys[self.current_index]
            
            # Reset quotas if needed
            self._reset_quotas(key_info)
            
            # Check if key is healthy and has quota
            if (
                key_info.is_healthy and
                key_info.requests_today < key_info.quota_per_day and
                key_info.requests_this_minute < key_info.quota_per_minute
            ):
                return key_info
            
            # Try next key
            self.current_index = (self.current_index + 1) % len(self.keys)
        
        logger.warning("No available API keys with quota!")
        return None
    
    def record_request(self, key_info: APIKeyInfo, success: bool = True):
        """Record API request"""
        key_info.requests_today += 1
        key_info.requests_this_minute += 1
        key_info.last_used = datetime.now()
        
        if not success:
            key_info.failures += 1
            
            # Mark as unhealthy after 5 consecutive failures
            if key_info.failures >= 5:
                key_info.is_healthy = False
                key_info.cooldown_until = datetime.now() + timedelta(minutes=5)
                logger.error(f"API key {key_info.name} marked as unhealthy (5m cooldown)")
        else:
            # Reset failure count on success
            key_info.failures = 0
            key_info.is_healthy = True
            key_info.cooldown_until = None

    def record_key_failure(self, key: str, is_quota_error: bool = False, is_overloaded: bool = False):
        """Record failure for a specific key"""
        for key_info in self.keys:
            if key_info.key == key:
                key_info.last_used = datetime.now()
                if is_overloaded:
                    # 503 server overload — tạm thời, KHÔNG mark unhealthy, chỉ log
                    logger.warning(f"API key {key_info.name} got server overload (503). Will retry with next model.")
                elif is_quota_error:
                    key_info.failures += 1
                    key_info.is_healthy = False
                    key_info.cooldown_until = datetime.now() + timedelta(minutes=1)
                    logger.warning(f"API key {key_info.name} hit quota limit. Marked as unhealthy (1m cooldown).")
                else:
                    key_info.failures += 1
                    if key_info.failures >= 5:
                        key_info.is_healthy = False
                        key_info.cooldown_until = datetime.now() + timedelta(minutes=5)
                        logger.error(f"API key {key_info.name} marked as unhealthy after {key_info.failures} consecutive failures (5m cooldown)")
                break

    def record_key_success(self, key: str):
        """Record success for a specific key"""
        for key_info in self.keys:
            if key_info.key == key:
                key_info.failures = 0
                key_info.is_healthy = True
                key_info.cooldown_until = None
                key_info.requests_today += 1
                key_info.requests_this_minute += 1
                key_info.last_used = datetime.now()
                break
    
    def get_next_model(self, current_model: str) -> Optional[str]:
        """Get next fallback model"""
        try:
            current_index = self.fallback_models.index(current_model)
            if current_index < len(self.fallback_models) - 1:
                return self.fallback_models[current_index + 1]
        except ValueError:
            pass
        
        return None
    
    def get_status(self) -> Dict:
        """Get status of all keys"""
        status = {
            "total_keys": len(self.keys),
            "healthy_keys": sum(1 for k in self.keys if k.is_healthy),
            "keys": []
        }
        
        for key_info in self.keys:
            self._reset_quotas(key_info)
            
            key_status = {
                "name": key_info.name,
                "is_healthy": key_info.is_healthy,
                "requests_today": key_info.requests_today,
                "quota_remaining_today": key_info.quota_per_day - key_info.requests_today,
                "requests_this_minute": key_info.requests_this_minute,
                "quota_remaining_minute": key_info.quota_per_minute - key_info.requests_this_minute,
                "failures": key_info.failures,
                "last_used": key_info.last_used.isoformat() if key_info.last_used else None
            }
            status["keys"].append(key_status)
        
        return status


class FallbackModelManager:
    """Manage fallback between different models"""
    
    def __init__(self, api_key_manager: APIKeyManager):
        self.api_key_manager = api_key_manager
        self.model_preferences = {
            "fast": ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-flash-latest"],
            "accurate": ["gemini-2.5-flash", "gemini-2.5-pro"],
            "translation": ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
        }
    
    def get_model_for_task(self, task: str = "fast") -> tuple[Optional[str], Optional[str]]:
        """
        Get best available model and API key for task
        
        Returns:
            (model_name, api_key)
        """
        models = self.model_preferences.get(task, self.model_preferences["fast"])
        
        for model in models:
            # Get available API key
            key_info = self.api_key_manager.get_available_key()
            if key_info:
                return model, key_info.key
        
        logger.error(f"No available model/key for task: {task}")
        return None, None
    
    async def call_with_fallback(
        self,
        func,
        task: str = "fast",
        *args,
        **kwargs
    ):
        """Call function with automatic model fallback"""
        models = self.model_preferences.get(task, self.model_preferences["fast"])
        last_error = None
        
        for model in models:
            key_info = self.api_key_manager.get_available_key()
            if not key_info:
                continue
            
            try:
                logger.info(f"Trying model: {model} with key: {key_info.name}")
                
                # Call function with model and key
                result = await func(model, key_info.key, *args, **kwargs)
                
                # Record success
                self.api_key_manager.record_request(key_info, success=True)
                
                return result
            
            except Exception as e:
                last_error = e
                logger.warning(f"Model {model} failed: {e}")
                
                # Record failure
                self.api_key_manager.record_request(key_info, success=False)
                
                # Continue to next model
                continue
        
        # All models failed
        if last_error:
            raise last_error
        else:
            raise Exception("No available models or API keys")


# Global instances
api_key_manager = APIKeyManager()
fallback_manager = None


def init_api_keys():
    """Initialize API key manager"""
    global fallback_manager
    
    # Clear existing to prevent duplicate loading if called multiple times
    api_key_manager.keys = []
    api_key_manager.load_from_env()
    fallback_manager = FallbackModelManager(api_key_manager)
    
    logger.info(f"Initialized with {len(api_key_manager.keys)} API keys")
    return api_key_manager


def get_api_key() -> Optional[str]:
    """Get available API key"""
    key_info = api_key_manager.get_available_key()
    return key_info.key if key_info else None


def get_model_and_key(task: str = "fast") -> tuple[Optional[str], Optional[str]]:
    """Get model and API key for task"""
    if fallback_manager:
        return fallback_manager.get_model_for_task(task)
    return None, None


# Auto-initialize on module load
try:
    init_api_keys()
except Exception as e:
    logger.error(f"Error auto-initializing api keys: {e}")
