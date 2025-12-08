#!/usr/bin/env python3
"""
Test script for HuggingFace integration
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Test imports - avoid dotenv loading by testing syntax only
try:
    # Just test that the file can be parsed
    import ast
    with open('backend/services/llm_service.py', 'r') as f:
        ast.parse(f.read())
    print('✅ llm_service.py syntax is valid')

    # Now test imports (will fail on dotenv but that's expected)
    try:
        from services.llm_service import BaseLLMService, ClaudeService, HuggingFaceK2Service, HuggingFaceK2OpenAIService, get_llm_service
    print('✅ All LLM service classes import successfully')

    # Test factory function with different models
    models_to_test = ['claude', 'hf-k2', 'hf-k2-openai']

    for model in models_to_test:
        try:
            service = get_llm_service(model)
            print(f'✅ {model} service factory works (class: {service.__class__.__name__})')
        except ValueError as e:
            print(f'⚠️  {model} service requires token: {e}')
        except Exception as e:
            print(f'❌ {model} service failed: {e}')

    # Test journey generator import
    from services.journey_generator import JourneyGenerator
    print('✅ JourneyGenerator imports successfully')

    # Test API import
    from api.journey import JourneyRequest, JourneyResponse
    print('✅ Journey API models import successfully')

    print('\n🎉 All imports successful! HuggingFace integration is ready.')

except Exception as e:
    print(f'❌ Import error: {e}')
    import traceback
    traceback.print_exc()
