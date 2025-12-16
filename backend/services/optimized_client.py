"""
Enhanced HTTP client with connection pooling and circuit breakers
Provides optimized HTTP requests with intelligent retry logic
"""
import asyncio
import aiohttp
import time
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
import threading
from enum import Enum
import json


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"     # Normal operation
    OPEN = "open"         # Circuit is open, fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5          # Failures before opening
    recovery_timeout: float = 60.0      # Seconds to wait before trying again
    expected_exception: type = Exception # Exception type to track


class CircuitBreaker:
    """Circuit breaker for preventing cascade failures"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.lock = threading.RLock()
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        with self.lock:
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time < self.config.recovery_timeout:
                    raise Exception(f"Circuit breaker is OPEN for {self.config.recovery_timeout}s")
                else:
                    # Try to recover
                    self.state = CircuitState.HALF_OPEN
            
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.config.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call"""
        with self.lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failed call"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN


class OptimizedHTTPClient:
    """
    HTTP client with connection pooling, retry logic, and circuit breakers
    """
    
    def __init__(
        self,
        base_url: str,
        max_connections: int = 100,
        connection_timeout: float = 30.0,
        read_timeout: float = 60.0,
        max_retries: int = 3,
        backoff_factor: float = 1.0
    ):
        self.base_url = base_url.rstrip('/')
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        
        # Configure circuit breakers for different types of failures
        self.circuit_breakers = {
            'rate_limit': CircuitBreaker(CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=120.0,
                expected_exception=Exception
            )),
            'timeout': CircuitBreaker(CircuitBreakerConfig(
                failure_threshold=2,
                recovery_timeout=60.0,
                expected_exception=Exception
            )),
            'server_error': CircuitBreaker(CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=300.0,
                expected_exception=Exception
            ))
        }
        
        # Session configuration
        self.session_config = aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=max_connections // 2,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        self.timeout_config = aiohttp.ClientTimeout(
            total=connection_timeout + read_timeout,
            connect=connection_timeout,
            sock_read=read_timeout
        )
    
    async def post(self, endpoint: str, data: Dict, headers: Optional[Dict] = None) -> Dict:
        """
        Make POST request with retry logic and circuit breaker protection
        """
        url = f"{self.base_url}{endpoint}"
        request_headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'DocsBuddy-Optimized/1.0',
            **(headers or {})
        }
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with aiohttp.ClientSession(
                    connector=self.session_config,
                    timeout=self.timeout_config
                ) as session:
                    async with session.post(
                        url,
                        json=data,
                        headers=request_headers
                    ) as response:
                        # Handle different response codes
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:
                            # Rate limited - use circuit breaker
                            circuit_breaker = self.circuit_breakers['rate_limit']
                            error_text = await response.text()
                            exception = Exception(f"Rate limit exceeded: {error_text}")
                            
                            if attempt < self.max_retries:
                                # Exponential backoff for rate limits
                                wait_time = self.backoff_factor * (2 ** attempt)
                                print(f"⚠️ Rate limit hit. Waiting {wait_time}s (attempt {attempt + 1})")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                raise circuit_breaker.call(lambda: exception)
                        
                        elif response.status >= 500:
                            # Server error - use circuit breaker
                            circuit_breaker = self.circuit_breakers['server_error']
                            error_text = await response.text()
                            exception = Exception(f"Server error {response.status}: {error_text}")
                            raise circuit_breaker.call(lambda: exception)
                        
                        else:
                            # Client error - no retry
                            error_text = await response.text()
                            raise Exception(f"HTTP {response.status}: {error_text}")
            
            except asyncio.TimeoutError as e:
                circuit_breaker = self.circuit_breakers['timeout']
                if attempt < self.max_retries:
                    wait_time = self.backoff_factor * (2 ** attempt)
                    print(f"⚠️ Request timeout. Waiting {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise circuit_breaker.call(lambda: e)
            
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.backoff_factor * (2 ** attempt)
                    print(f"⚠️ Request failed: {e}. Waiting {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise e
        
        # If we get here, all retries failed
        raise last_exception
    
    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make GET request with retry logic"""
        url = f"{self.base_url}{endpoint}"
        
        async with aiohttp.ClientSession(
            connector=self.session_config,
            timeout=self.timeout_config
        ) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
    
    def get_circuit_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            name: {
                'state': cb.state.value,
                'failure_count': cb.failure_count,
                'last_failure': cb.last_failure_time
            }
            for name, cb in self.circuit_breakers.items()
        }


class ConnectionPool:
    """Thread-safe connection pool manager"""
    
    def __init__(self):
        self.pools: Dict[str, OptimizedHTTPClient] = {}
        self.lock = threading.RLock()
    
    def get_client(self, base_url: str, **kwargs) -> OptimizedHTTPClient:
        """Get or create HTTP client for a base URL"""
        with self.lock:
            if base_url not in self.pools:
                self.pools[base_url] = OptimizedHTTPClient(base_url, **kwargs)
            return self.pools[base_url]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all connection pools"""
        return {
            url: {
                'circuit_breakers': client.get_circuit_stats()
            }
            for url, client in self.pools.items()
        }


# Global connection pool instance
_connection_pool: Optional[ConnectionPool] = None
_pool_lock = threading.Lock()


def get_connection_pool() -> ConnectionPool:
    """Get or create global connection pool"""
    global _connection_pool
    
    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                _connection_pool = ConnectionPool()
    
    return _connection_pool


def get_optimized_client(base_url: str, **kwargs) -> OptimizedHTTPClient:
    """Get optimized HTTP client for a service"""
    pool = get_connection_pool()
    return pool.get_client(base_url, **kwargs)


async def batch_requests(
    requests: List[Dict], 
    max_concurrent: int = 10
) -> List[Dict]:
    """
    Execute multiple requests concurrently with controlled concurrency
    
    Args:
        requests: List of request dicts with 'url', 'method', 'data', 'headers'
        max_concurrent: Maximum concurrent requests
    
    Returns:
        List of responses in same order as requests
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def execute_single(request):
        async with semaphore:
            client = get_optimized_client(request['url'])
            
            if request['method'].upper() == 'POST':
                return await client.post(
                    request['endpoint'],
                    request.get('data', {}),
                    request.get('headers')
                )
            elif request['method'].upper() == 'GET':
                return await client.get(
                    request['endpoint'],
                    request.get('params')
                )
    
    # Execute all requests concurrently
    tasks = [execute_single(req) for req in requests]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return results