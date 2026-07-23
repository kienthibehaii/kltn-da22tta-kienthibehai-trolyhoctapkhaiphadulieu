# reliability/monitoring.py - Production Monitoring & Alerting
"""
Monitoring system:
- Request tracing
- Performance metrics
- Error tracking
- Quota monitoring
- Alerting
"""

import time
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class RequestTrace:
    """Request trace information"""
    request_id: str
    endpoint: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    status: str = "pending"  # pending, success, error
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    
    def add_request(self, duration: float, success: bool):
        """Add request metrics"""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        self.total_duration += duration
        self.min_duration = min(self.min_duration, duration)
        self.max_duration = max(self.max_duration, duration)
    
    def get_avg_duration(self) -> float:
        """Get average duration"""
        if self.total_requests == 0:
            return 0.0
        return self.total_duration / self.total_requests
    
    def get_success_rate(self) -> float:
        """Get success rate"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests


class RequestTracer:
    """Trace requests for monitoring"""
    
    def __init__(self, max_traces: int = 1000):
        self.traces: deque = deque(maxlen=max_traces)
        self.active_traces: Dict[str, RequestTrace] = {}
    
    def start_trace(self, request_id: str, endpoint: str, **metadata) -> RequestTrace:
        """Start tracing a request"""
        trace = RequestTrace(
            request_id=request_id,
            endpoint=endpoint,
            start_time=time.time(),
            metadata=metadata
        )
        self.active_traces[request_id] = trace
        return trace
    
    def end_trace(self, request_id: str, success: bool = True, error: Optional[str] = None):
        """End tracing a request"""
        if request_id in self.active_traces:
            trace = self.active_traces[request_id]
            trace.end_time = time.time()
            trace.duration = trace.end_time - trace.start_time
            trace.status = "success" if success else "error"
            trace.error = error
            
            self.traces.append(trace)
            del self.active_traces[request_id]
    
    def get_recent_traces(self, limit: int = 100) -> List[RequestTrace]:
        """Get recent traces"""
        return list(self.traces)[-limit:]
    
    def get_slow_requests(self, threshold: float = 5.0) -> List[RequestTrace]:
        """Get slow requests"""
        return [
            trace for trace in self.traces
            if trace.duration and trace.duration > threshold
        ]


class MetricsCollector:
    """Collect and aggregate metrics"""
    
    def __init__(self):
        self.metrics_by_endpoint: Dict[str, PerformanceMetrics] = {}
        self.metrics_by_service: Dict[str, PerformanceMetrics] = {}
        self.error_counts: Dict[str, int] = {}
        self.quota_usage: Dict[str, Dict] = {}
    
    def record_request(
        self,
        endpoint: str,
        service: str,
        duration: float,
        success: bool,
        error: Optional[str] = None
    ):
        """Record request metrics"""
        # Endpoint metrics
        if endpoint not in self.metrics_by_endpoint:
            self.metrics_by_endpoint[endpoint] = PerformanceMetrics()
        self.metrics_by_endpoint[endpoint].add_request(duration, success)
        
        # Service metrics
        if service not in self.metrics_by_service:
            self.metrics_by_service[service] = PerformanceMetrics()
        self.metrics_by_service[service].add_request(duration, success)
        
        # Error tracking
        if not success and error:
            self.error_counts[error] = self.error_counts.get(error, 0) + 1
    
    def record_quota_usage(self, service: str, used: int, limit: int):
        """Record quota usage"""
        self.quota_usage[service] = {
            "used": used,
            "limit": limit,
            "percentage": (used / limit * 100) if limit > 0 else 0,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_summary(self) -> Dict:
        """Get metrics summary"""
        summary = {
            "endpoints": {},
            "services": {},
            "errors": self.error_counts,
            "quota": self.quota_usage
        }
        
        # Endpoint summary
        for endpoint, metrics in self.metrics_by_endpoint.items():
            summary["endpoints"][endpoint] = {
                "total_requests": metrics.total_requests,
                "success_rate": f"{metrics.get_success_rate():.2%}",
                "avg_duration": f"{metrics.get_avg_duration():.2f}s",
                "min_duration": f"{metrics.min_duration:.2f}s",
                "max_duration": f"{metrics.max_duration:.2f}s"
            }
        
        # Service summary
        for service, metrics in self.metrics_by_service.items():
            summary["services"][service] = {
                "total_requests": metrics.total_requests,
                "success_rate": f"{metrics.get_success_rate():.2%}",
                "avg_duration": f"{metrics.get_avg_duration():.2f}s"
            }
        
        return summary


class AlertManager:
    """Manage alerts and notifications"""
    
    def __init__(self):
        self.alerts: List[Dict] = []
        self.alert_thresholds = {
            "error_rate": 0.1,  # 10% error rate
            "slow_request": 10.0,  # 10 seconds
            "quota_usage": 0.9,  # 90% quota used
            "circuit_breaker_open": True
        }
    
    def check_error_rate(self, metrics: PerformanceMetrics):
        """Check if error rate is too high"""
        if metrics.total_requests < 10:
            return  # Not enough data
        
        error_rate = 1 - metrics.get_success_rate()
        if error_rate > self.alert_thresholds["error_rate"]:
            self.create_alert(
                "high_error_rate",
                f"Error rate is {error_rate:.1%}",
                severity="warning"
            )
    
    def check_slow_requests(self, traces: List[RequestTrace]):
        """Check for slow requests"""
        slow_requests = [
            t for t in traces
            if t.duration and t.duration > self.alert_thresholds["slow_request"]
        ]
        
        if len(slow_requests) > 5:
            self.create_alert(
                "slow_requests",
                f"{len(slow_requests)} slow requests detected",
                severity="warning"
            )
    
    def check_quota_usage(self, quota_data: Dict):
        """Check quota usage"""
        for service, data in quota_data.items():
            if data["percentage"] > self.alert_thresholds["quota_usage"] * 100:
                self.create_alert(
                    "quota_warning",
                    f"{service} quota at {data['percentage']:.1f}%",
                    severity="critical"
                )
    
    def create_alert(self, alert_type: str, message: str, severity: str = "info"):
        """Create an alert"""
        alert = {
            "type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        }
        
        self.alerts.append(alert)
        
        # Log alert
        if severity == "critical":
            logger.error(f"🚨 ALERT: {message}")
        elif severity == "warning":
            logger.warning(f"⚠️ ALERT: {message}")
        else:
            logger.info(f"ℹ️ ALERT: {message}")
    
    def get_active_alerts(self, since_minutes: int = 60) -> List[Dict]:
        """Get recent alerts"""
        cutoff = datetime.now() - timedelta(minutes=since_minutes)
        
        return [
            alert for alert in self.alerts
            if datetime.fromisoformat(alert["timestamp"]) > cutoff
        ]


class MonitoringSystem:
    """Complete monitoring system"""
    
    def __init__(self):
        self.tracer = RequestTracer()
        self.metrics = MetricsCollector()
        self.alerts = AlertManager()
        self.start_time = datetime.now()
    
    def start_request(self, request_id: str, endpoint: str, **metadata) -> RequestTrace:
        """Start monitoring a request"""
        return self.tracer.start_trace(request_id, endpoint, **metadata)
    
    def end_request(
        self,
        request_id: str,
        endpoint: str,
        service: str,
        success: bool = True,
        error: Optional[str] = None
    ):
        """End monitoring a request"""
        self.tracer.end_trace(request_id, success, error)
        
        # Get trace for metrics
        traces = [t for t in self.tracer.traces if t.request_id == request_id]
        if traces:
            trace = traces[0]
            if trace.duration:
                self.metrics.record_request(endpoint, service, trace.duration, success, error)
    
    def record_quota(self, service: str, used: int, limit: int):
        """Record quota usage"""
        self.metrics.record_quota_usage(service, used, limit)
        
        # Check for alerts
        self.alerts.check_quota_usage(self.metrics.quota_usage)
    
    def run_health_check(self):
        """Run periodic health check"""
        # Check error rates
        for endpoint, metrics in self.metrics.metrics_by_endpoint.items():
            self.alerts.check_error_rate(metrics)
        
        # Check slow requests
        recent_traces = self.tracer.get_recent_traces(100)
        self.alerts.check_slow_requests(recent_traces)
    
    def get_dashboard(self) -> Dict:
        """Get monitoring dashboard data"""
        uptime = datetime.now() - self.start_time
        
        return {
            "uptime": str(uptime),
            "metrics": self.metrics.get_summary(),
            "recent_traces": [
                {
                    "request_id": t.request_id,
                    "endpoint": t.endpoint,
                    "duration": f"{t.duration:.2f}s" if t.duration else "N/A",
                    "status": t.status
                }
                for t in self.tracer.get_recent_traces(20)
            ],
            "slow_requests": len(self.tracer.get_slow_requests()),
            "active_alerts": self.alerts.get_active_alerts(),
            "timestamp": datetime.now().isoformat()
        }


# Global monitoring instance
monitoring = MonitoringSystem()


def trace_request(endpoint: str, service: str = "unknown"):
    """Decorator for request tracing"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            import uuid
            request_id = str(uuid.uuid4())
            
            # Start trace
            monitoring.start_request(request_id, endpoint)
            
            try:
                result = await func(*args, **kwargs)
                monitoring.end_request(request_id, endpoint, service, success=True)
                return result
            except Exception as e:
                monitoring.end_request(request_id, endpoint, service, success=False, error=str(e))
                raise
        
        def sync_wrapper(*args, **kwargs):
            import uuid
            request_id = str(uuid.uuid4())
            
            monitoring.start_request(request_id, endpoint)
            
            try:
                result = func(*args, **kwargs)
                monitoring.end_request(request_id, endpoint, service, success=True)
                return result
            except Exception as e:
                monitoring.end_request(request_id, endpoint, service, success=False, error=str(e))
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
