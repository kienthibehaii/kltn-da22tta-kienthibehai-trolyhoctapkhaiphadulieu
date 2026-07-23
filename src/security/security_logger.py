# security/security_logger.py - Security Event Logging
"""
Security Logging System

Features:
- Security event logging
- Suspicious activity detection
- Audit trail
- Log rotation
- Alert system
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum
from pathlib import Path


class SecurityEventType(Enum):
    """Security event types"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    REGISTRATION = "registration"
    PASSWORD_CHANGE = "password_change"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    API_KEY_USED = "api_key_used"
    ENCRYPTION_ERROR = "encryption_error"
    AUTHENTICATION_ERROR = "authentication_error"


class SecurityLogger:
    """
    Security event logger with suspicious activity detection.
    """
    
    def __init__(self, log_dir: str = "logs/security"):
        """
        Initialize security logger.
        
        Args:
            log_dir: Directory for log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = self._setup_logger()
        
        # Suspicious activity tracking
        self.suspicious_events: List[Dict] = []
        self.alert_threshold = 5  # Number of suspicious events before alert
        
        print(f"✅ Security Logger initialized")
        print(f"   Log directory: {self.log_dir}")
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('security')
        logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        logger.handlers = []
        
        # File handler with rotation
        log_file = self.log_dir / f"security_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def log_event(self,
                  event_type: SecurityEventType,
                  user_id: Optional[str] = None,
                  username: Optional[str] = None,
                  ip_address: Optional[str] = None,
                  details: Optional[Dict] = None,
                  severity: str = "INFO"):
        """
        Log security event.
        
        Args:
            event_type: Type of security event
            user_id: User ID
            username: Username
            ip_address: IP address
            details: Additional details
            severity: Log severity (INFO, WARNING, ERROR, CRITICAL)
        """
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type.value,
            'user_id': user_id,
            'username': username,
            'ip_address': ip_address,
            'details': details or {},
            'severity': severity
        }
        
        # Log to file
        log_message = json.dumps(event)
        
        if severity == "INFO":
            self.logger.info(log_message)
        elif severity == "WARNING":
            self.logger.warning(log_message)
        elif severity == "ERROR":
            self.logger.error(log_message)
        elif severity == "CRITICAL":
            self.logger.critical(log_message)
        
        # Check for suspicious activity
        if self._is_suspicious(event):
            self._handle_suspicious_activity(event)
    
    def log_login_success(self, username: str, user_id: str, ip_address: Optional[str] = None):
        """Log successful login"""
        self.log_event(
            SecurityEventType.LOGIN_SUCCESS,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            severity="INFO"
        )
    
    def log_login_failed(self, username: str, ip_address: Optional[str] = None, reason: str = ""):
        """Log failed login attempt"""
        self.log_event(
            SecurityEventType.LOGIN_FAILED,
            username=username,
            ip_address=ip_address,
            details={'reason': reason},
            severity="WARNING"
        )
    
    def log_logout(self, username: str, user_id: str):
        """Log logout"""
        self.log_event(
            SecurityEventType.LOGOUT,
            user_id=user_id,
            username=username,
            severity="INFO"
        )
    
    def log_registration(self, username: str, email: str, ip_address: Optional[str] = None):
        """Log user registration"""
        self.log_event(
            SecurityEventType.REGISTRATION,
            username=username,
            ip_address=ip_address,
            details={'email': email},
            severity="INFO"
        )
    
    def log_password_change(self, username: str, user_id: str):
        """Log password change"""
        self.log_event(
            SecurityEventType.PASSWORD_CHANGE,
            user_id=user_id,
            username=username,
            severity="INFO"
        )
    
    def log_unauthorized_access(self, username: Optional[str] = None, 
                               resource: str = "", 
                               ip_address: Optional[str] = None):
        """Log unauthorized access attempt"""
        self.log_event(
            SecurityEventType.UNAUTHORIZED_ACCESS,
            username=username,
            ip_address=ip_address,
            details={'resource': resource},
            severity="WARNING"
        )
    
    def log_rate_limit_exceeded(self, client_id: str, limit_type: str):
        """Log rate limit exceeded"""
        self.log_event(
            SecurityEventType.RATE_LIMIT_EXCEEDED,
            details={'client_id': client_id, 'limit_type': limit_type},
            severity="WARNING"
        )
    
    def log_data_access(self, username: str, user_id: str, resource: str):
        """Log data access"""
        self.log_event(
            SecurityEventType.DATA_ACCESS,
            user_id=user_id,
            username=username,
            details={'resource': resource},
            severity="INFO"
        )
    
    def log_data_modification(self, username: str, user_id: str, 
                             resource: str, action: str):
        """Log data modification"""
        self.log_event(
            SecurityEventType.DATA_MODIFICATION,
            user_id=user_id,
            username=username,
            details={'resource': resource, 'action': action},
            severity="INFO"
        )
    
    def log_api_key_used(self, api_key_id: str, endpoint: str):
        """Log API key usage"""
        self.log_event(
            SecurityEventType.API_KEY_USED,
            details={'api_key_id': api_key_id, 'endpoint': endpoint},
            severity="INFO"
        )
    
    def log_encryption_error(self, error: str, context: str = ""):
        """Log encryption error"""
        self.log_event(
            SecurityEventType.ENCRYPTION_ERROR,
            details={'error': error, 'context': context},
            severity="ERROR"
        )
    
    def log_authentication_error(self, error: str, username: Optional[str] = None):
        """Log authentication error"""
        self.log_event(
            SecurityEventType.AUTHENTICATION_ERROR,
            username=username,
            details={'error': error},
            severity="ERROR"
        )
    
    def _is_suspicious(self, event: Dict) -> bool:
        """
        Detect suspicious activity.
        
        Suspicious patterns:
        - Multiple failed login attempts
        - Unauthorized access attempts
        - Rate limit exceeded
        - Unusual access patterns
        """
        event_type = event['event_type']
        
        suspicious_types = [
            SecurityEventType.LOGIN_FAILED.value,
            SecurityEventType.UNAUTHORIZED_ACCESS.value,
            SecurityEventType.RATE_LIMIT_EXCEEDED.value
        ]
        
        return event_type in suspicious_types
    
    def _handle_suspicious_activity(self, event: Dict):
        """Handle suspicious activity"""
        self.suspicious_events.append(event)
        
        # Check if threshold exceeded
        if len(self.suspicious_events) >= self.alert_threshold:
            self._trigger_alert()
    
    def _trigger_alert(self):
        """Trigger security alert"""
        alert_message = f"⚠️ SECURITY ALERT: {len(self.suspicious_events)} suspicious events detected"
        
        self.logger.critical(alert_message)
        
        # Log suspicious events
        for event in self.suspicious_events:
            self.logger.critical(f"Suspicious event: {json.dumps(event)}")
        
        # Clear suspicious events
        self.suspicious_events = []
        
        # In production, send alert via email/SMS/Slack
        print(f"\n{alert_message}\n")
    
    def get_recent_events(self, limit: int = 100, 
                         event_type: Optional[SecurityEventType] = None) -> List[Dict]:
        """
        Get recent security events.
        
        Args:
            limit: Maximum number of events
            event_type: Filter by event type
        
        Returns:
            List of events
        """
        events = []
        
        # Read from today's log file
        log_file = self.log_dir / f"security_{datetime.now().strftime('%Y%m%d')}.log"
        
        if not log_file.exists():
            return events
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        # Parse log line
                        parts = line.split(' - ')
                        if len(parts) >= 4:
                            event_json = ' - '.join(parts[3:])
                            event = json.loads(event_json)
                            
                            # Filter by event type
                            if event_type is None or event['event_type'] == event_type.value:
                                events.append(event)
                    except:
                        continue
            
            # Return most recent events
            return events[-limit:]
        
        except Exception as e:
            self.logger.error(f"Error reading events: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get security statistics"""
        events = self.get_recent_events(limit=1000)
        
        stats = {
            'total_events': len(events),
            'by_type': {},
            'by_severity': {},
            'suspicious_events': len(self.suspicious_events)
        }
        
        for event in events:
            event_type = event['event_type']
            severity = event['severity']
            
            stats['by_type'][event_type] = stats['by_type'].get(event_type, 0) + 1
            stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1
        
        return stats


