"""
Configuration management for DocsBuddy
Environment-specific settings and optimization parameters
"""
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class CacheConfig:
    """Cache configuration settings"""
    # Cache sizes
    embeddings_size: int = 500
    rag_size: int = 200
    llm_size: int = 300
    intent_size: int = 200
    summary_size: int = 400
    
    # TTL settings (seconds)
    embeddings_ttl: int = 86400  # 24 hours
    rag_ttl: int = 7200          # 2 hours
    llm_ttl: int = 3600          # 1 hour
    intent_ttl: int = 14400       # 4 hours
    summary_ttl: int = 43200      # 12 hours


@dataclass
class ConnectionConfig:
    """Connection pool and HTTP client settings"""
    max_connections: int = 100
    connection_timeout: float = 30.0
    read_timeout: float = 60.0
    max_retries: int = 3
    backoff_factor: float = 1.0
    
    # Circuit breaker settings
    rate_limit_threshold: int = 3
    rate_limit_timeout: float = 120.0
    server_error_threshold: int = 5
    server_error_timeout: float = 300.0


@dataclass
class LLMConfig:
    """LLM optimization settings"""
    # Token management
    max_context_tokens: int = 3000
    reserve_for_response: int = 500
    min_tokens_per_section: int = 50
    
    # Temperature defaults
    journey_generation_temp: float = 0.7
    summarization_temp: float = 0.3
    qa_temp: float = 0.7
    intent_extraction_temp: float = 0.3
    
    # Model selection
    default_model: str = "claude"
    fallback_model: str = "hf-k2-openai"


@dataclass
class RAGConfig:
    """RAG system configuration"""
    # Search parameters
    default_top_k: int = 20
    similarity_cutoff_beginner: float = 0.65
    similarity_cutoff_intermediate: float = 0.7
    similarity_cutoff_advanced: float = 0.75
    
    # Cohere optimizations
    use_query_expansion: bool = True
    use_rerank: bool = True
    use_compression: bool = True
    max_expansion_queries: int = 3
    
    # Performance tuning
    search_multiplier: int = 2  # Search multiplier * top_k for candidates
    max_docs_for_context: int = 5


@dataclass
class PerformanceConfig:
    """Performance monitoring and optimization"""
    # Concurrency settings
    max_concurrent_requests: int = 10
    batch_processing_enabled: bool = True
    
    # Monitoring
    enable_metrics: bool = True
    metrics_retention_hours: int = 24
    enable_tracing: bool = False
    
    # Rate limiting
    requests_per_minute: Optional[int] = None  # None = no limit
    requests_per_hour: Optional[int] = None


