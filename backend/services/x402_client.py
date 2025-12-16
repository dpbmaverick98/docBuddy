"""
x402 HTTP client for DocsBuddy
Manual implementation compatible with Python 3.9
Follows x402 protocol specification v1 and v2
"""
import os
import requests
import json
import time
import base64
from typing import Dict, List, Optional

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception as e:
    print(f"⚠️  Could not load .env file: {e}")

# Import web3 and ethereum functionality
WEB3_AVAILABLE = False
try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
    WEB3_AVAILABLE = True
except ImportError as e:
    WEB3_AVAILABLE = False
    print(f"⚠️ eth_account not available: {e}")
    Account = None
    encode_defunct = None

class X402Client:
    """HTTP-based x402 client for DocsBuddy - Python 3.9 compatible"""

    def __init__(self, protocol_version: int = 2):
        self.service_url = os.getenv('X402_SERVICE_URL', 'http://localhost:3000')  # Updated to default port 3000
        self.facilitator_url = os.getenv('X402_FACILITATOR_URL', 'https://open.x402.host')
        self.network = os.getenv('X402_NETWORK', 'base')
        self.protocol_version = protocol_version  # Default to v2, can fallback to v1

        # Wallet for payments (DocsBuddy's wallet)
        self.private_key = os.getenv('X402_WALLET_PRIVATE_KEY')
        self.wallet_address = os.getenv('X402_WALLET_ADDRESS')

        if not WEB3_AVAILABLE:
            raise Exception("eth_account not installed. Install with: pip install eth-account")

        if not self.private_key:
            raise Exception("X402_WALLET_PRIVATE_KEY not set in .env file")

        try:
            # Create account from private key
            if WEB3_AVAILABLE and Account:
                self.account = Account.from_key(self.private_key)
            else:
                raise Exception("Web3 not available")
            
            # Verify wallet address matches
            if self.wallet_address and self.account.address.lower() != self.wallet_address.lower():
                print(f"⚠️  Wallet address mismatch: {self.account.address} != {self.wallet_address}")
            
            print(f"✅ x402 wallet configured successfully (v{protocol_version} protocol)")
        except Exception as e:
            print(f"❌ Error creating x402 client: {e}")
            raise Exception(f"Failed to initialize x402 client: {e}")

    def _generate_payment_payload(self, amount: str, recipient_address: Optional[str] = None) -> Dict:
        """Generate x402 payment payload following the protocol spec"""
        timestamp = int(time.time())

        # Build payload with all required fields
        # CRITICAL: Use addresses in their original format (checksum) - don't convert to lowercase
        # The message must match byte-for-byte when signing and verifying
        payload = {
            'amount': str(amount),  # Ensure string format
            'client_address': self.account.address,  # Keep checksum format (e.g., "0xBA4A3e4b89e004c0F7A8cb862266703A71B973Cd")
            'currency': 'USDC',
            'network': self.network,
            'scheme': 'exact',
            'timestamp': timestamp,
        }
        
        # Include recipient_address if provided (required for payment signing)
        # Keep original casing - don't convert to lowercase
        if recipient_address:
            payload['recipient_address'] = recipient_address

        # Create message for signing - sort keys alphabetically (matches x402 spec)
        # Use json.dumps with sort_keys=True - this handles sorting automatically
        # separators=(',', ':') ensures compact JSON (no spaces) to match server
        message = json.dumps(payload, separators=(',', ':'), sort_keys=True)

        # Sign the message using Ethereum message signing (matches x402 spec)
        if WEB3_AVAILABLE and self.account and encode_defunct:
            try:
                # Log what we're signing (for debugging)
                print(f"📝 Signing payment message:")
                print(f"   Message: {message}")
                print(f"   Message length: {len(message)} bytes")
                print(f"   Wallet address: {self.account.address}")
                print(f"   Recipient address: {recipient_address or 'N/A'}")
                
                # encode_defunct creates: "\x19Ethereum Signed Message:\n" + len(message) + message
                if encode_defunct is None:
                    raise Exception("encode_defunct not available")
                message_hash = encode_defunct(text=message)
                signed_message = self.account.sign_message(message_hash)
                payload['signature'] = signed_message.signature.hex()
                
                # Add debug info (for troubleshooting - remove in production)
                import hashlib
                message_hash_hex = hashlib.sha256(message.encode()).hexdigest()
                print(f"🔐 Message SHA256: {message_hash_hex[:16]}...")
                print(f"🔐 Signature: {payload['signature'][:20]}...")
                print(f"🔐 Signed payment: {amount} {payload['currency']} to {recipient_address or 'N/A'}")
            except Exception as e:
                print(f"⚠️  Failed to sign payment: {e}")
                raise Exception(f"Payment signing failed: {e}")

        return payload

    def _generate_payment_payload_v2(self, amount: str, recipient_address: str) -> Dict:
        """Generate x402 v2 payment payload following EIP-712 structure"""
        current_time = int(time.time())
        valid_after = str(current_time)
        valid_before = str(current_time + 300)  # 5 minutes validity
        nonce = str(int(time.time() * 1000))  # Unique nonce

        # Build EIP-712 authorization structure
        authorization = {
            'from': self.account.address,  # Keep checksum format
            'to': recipient_address,       # Keep checksum format  
            'value': str(amount),
            'validAfter': valid_after,
            'validBefore': valid_before,
            'nonce': nonce
        }

        # Build v2 payload structure
        payload_v2 = {
            'x402Version': 2,
            'scheme': 'exact',
            'network': self.network,
            'payload': {
                'authorization': authorization
            }
        }

        # Create message for EIP-712 signing (simplified version)
        message = json.dumps({
            'from': authorization['from'],
            'to': authorization['to'],
            'value': authorization['value'],
            'validAfter': authorization['validAfter'],
            'validBefore': authorization['validBefore'],
            'nonce': authorization['nonce']
        }, separators=(',', ':'))

        # Sign the message using Ethereum message signing
        if WEB3_AVAILABLE and self.account and encode_defunct:
            try:
                print(f"📝 Signing v2 payment message:")
                print(f"   Message: {message}")
                print(f"   Message length: {len(message)} bytes")
                print(f"   Wallet address: {self.account.address}")
                print(f"   Recipient address: {recipient_address}")
                
                message_hash = encode_defunct(text=message)
                signed_message = self.account.sign_message(message_hash)
                payload_v2['payload']['signature'] = signed_message.signature.hex()
                
                # Add debug info
                import hashlib
                message_hash_hex = hashlib.sha256(message.encode()).hexdigest()
                print(f"🔐 Message SHA256: {message_hash_hex[:16]}...")
                print(f"🔐 Signature: {payload_v2['payload']['signature'][:20]}...")
                print(f"🔐 Signed v2 payment: {amount} USDC to {recipient_address}")
            except Exception as e:
                print(f"⚠️  Failed to sign v2 payment: {e}")
                raise Exception(f"V2 payment signing failed: {e}")
        else:
            raise Exception("Web3 not available for v2 payment signing")

        return payload_v2

    def _make_payment_request(self, endpoint: str, data: Dict, timeout: int = 120) -> Dict:
        """
        Make request with x402 payment verification - follows x402 protocol v1/v2
        
        Args:
            endpoint: API endpoint path
            data: Request payload
            timeout: Request timeout in seconds (default: 120 for long K2 responses)
        """
        url = f"{self.service_url}{endpoint}"
        
        # First request - no payment header (x402 protocol)
        headers = {
            'Content-Type': 'application/json',
        }

        protocol_name = f"v{self.protocol_version}"
        print(f"💳 Making x402 request: {endpoint} ({protocol_name} protocol, timeout={timeout}s)")

        try:
            # First request - server will return 402 with payment requirements
            response = requests.post(url, json=data, headers=headers, timeout=timeout)

            if response.status_code == 402:
                # Payment required - extract payment details from 402 response
                payment_info = response.json()
                print(f"💰 Payment required: {payment_info}")

                # Try v2 format first, then fallback to v1
                if self.protocol_version == 2 and 'accepts' in payment_info and payment_info['accepts']:
                    # x402 v2 response format
                    payment_requirements = payment_info['accepts'][0]  # Take first payment option
                    
                    if not payment_requirements:
                        raise Exception(f"Invalid v2 402 response - missing payment requirements: {payment_info}")

                    required_amount = payment_requirements.get('maxAmountRequired')
                    recipient_address = payment_requirements.get('payTo')

                    print(f"🔄 Creating v2 signed payment: {required_amount} USDC to {recipient_address}")

                    # Create signed v2 payment payload
                    signed_payload_v2 = self._generate_payment_payload_v2(required_amount, recipient_address)
                    
                    # Add PAYMENT-SIGNATURE header for retry (base64 encoded)
                    headers['PAYMENT-SIGNATURE'] = base64.b64encode(
                        json.dumps(signed_payload_v2).encode()
                    ).decode()

                else:
                    # x402 v1 fallback response format
                    payment_required = payment_info.get('payment_required', {})
                    required_amount = payment_required.get('amount')
                    recipient_address = payment_required.get('recipient_address')

                    if not required_amount or not recipient_address:
                        raise Exception(f"Invalid v1 402 response - missing payment details: {payment_info}")

                    print(f"🔄 Creating v1 signed payment: {required_amount} USDC to {recipient_address}")

                    # Create signed v1 payment payload
                    signed_payload = self._generate_payment_payload(required_amount, recipient_address)

                    # Add X402-Payment header for retry
                    headers['X402-Payment'] = json.dumps(signed_payload)

                # Retry request with signed payment
                print(f"🔄 Retrying request with signed {protocol_name} payment...")
                retry_response = requests.post(url, json=data, headers=headers, timeout=timeout)

                if retry_response.status_code == 200:
                    result = retry_response.json()
                    print(f"✅ {protocol_name} payment signed and accepted, received response")
                    return result
                else:
                    error_text = retry_response.text
                    raise Exception(f"Signed {protocol_name} payment rejected: {retry_response.status_code} - {error_text}")

            elif response.status_code == 200:
                # Free request - no payment needed
                result = response.json()
                print(f"✅ Free request successful, received response")
                return result
            else:
                error_text = response.text
                raise Exception(f"x402 request failed: {response.status_code} - {error_text}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"x402 network error: {e}")

    def k2_generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        Call K2 via x402 service
        
        Uses longer timeout (180s) for K2 requests as they can generate long responses
        """
        result = self._make_payment_request('/v1/k2/chat/completions', {
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens,
            'temperature': temperature,
        }, timeout=180)  # 3 minutes for K2 responses

        return result['choices'][0]['message']['content']

    def cohere_rerank(self, query: str, documents: List[str], top_n: int = 5) -> List[Dict]:
        """Call Cohere rerank via x402 service"""
        result = self._make_payment_request('/v1/cohere/rerank', {
            'query': query,
            'documents': documents,
            'top_n': top_n,
        })

        return result['results']

    def cohere_chat(self, message: str, max_tokens: int = 100, temperature: float = 0.2) -> str:
        """Call Cohere chat via x402 service"""
        result = self._make_payment_request('/v1/cohere/chat', {
            'message': message,
            'max_tokens': max_tokens,
            'temperature': temperature,
        })

        return result['text']

    def cohere_embed(self, texts: List[str], model: str = 'embed-multilingual-v3.0',
                     input_type: str = 'search_document') -> List[List[float]]:
        """Call Cohere embed via x402 service"""
        result = self._make_payment_request('/v1/cohere/embed', {
            'texts': texts,
            'model': model,
            'input_type': input_type,
        })

        return result['embeddings']

    def set_protocol_version(self, version: int):
        """Switch between v1 and v2 protocol"""
        if version not in [1, 2]:
            raise ValueError("Protocol version must be 1 or 2")
        self.protocol_version = version
        print(f"🔄 Switched to x402 v{version} protocol")

    def test_connection(self) -> bool:
        """Test connection to x402 service"""
        try:
            response = requests.get(f"{self.service_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                version = health_data.get('version', 'unknown')
                print(f"🩺 Connected to x402 service v{version}")
                return True
            return False
        except Exception as e:
            print(f"❌ Failed to connect to x402 service: {e}")
            return False

    def get_service_health(self) -> Dict:
        """Get detailed health information from x402 service"""
        try:
            response = requests.get(f"{self.service_url}/health/services", timeout=5)
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            print(f"❌ Failed to get x402 service health: {e}")
            return {}

# Usage example
if __name__ == "__main__":
    # Initialize x402 client (defaults to v2)
    client = X402Client(protocol_version=2)
    
    # Test connection
    if client.test_connection():
        print("✅ x402 service is healthy")
        
        # Get detailed health
        health = client.get_service_health()
        print(f"🩺 Service health: {health}")
        
        # Test a simple request
        try:
            result = client.cohere_chat("Hello, this is a test message", max_tokens=50)
            print(f"✅ Test successful: {result[:100]}...")
        except Exception as e:
            print(f"❌ Test failed: {e}")
    else:
        print("❌ x402 service is not available")
