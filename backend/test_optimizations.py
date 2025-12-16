"""
Test script for backend optimizations
Validates caching, performance improvements, and token optimization
"""
import asyncio
import time
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from services.journey_generator import JourneyGenerator
from services.cache_manager import get_cache_manager, get_cache_stats
from services.config import get_config
from services.monitoring import get_metrics


def test_caching():
    """Test caching functionality"""
    print("🧪 Testing Caching System...")
    
    try:
        cache_manager = get_cache_manager()
        
        # Test basic cache operations
        cache_manager.llm_responses.set("test_key", {"result": "test_value"})
        cached_value = cache_manager.llm_responses.get("test_key")
        
        assert cached_value == {"result": "test_value"}, "Basic cache test failed"
        print("✅ Basic caching works")
        
        # Test cache stats
        stats = get_cache_stats()
        print(f"✅ Cache stats available: {len(stats)} cache types")
        
    except Exception as e:
        print(f"❌ Cache test failed: {e}")


def test_config():
    """Test configuration system"""
    print("\n🧪 Testing Configuration System...")
    
    try:
        config = get_config()
        
        # Test config values
        assert hasattr(config, 'cache'), "Config missing cache section"
        assert hasattr(config, 'connections'), "Config missing connections section"
        assert hasattr(config, 'llm'), "Config missing llm section"
        
        # Test environment-based values
        assert config.cache.embeddings_size > 0, "Invalid cache size"
        assert config.connections.max_connections > 0, "Invalid connection limit"
        
        print(f"✅ Configuration loaded successfully")
        print(f"   Cache sizes: embeddings={config.cache.embeddings_size}, llm={config.cache.llm_size}")
        print(f"   Connection pool: max={config.connections.max_connections}")
        print(f"   LLM settings: temp={config.llm.journey_generation_temp}")
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")


def test_journey_generation():
    """Test journey generation with optimizations"""
    print("\n🧪 Testing Journey Generation...")
    
    try:
        generator = JourneyGenerator(use_rag=True, temperature=0.7)
        
        # Test simple query
        query = "set up authentication"
        print(f"🚀 Testing query: '{query}'")
        
        start_time = time.time()
        result = generator.generate_journey(query, max_steps=3)
        end_time = time.time()
        
        # Validate result
        assert 'error' not in result, f"Journey generation failed: {result.get('error')}"
        assert 'steps' in result, "Missing steps in result"
        assert len(result['steps']) > 0, "No steps generated"
        
        print(f"✅ Journey generated in {end_time - start_time:.2f}s")
        print(f"   Generated {len(result['steps'])} steps")
        print(f"   Estimated time: {result.get('estimated_time', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Journey generation test failed: {e}")


async def test_parallel_processing():
    """Test parallel processing capabilities"""
    print("\n🧪 Testing Parallel Processing...")
    
    try:
        generator = JourneyGenerator(use_rag=True, temperature=0.7)
        
        # Test async journey generation
        query = "implement user login"
        print(f"🔀 Testing async query: '{query}'")
        
        start_time = time.time()
        result = await generator.generate_journey_async(query, max_steps=3)
        end_time = time.time()
        
        # Validate result
        assert 'error' not in result, f"Async journey generation failed: {result.get('error')}"
        assert 'steps' in result, "Missing steps in async result"
        
        print(f"✅ Async journey generated in {end_time - start_time:.2f}s")
        print(f"   Generated {len(result['steps'])} steps")
        
    except Exception as e:
        print(f"❌ Parallel processing test failed: {e}")


def test_token_optimization():
    """Test token optimization functionality"""
    print("\n🧪 Testing Token Optimization...")
    
    try:
        from services.token_optimizer import ContentOptimizer, TokenBudget
        
        optimizer = ContentOptimizer()
        
        # Test token estimation
        test_text = "This is a test sentence with multiple words for token estimation."
        token_count = optimizer.estimate_tokens(test_text)
        assert token_count > 0, "Token estimation failed"
        
        # Test content optimization
        query = "authentication setup"
        content = "This document explains how to set up authentication in your application. First, you need to install the required packages. Then configure the authentication middleware. Finally, test the login functionality."
        
        optimized = optimizer.extract_relevant_sentences(content, query, max_tokens=50)
        assert len(optimized) <= len(content), "Content optimization failed"
        
        print(f"✅ Token optimization working")
        print(f"   Estimated tokens: {token_count}")
        print(f"   Content compression: {len(optimized)}/{len(content)} chars")
        
    except Exception as e:
        print(f"❌ Token optimization test failed: {e}")


def test_monitoring():
    """Test monitoring and metrics"""
    print("\n🧪 Testing Monitoring System...")
    
    try:
        metrics = get_metrics()
        
        if metrics:
            # Test request tracking
            request_id = metrics.start_request()
            metrics.record_cache_hit()
            metrics.record_api_call(request_id, 'test', 'test', 'success', 0.1, 10, 0.001)
            metrics.end_request(request_id, 100)
            
            # Get metrics
            current_metrics = metrics.get_current_metrics()
            assert current_metrics.total_requests > 0, "Request tracking failed"
            
            print(f"✅ Monitoring system working")
            print(f"   Total requests: {current_metrics.total_requests}")
            print(f"   Cache hit rate: {current_metrics.cache_hit_rate:.1f}%")
        else:
            print("⚠️  Monitoring not available (import fallback)")
        
    except Exception as e:
        print(f"❌ Monitoring test failed: {e}")


async def run_all_tests():
    """Run all optimization tests"""
    print("🧪 Running Backend Optimization Tests\n")
    print("=" * 50)
    
    # Run synchronous tests
    test_caching()
    test_config()
    test_token_optimization()
    test_monitoring()
    test_journey_generation()
    
    # Run async tests
    await test_parallel_processing()
    
    print("\n" + "=" * 50)
    print("🎉 Optimization Tests Completed!")
    
    # Show final cache stats
    try:
        final_stats = get_cache_stats()
        print(f"\n📊 Final Cache Stats:")
        for cache_type, stats in final_stats.items():
            print(f"   {cache_type}: {stats['hits']} hits, {stats['misses']} misses, {stats['hit_rate']}% hit rate")
    except:
        pass


def main():
    """Main test runner"""
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")


if __name__ == "__main__":
    main()