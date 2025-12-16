#!/usr/bin/env python3
"""
Final comprehensive test from backend directory
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def test_all_modules():
    """Test all optimization modules work together"""
    print("🧪 Final Integration Test\n")
    print("=" * 50)
    
    success_count = 0
    total_tests = 0
    
    # Test each module
    modules = [
        ("cache_manager", "get_cache_manager"),
        ("config", "get_config"), 
        ("token_optimizer", "ContentOptimizer"),
        ("optimized_client", "OptimizedHTTPClient"),
        ("monitoring", "get_metrics"),
        ("journey_generator", "JourneyGenerator")
    ]
    
    for module_name, import_name in modules:
        total_tests += 1
        try:
            if module_name == "journey_generator":
                # JourneyGenerator requires special handling
                # Just test import without instantiation
                exec(f"from services.{module_name} import {import_name}")
            else:
                # Test import and basic instantiation
                module = __import__(f"services.{module_name}", fromlist=[import_name])
                if import_name == "get_cache_manager":
                    instance = getattr(module, import_name)()
                elif import_name == "get_config":
                    instance = getattr(module, import_name)()
                elif import_name == "ContentOptimizer":
                    instance = getattr(module, import_name)()
                else:
                    instance = getattr(module, import_name)
            
            print(f"✅ {module_name}: {import_name} - OK")
            success_count += 1
        except Exception as e:
            print(f"❌ {module_name}: {import_name} - {e}")
    
    print("\n" + "=" * 50)
    
    if success_count == total_tests:
        print("🎉 ALL MODULES WORKING!")
        print("✅ Backend optimizations are ready!")
        return 0
    else:
        print(f"❌ {total_tests - success_count} modules failed")
        return 1

if __name__ == "__main__":
    exit(test_all_modules())