class Config:
    """Main configuration manager"""
    
    def __init__(self, env_file: Optional[str] = None):
        self.env_file = env_file
        self._load_environment()
        self._setup_configs()
    
    def _load_environment(self):
        """Load environment variables"""
        if self.env_file:
            from dotenv import load_dotenv
            load_dotenv(self.env_file)
        else:
            # Try to load from default locations
            for env_path in ['.env', '../.env', '../../.env']:
                if Path(env_path).exists():
                    from dotenv import load_dotenv
                    load_dotenv(env_path)
                    break
    
    def _setup_configs(self):
        """Setup configuration objects"""
        self.cache = CacheConfig(
            embeddings_size=int(os.getenv('CACHE_EMBEDDINGS_SIZE', '500')),
            rag_size=int(os.getenv('CACHE_RAG_SIZE', '200')),
            llm_size=int(os.getenv('CACHE_LLM_SIZE', '300')),
            intent_size=int(os.getenv('CACHE_INTENT_SIZE', '200')),
            summary_size=int(os.getenv('CACHE_SUMMARY_SIZE', '400')),
            
            embeddings_ttl=int(os.getenv('CACHE_EMBEDDINGS_TTL', '86400')),
            rag_ttl=int(os.getenv('CACHE_RAG_TTL', '7200')),
            llm_ttl=int(os.getenv('CACHE_LLM_TTL', '3600')),
            intent_ttl=int(os.getenv('CACHE_INTENT_TTL', '14400')),
            summary_ttl=int(os.getenv('CACHE_SUMMARY_TTL', '43200'))
        )
        
        self.connections = ConnectionConfig(
            max_connections=int(os.getenv('HTTP_MAX_CONNECTIONS', '100')),
            connection_timeout=float(os.getenv('HTTP_TIMEOUT', '30.0')),
            read_timeout=float(os.getenv('HTTP_READ_TIMEOUT', '60.0')),
            max_retries=int(os.getenv('HTTP_MAX_RETRIES', '3')),
            backoff_factor=float(os.getenv('HTTP_BACKOFF_FACTOR', '1.0')),
            
            rate_limit_threshold=int(os.getenv('RATE_LIMIT_THRESHOLD', '3')),
            rate_limit_timeout=float(os.getenv('RATE_LIMIT_TIMEOUT', '120.0')),
            server_error_threshold=int(os.getenv('SERVER_ERROR_THRESHOLD', '5')),
            server_error_timeout=float(os.getenv('SERVER_ERROR_TIMEOUT', '300.0'))
        )
        
        self.llm = LLMConfig(
            max_context_tokens=int(os.getenv('LLM_MAX_CONTEXT_TOKENS', '3000')),
            reserve_for_response=int(os.getenv('LLM_RESERVE_RESPONSE', '500')),
            min_tokens_per_section=int(os.getenv('LLM_MIN_TOKENS_SECTION', '50')),
            
            journey_generation_temp=float(os.getenv('LLM_JOURNEY_TEMP', '0.7')),
            summarization_temp=float(os.getenv('LLM_SUMMARY_TEMP', '0.3')),
            qa_temp=float(os.getenv('LLM_QA_TEMP', '0.7')),
            intent_extraction_temp=float(os.getenv('LLM_INTENT_TEMP', '0.3')),
            
            default_model=os.getenv('LLM_DEFAULT_MODEL', 'claude'),
            fallback_model=os.getenv('LLM_FALLBACK_MODEL', 'hf-k2-openai')
        )
        
        self.rag = RAGConfig(
            default_top_k=int(os.getenv('RAG_DEFAULT_TOP_K', '20')),
            similarity_cutoff_beginner=float(os.getenv('RAG_CUTOFF_BEGINNER', '0.65')),
            similarity_cutoff_intermediate=float(os.getenv('RAG_CUTOFF_INTERMEDIATE', '0.7')),
            similarity_cutoff_advanced=float(os.getenv('RAG_CUTOFF_ADVANCED', '0.75')),
            
            use_query_expansion=os.getenv('RAG_USE_EXPANSION', 'true').lower() == 'true',
            use_rerank=os.getenv('RAG_USE_RERANK', 'true').lower() == 'true',
            use_compression=os.getenv('RAG_USE_COMPRESSION', 'true').lower() == 'true',
            max_expansion_queries=int(os.getenv('RAG_MAX_EXPANSION', '3')),
            
            search_multiplier=int(os.getenv('RAG_SEARCH_MULTIPLIER', '2')),
            max_docs_for_context=int(os.getenv('RAG_MAX_DOCS_CONTEXT', '5'))
        )
        
        self.performance = PerformanceConfig(
            max_concurrent_requests=int(os.getenv('MAX_CONCURRENT_REQUESTS', '10')),
            batch_processing_enabled=os.getenv('BATCH_PROCESSING', 'true').lower() == 'true',
            
            enable_metrics=os.getenv('ENABLE_METRICS', 'true').lower() == 'true',
            metrics_retention_hours=int(os.getenv('METRICS_RETENTION_HOURS', '24')),
            enable_tracing=os.getenv('ENABLE_TRACING', 'false').lower() == 'true',
            
            requests_per_minute=int(os.getenv('RATE_LIMIT_PER_MINUTE', '0')) or None,
            requests_per_hour=int(os.getenv('RATE_LIMIT_PER_HOUR', '0')) or None
        )
    
    def get_circuit_breaker_config(self, error_type: str) -> Dict[str, Any]:
        """Get circuit breaker configuration for error type"""
        configs = {
            'rate_limit': {
                'failure_threshold': self.connections.rate_limit_threshold,
                'recovery_timeout': self.connections.rate_limit_timeout,
                'expected_exception': Exception
            },
            'server_error': {
                'failure_threshold': self.connections.server_error_threshold,
                'recovery_timeout': self.connections.server_error_timeout,
                'expected_exception': Exception
            },
            'timeout': {
                'failure_threshold': 2,
                'recovery_timeout': 60.0,
                'expected_exception': Exception
            }
        }
        return configs.get(error_type, configs['server_error'])
    
    def get_similarity_cutoff(self, complexity: str) -> float:
        """Get similarity cutoff based on complexity level"""
        cutoffs = {
            'beginner': self.rag.similarity_cutoff_beginner,
            'intermediate': self.rag.similarity_cutoff_intermediate,
            'advanced': self.rag.similarity_cutoff_advanced
        }
        return cutoffs.get(complexity, self.rag.similarity_cutoff_intermediate)
    
    def get_temperature(self, task_type: str) -> float:
        """Get temperature setting for task type"""
        temperatures = {
            'journey_generation': self.llm.journey_generation_temp,
            'summarization': self.llm.summarization_temp,
            'qa': self.llm.qa_temp,
            'intent_extraction': self.llm.intent_extraction_temp
        }
        return temperatures.get(task_type, self.llm.journey_generation_temp)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'cache': self.cache.__dict__,
            'connections': self.connections.__dict__,
            'llm': self.llm.__dict__,
            'rag': self.rag.__dict__,
            'performance': self.performance.__dict__
        }
    
    def save_to_file(self, file_path: str):
        """Save configuration to JSON file"""
        config_dict = self.to_dict()
        with open(file_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    @classmethod
    def from_file(cls, file_path: str) -> 'Config':
        """Load configuration from JSON file"""
        with open(file_path, 'r') as f:
            config_dict = json.load(f)
        
        # Create config instance
        config = cls()
        
        # Update with loaded values
        for section_name, section_data in config_dict.items():
            section = getattr(config, section_name)
            for key, value in section_data.items():
                setattr(section, key, value)
        
        return config


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create global configuration instance"""
    global _config
    
    if _config is None:
        _config = Config()
    
    return _config


def reload_config(env_file: Optional[str] = None):
    """Reload configuration from environment"""
    global _config
    _config = Config(env_file)