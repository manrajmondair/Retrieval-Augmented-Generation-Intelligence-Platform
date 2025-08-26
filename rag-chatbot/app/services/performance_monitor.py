import time
import asyncio
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from enum import Enum
import json
import statistics
import redis.asyncio as redis
from app.core.config import settings


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning" 
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """Individual performance metric."""
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str]
    alert_level: Optional[AlertLevel] = None


@dataclass
class PerformanceAlert:
    """Performance alert."""
    metric_name: str
    current_value: float
    threshold: float
    level: AlertLevel
    timestamp: float
    message: str


class PerformanceMonitor:
    """Real-time performance monitoring and alerting system."""
    
    def __init__(self):
        # Metric storage (circular buffers for memory efficiency)
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.alerts: deque = deque(maxlen=100)
        
        # Performance thresholds
        self.thresholds = {
            'query_latency_ms': {'warning': 100, 'critical': 300},
            'retrieval_latency_ms': {'warning': 50, 'critical': 150},
            'llm_latency_ms': {'warning': 200, 'critical': 500},
            'cache_hit_rate': {'warning': 50, 'critical': 30},  # Lower is worse
            'error_rate': {'warning': 0.05, 'critical': 0.10},  # 5% and 10%
            'concurrent_requests': {'warning': 50, 'critical': 100},
            'memory_usage_mb': {'warning': 1000, 'critical': 2000},
            'redis_connection_errors': {'warning': 5, 'critical': 10}
        }
        
        # Real-time counters
        self.request_counters = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'concurrent_requests': 0
        }
        
        # Time windows for calculating rates
        self.time_windows = {
            '1m': deque(maxlen=60),    # 1 second resolution for 1 minute
            '5m': deque(maxlen=300),   # 1 second resolution for 5 minutes 
            '1h': deque(maxlen=3600)   # 1 second resolution for 1 hour
        }
        
        # Redis client for persistent metrics
        self.redis_client: Optional[redis.Redis] = None
        
        # Alert tracking
        self.alert_counts = defaultdict(int)
        self.last_alert_times = {}
        self.alert_suppression_seconds = 300  # 5 minutes
        
        # Start background monitoring
        asyncio.create_task(self._init_redis())
        asyncio.create_task(self._background_monitor())
    
    async def _init_redis(self):
        """Initialize Redis connection for metric persistence."""
        try:
            self.redis_client = redis.from_url(settings.redis_url)
            await self.redis_client.ping()
        except Exception as e:
            print(f"Performance monitor Redis connection failed: {e}")
            self.redis_client = None
    
    async def record_metric(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Record a performance metric."""
        labels = labels or {}
        timestamp = time.time()
        
        metric = PerformanceMetric(
            name=name,
            value=value,
            timestamp=timestamp,
            labels=labels
        )
        
        # Store in memory
        self.metrics[name].append(metric)
        
        # Add to time windows
        for window in self.time_windows.values():
            window.append((timestamp, name, value))
        
        # Check for alerts
        alert = self._check_threshold(name, value, timestamp)
        if alert:
            self.alerts.append(alert)
            await self._handle_alert(alert)
        
        # Persist to Redis (fire and forget)
        if self.redis_client:
            asyncio.create_task(self._persist_metric(metric))
    
    def _check_threshold(self, metric_name: str, value: float, timestamp: float) -> Optional[PerformanceAlert]:
        """Check if metric value violates thresholds."""
        if metric_name not in self.thresholds:
            return None
        
        thresholds = self.thresholds[metric_name]
        alert_level = None
        threshold = None
        
        # Special handling for cache hit rate (lower is worse)
        if metric_name == 'cache_hit_rate':
            if value < thresholds['critical']:
                alert_level = AlertLevel.CRITICAL
                threshold = thresholds['critical']
            elif value < thresholds['warning']:
                alert_level = AlertLevel.WARNING
                threshold = thresholds['warning']
        else:
            # Higher is worse for most metrics
            if value > thresholds['critical']:
                alert_level = AlertLevel.CRITICAL
                threshold = thresholds['critical']
            elif value > thresholds['warning']:
                alert_level = AlertLevel.WARNING
                threshold = thresholds['warning']
        
        if alert_level:
            # Check alert suppression
            alert_key = f"{metric_name}:{alert_level.value}"
            last_alert = self.last_alert_times.get(alert_key, 0)
            
            if timestamp - last_alert > self.alert_suppression_seconds:
                self.last_alert_times[alert_key] = timestamp
                
                return PerformanceAlert(
                    metric_name=metric_name,
                    current_value=value,
                    threshold=threshold,
                    level=alert_level,
                    timestamp=timestamp,
                    message=f"{metric_name} is {value:.2f}, exceeding {alert_level.value} threshold of {threshold}"
                )
        
        return None
    
    async def _handle_alert(self, alert: PerformanceAlert) -> None:
        """Handle performance alert."""
        self.alert_counts[f"{alert.metric_name}:{alert.level.value}"] += 1
        
        # Log alert
        print(f"🚨 {alert.level.value.upper()} ALERT: {alert.message}")
        
        # Could integrate with external alerting systems here
        # e.g., send to Slack, PagerDuty, etc.
    
    async def _persist_metric(self, metric: PerformanceMetric) -> None:
        """Persist metric to Redis."""
        if not self.redis_client:
            return
        
        try:
            # Store metric in Redis with TTL
            key = f"metrics:{metric.name}:{int(metric.timestamp)}"
            data = asdict(metric)
            await self.redis_client.setex(key, 3600, json.dumps(data))  # 1 hour TTL
        except Exception:
            pass  # Fail silently for metrics persistence
    
    async def _background_monitor(self) -> None:
        """Background monitoring task."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._calculate_derived_metrics()
            except Exception as e:
                print(f"Background monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _calculate_derived_metrics(self) -> None:
        """Calculate derived metrics like error rates, throughput, etc."""
        now = time.time()
        
        # Calculate error rate over last 5 minutes
        recent_window = now - 300  # 5 minutes
        recent_metrics = [
            (timestamp, name, value) 
            for timestamp, name, value in self.time_windows['5m']
            if timestamp > recent_window
        ]
        
        if recent_metrics:
            # Error rate
            error_count = len([m for m in recent_metrics if m[1] == 'request_error'])
            total_count = len([m for m in recent_metrics if m[1] == 'request_total'])
            
            if total_count > 0:
                error_rate = error_count / total_count
                await self.record_metric('error_rate', error_rate)
            
            # Request throughput (requests per second)
            if total_count > 0:
                throughput = total_count / 300  # Over 5 minutes
                await self.record_metric('requests_per_second', throughput)
    
    async def start_request(self) -> str:
        """Start tracking a request. Returns request ID."""
        request_id = f"req_{int(time.time() * 1000)}_{self.request_counters['total_requests']}"
        self.request_counters['total_requests'] += 1
        self.request_counters['concurrent_requests'] += 1
        
        await self.record_metric('request_total', 1)
        await self.record_metric('concurrent_requests', self.request_counters['concurrent_requests'])
        
        return request_id
    
    async def end_request(self, request_id: str, success: bool, latency_ms: float) -> None:
        """End tracking a request."""
        self.request_counters['concurrent_requests'] -= 1
        
        if success:
            self.request_counters['successful_requests'] += 1
            await self.record_metric('request_success', 1)
        else:
            self.request_counters['failed_requests'] += 1
            await self.record_metric('request_error', 1)
        
        await self.record_metric('query_latency_ms', latency_ms)
        await self.record_metric('concurrent_requests', self.request_counters['concurrent_requests'])
    
    async def record_retrieval_latency(self, latency_ms: float, retriever_type: str = 'hybrid') -> None:
        """Record retrieval latency."""
        await self.record_metric('retrieval_latency_ms', latency_ms, {'type': retriever_type})
    
    async def record_llm_latency(self, latency_ms: float, model: str = 'default') -> None:
        """Record LLM latency.""" 
        await self.record_metric('llm_latency_ms', latency_ms, {'model': model})
    
    async def record_cache_stats(self, service: str, hit_rate: float, cache_size: int) -> None:
        """Record cache performance statistics."""
        await self.record_metric('cache_hit_rate', hit_rate, {'service': service})
        await self.record_metric('cache_size', cache_size, {'service': service})
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        now = time.time()
        stats = {
            'timestamp': now,
            'requests': dict(self.request_counters),
            'recent_metrics': {},
            'alerts': {
                'active_alerts': len(self.alerts),
                'alert_counts': dict(self.alert_counts),
                'recent_alerts': [asdict(alert) for alert in list(self.alerts)[-10:]]
            }
        }
        
        # Calculate recent averages for key metrics
        recent_window = now - 300  # Last 5 minutes
        
        for metric_name in ['query_latency_ms', 'retrieval_latency_ms', 'llm_latency_ms']:
            if metric_name in self.metrics:
                recent_values = [
                    m.value for m in self.metrics[metric_name]
                    if m.timestamp > recent_window
                ]
                
                if recent_values:
                    stats['recent_metrics'][metric_name] = {
                        'count': len(recent_values),
                        'avg': round(statistics.mean(recent_values), 2),
                        'min': round(min(recent_values), 2),
                        'max': round(max(recent_values), 2),
                        'p95': round(sorted(recent_values)[int(len(recent_values) * 0.95)], 2) if len(recent_values) > 1 else recent_values[0]
                    }
        
        return stats
    
    def get_health_score(self) -> Dict[str, Any]:
        """Calculate overall system health score."""
        now = time.time()
        recent_window = now - 300  # Last 5 minutes
        
        health_factors = []
        issues = []
        
        # Check recent latency
        if 'query_latency_ms' in self.metrics:
            recent_latencies = [
                m.value for m in self.metrics['query_latency_ms']
                if m.timestamp > recent_window
            ]
            
            if recent_latencies:
                avg_latency = statistics.mean(recent_latencies)
                if avg_latency < 50:
                    health_factors.append(1.0)  # Excellent
                elif avg_latency < 100:
                    health_factors.append(0.8)  # Good
                elif avg_latency < 200:
                    health_factors.append(0.6)  # Fair
                    issues.append(f"Average latency is {avg_latency:.1f}ms")
                else:
                    health_factors.append(0.3)  # Poor
                    issues.append(f"High latency: {avg_latency:.1f}ms")
        
        # Check error rate
        recent_errors = len([a for a in self.alerts if a.timestamp > recent_window])
        if recent_errors == 0:
            health_factors.append(1.0)
        elif recent_errors < 5:
            health_factors.append(0.7)
            issues.append(f"{recent_errors} recent alerts")
        else:
            health_factors.append(0.4)
            issues.append(f"High alert rate: {recent_errors} alerts")
        
        # Check concurrent load
        current_load = self.request_counters['concurrent_requests']
        if current_load < 10:
            health_factors.append(1.0)
        elif current_load < 50:
            health_factors.append(0.8)
        else:
            health_factors.append(0.5)
            issues.append(f"High concurrent load: {current_load}")
        
        # Calculate overall health score
        if health_factors:
            overall_score = statistics.mean(health_factors)
        else:
            overall_score = 0.5  # Default when no data
        
        # Determine health status
        if overall_score >= 0.9:
            status = "excellent"
        elif overall_score >= 0.7:
            status = "good"
        elif overall_score >= 0.5:
            status = "fair"
        else:
            status = "poor"
        
        return {
            'score': round(overall_score, 2),
            'status': status,
            'issues': issues,
            'timestamp': now
        }


# Global instance
_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get or create the performance monitor singleton."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor