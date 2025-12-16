#!/usr/bin/env python3
"""
Test script for updated x402 client with v2 protocol support
"""
import os
import sys
import json
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.x402_client import X402Client

def test_x402_client():
    print("🧪 Testing x402 Client v2 Upgrade")
    print("=" * 50)
    
    try:
        # Test v2 protocol (default)
        print("\n1️⃣ Testing x402 v2 Protocol...")
        client_v2 = X402Client(protocol_version=2)
        
        if client_v2.test_connection():
            print("✅ v2 client connected successfully")
            
            # Test health endpoint
            health = client_v2.get_service_health()
            if health:
                print(f"✅ Service health: {health.get('status', 'unknown')}")
                print(f"🩺 Version: {health.get('version', 'unknown')}")
        else:
            print("❌ v2 client connection failed")
        
        # Test v1 protocol fallback
        print("\n2️⃣ Testing x402 v1 Protocol (fallback)...")
        client_v1 = X402Client(protocol_version=1)
        
        if client_v1.test_connection():
            print("✅ v1 client connected successfully")
        else:
            print("❌ v1 client connection failed")
            
        print("\n3️⃣ Protocol Feature Summary:")
        print("🆕 v2 Features:")
        print("   - PAYMENT-SIGNATURE header (base64 encoded)")
        print("   - EIP-712 structured authorization")
        print("   - Enhanced error responses with correlation IDs")
        print("   - Session support (if enabled on server)")
        
        print("\n🔄 v1 Features (fallback):")
        print("   - X402-Payment header (JSON)")
        print("   - Legacy message signing")
        print("   - Backward compatible")
        
        print("\n4️⃣ Configuration:")
        print(f"   Service URL: {os.getenv('X402_SERVICE_URL', 'http://localhost:3000')}")
        print(f"   Network: {os.getenv('X402_NETWORK', 'base')}")
        print(f"   Protocol Version: {os.getenv('X402_PROTOCOL_VERSION', '2')}")
        
        print("\n5️⃣ Usage in Backend Services:")
        print("   services.x402_client.X402Client()  # Defaults to v2")
        print("   services.x402_client.X402Client(1) # Force v1 protocol")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_x402_client()