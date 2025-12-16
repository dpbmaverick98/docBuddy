"""
Performance monitoring and metrics collection for DocsBuddy
Tracks API calls, latencies, costs, and system performance
"""
import time
import threading
import json
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from datetime import datetime, timedelta
import os


@dataclass
class APICall:
    """Individual API call record"""
    timestamp: float
    service: str  # 'cohere', 'anthropic', 'x402', etc.
    endpoint: str
    method: str   # 'embed', 'chat', 'rerank', etc.
    status: str    # 'success', 'error', 'timeout'
    latency: float  # Response time in seconds
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class RequestMetrics:
    """Metrics for a single request (e.g., journey generation)"""
    request_id: str
    start_time: float
    end_time: float
    total_latency: float
    api_calls: List[APICall]
    cache_hits: int
    cache_misses: int
    final_result_size: int  # Characters in response
    
    @property
    def total_cost(self) -> float:
        """Total cost of all API calls"""
        return sum(call.cost_usd or 0 for call in self.api_calls)
    
    @property
    def total_tokens(self) -> int:
        """Total tokens used across all API calls"""
        return sum(call.tokens_used or 0 for call in self.api_calls)


@dataclass
class SystemMetrics:
    """System-level performance metrics"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_api_calls: int
    total_cost_usd: float
    total_tokens: int
    average_response_time: float
    cache_hit_rate: float
    active_connections: int


class MetricsCollector:
    """Collects and manages performance metrics"""
    
    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self.lock = threading.RLock()
        
        # Request metrics storage
        self.request_metrics: deque = deque(maxlen=10000)  # Recent requests
        self.active_requests: Dict[str, RequestMetrics] = {}  # Currently active
        
        # Aggregated metrics
        self.api_call_stats = defaultdict(lambda: defaultdict(list))
        self.hourly_stats = defaultdict(lambda: defaultdict(float))
        
        # Real-time counters
        self.counters = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_api_calls': 0,
            'total_cost_usd': 0.0,
            'total_tokens': 0
        }
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()
    
    def start_request(self, request_id: Optional[str] = None) -> str:
        """Start tracking a new request"""
        if request_id is None:
            request_id = self._generate_request_id()
        
        with self.lock:
            self.active_requests[request_id] = RequestMetrics(
                request_id=request_id,
                start_time=time.time(),
                end_time=0,
                total_latency=0,
                api_calls=[],
                cache_hits=0,
                cache_misses=0,
                final_result_size=0
            )
            
            self.counters['total_requests'] += 1
        
        return request_id
    
    def end_request(self, request_id: str, final_result_size: int = 0):
        """Complete request tracking"""
        with self.lock:
            if request_id in self.active_requests:
                request = self.active_requests[request_id]
                request.end_time = time.time()
                request.total_latency = request.end_time - request.start_time
                request.final_result_size = final_result_size
                
                # Move to completed requests
                self.request_metrics.append(request)
                del self.active_requests[request_id]
                
                # Update counters
                self.counters['successful_requests'] += 1
                
                # Update hourly stats
                hour_key = datetime.now().strftime('%Y-%m-%d-%H')
                if 'requests' not in self.hourly_stats[hour_key]:
                    self.hourly_stats[hour_key]['requests'] = 0
                if 'latency_sum' not in self.hourly_stats[hour_key]:
                    self.hourly_stats[hour_key]['latency_sum'] = 0.0
                self.hourly_stats[hour_key]['requests'] += 1
                self.hourly_stats[hour_key]['latency_sum'] += request.total_latency
    
    def fail_request(self, request_id: str, error_message: str):
        """Mark request as failed"""
        with self.lock:
            if request_id in self.active_requests:
                request = self.active_requests[request_id]
                request.end_time = time.time()
                request.total_latency = request.end_time - request.start_time
                
                # Move to completed requests
                self.request_metrics.append(request)
                del self.active_requests[request_id]
                
                # Update counters
                self.counters['failed_requests'] += 1
    
    def record_api_call(
        self,
        request_id: str,
        service: str,
        endpoint: str,
        method: str,
        status: str,
        latency: float,
        tokens_used: Optional[int] = None,
        cost_usd: Optional[float] = None,
        error_message: Optional[str] = None
    ):
        """Record an API call within a request"""
        api_call = APICall(
            timestamp=time.time(),
            service=service,
            endpoint=endpoint,
            method=method,
            status=status,
            latency=latency,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            error_message=error_message
        )
        
        with self.lock:
            if request_id in self.active_requests:
                self.active_requests[request_id].api_calls.append(api_call)
            
            # Update counters
            self.counters['total_api_calls'] += 1
            if tokens_used:
                self.counters['total_tokens'] += tokens_used
            if cost_usd:
                self.counters['total_cost_usd'] += cost_usd
            
            # Update service stats
            self.api_call_stats[service][method].append({
                'timestamp': time.time(),
                'latency': latency,
                'status': status,
                'cost': cost_usd
            })
    
    def record_cache_hit(self):
        """Record a cache hit"""
        with self.lock:
            self.counters['cache_hits'] += 1
    
    def record_cache_miss(self):
        """Record a cache miss"""
        with self.lock:
            self.counters['cache_misses'] += 1
    
    def get_current_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        with self.lock:
            total_requests = self.counters['total_requests']
            
            # Calculate average response time
            successful_requests = [r for r in self.request_metrics 
                                if r.end_time > 0 and r.total_latency > 0]
            avg_response_time = (sum(r.total_latency for r in successful_requests) / 
                               len(successful_requests)) if successful_requests else 0
            
            # Calculate cache hit rate
            total_cache_requests = self.counters['cache_hits'] + self.counters['cache_misses']
            cache_hit_rate = (self.counters['cache_hits'] / total_cache_requests * 100) if total_cache_requests > 0 else 0
            
            return SystemMetrics(
                total_requests=total_requests,
                successful_requests=self.counters['successful_requests'],
                failed_requests=self.counters['failed_requests'],
                total_api_calls=self.counters['total_api_calls'],
                total_cost_usd=self.counters['total_cost_usd'],
                total_tokens=self.counters['total_tokens'],
                average_response_time=avg_response_time,
                cache_hit_rate=cache_hit_rate,
                active_connections=len(self.active_requests)
            )
    
    def get_service_stats(self, service: str, method: str) -> Dict[str, Any]:
        """Get statistics for a specific service and method"""
        with self.lock:
            calls = self.api_call_stats[service][method]
            
            if not calls:
                return {
                    'total_calls': 0,
                    'success_rate': 0,
                    'average_latency': 0,
                    'total_cost': 0,
                    'average_cost': 0
                }
            
            successful_calls = [c for c in calls if c['status'] == 'success']
            success_rate = len(successful_calls) / len(calls) * 100
            avg_latency = sum(c['latency'] for c in calls) / len(calls)
            total_cost = sum(c['cost'] or 0 for c in calls)
            avg_cost = total_cost / len(calls)
            
            return {
                'total_calls': len(calls),
                'success_rate': round(success_rate, 2),
                'average_latency': round(avg_latency, 3),
                'total_cost': round(total_cost, 6),
                'average_cost': round(avg_cost, 6)
            }
    
    def get_recent_requests(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent request metrics"""
        with self.lock:
            recent = list(self.request_metrics)[-limit:]
            return [asdict(req) for req in recent]
    
    def get_hourly_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get statistics by hour for the last N hours"""
        with self.lock:
            cutoff = datetime.now() - timedelta(hours=hours)
            result = {}
            
            for hour_key in sorted(self.hourly_stats.keys()):
                hour_dt = datetime.strptime(hour_key, '%Y-%m-%d-%H')
                if hour_dt >= cutoff:
                    stats = self.hourly_stats[hour_key]
                    avg_latency = (stats['latency_sum'] / stats['requests']) if stats['requests'] > 0 else 0
                    
                    result[hour_key] = {
                        'requests': stats['requests'],
                        'average_latency': round(avg_latency, 3)
                    }
            
            return result
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        return hashlib.md5(f"{time.time()}{os.urandom(8)}".encode()).hexdigest()[:16]
    
    def _cleanup_worker(self):
        """Background worker to clean up old metrics"""
        while True:
            try:
                time.sleep(3600)  # Run every hour
                cutoff_time = time.time() - (self.retention_hours * 3600)
                
                with self.lock:
                    # Remove old request metrics
                    while (self.request_metrics and 
                           self.request_metrics[0].end_time < cutoff_time):
                        self.request_metrics.popleft()
                    
                    # Clean old service stats
                    for service in self.api_call_stats:
                        for method in self.api_call_stats[service]:
                            calls = self.api_call_stats[service][method]
                            self.api_call_stats[service][method] = [
                                c for c in calls if c['timestamp'] > cutoff_time
                            ]
                    
                    # Clean old hourly stats
                    cutoff_hour = datetime.now() - timedelta(hours=self.retention_hours)
                    cutoff_key = cutoff_hour.strftime('%Y-%m-%d-%H')
                    keys_to_remove = [k for k in self.hourly_stats.keys() if k < cutoff_key]
                    for key in keys_to_remove:
                        del self.hourly_stats[key]
                
                print(f"🧹 Metrics cleanup completed")
                
            except Exception as e:
                print(f"⚠️ Metrics cleanup error: {e}")


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None
_metrics_lock = threading.Lock()


def get_metrics() -> MetricsCollector:
    """Get or create global metrics collector"""
    global _metrics_collector
    
    if _metrics_collector is None:
        with _metrics_lock:
            if _metrics_collector is None:
                retention_hours = int(os.getenv('METRICS_RETENTION_HOURS', '24'))
                _metrics_collector = MetricsCollector(retention_hours)
    
    return _metrics_collector


def reset_metrics():
    """Reset all metrics"""
    global _metrics_collector
    with _metrics_lock:
        _metrics_collector = None


# Decorator for automatic API call tracking
def track_api_call(service: str, method: str):
    """Decorator to automatically track API calls"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Create new request for each API call
            request_id = get_metrics().start_request()
            
            start_time = time.time()
            status = 'success'
            tokens = None
            cost = None
            error_msg = None
            
            try:
                result = func(*args, **kwargs)
                
                # Try to extract tokens/cost from result if available
                if isinstance(result, dict):
                    tokens = result.get('tokens_used')
                    cost = result.get('cost_usd')
                
                # End request successfully
                get_metrics().end_request(request_id)
                
                return result
                
            except Exception as e:
                status = 'error'
                error_msg = str(e)
                get_metrics().fail_request(request_id, error_msg)
                raise
            finally:
                latency = time.time() - start_time
                get_metrics().record_api_call(
                    request_id, service, '', method, status, latency, tokens, cost, error_msg
                )
        
        return wrapper
    return decorator


def set_current_request_id(request_id: str):
    """Set current request ID for API call tracking"""
    # This would typically be called at the start of request processing
    pass