# Test code
if __name__ == "__main__":
    print("="*60)
    print("TESTING SECURITY LOGGER")
    print("="*60)
    
    logger = SecurityLogger()
    
    # Test various events
    print("\n# Test Logging Events")
    
    logger.log_login_success("testuser", "user123", "192.168.1.1")
    logger.log_login_failed("baduser", "192.168.1.2", "Invalid password")
    logger.log_registration("newuser", "new@example.com", "192.168.1.3")
    logger.log_unauthorized_access("testuser", "/admin", "192.168.1.1")
    logger.log_rate_limit_exceeded("client123", "per_minute")
    
    # Test suspicious activity detection
    print("\n# Test Suspicious Activity Detection")
    for i in range(6):
        logger.log_login_failed(f"attacker{i}", "192.168.1.100", "Brute force attempt")
    
    # Test stats
    print("\n# Security Statistics")
    stats = logger.get_stats()
    print(f"Total events: {stats['total_events']}")
    print(f"By type: {stats['by_type']}")
    print(f"By severity: {stats['by_severity']}")
    print(f"Suspicious events: {stats['suspicious_events']}")
    
    # Test recent events
    print("\n# Recent Failed Login Events")
    failed_logins = logger.get_recent_events(limit=5, event_type=SecurityEventType.LOGIN_FAILED)
    for event in failed_logins:
        print(f"  {event['timestamp']}: {event['username']} - {event['details'].get('reason', 'N/A')}")
