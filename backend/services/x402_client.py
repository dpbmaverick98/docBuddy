"""
x402 HTTP client for DocsBuddy
Makes payment-enabled requests to x402 AI service
"""
import os
import requests
import json
import time
from typing import Dict, List, Optional
from web3 import Web3
from eth_account import Account

class X402Client:
    """HTTP-based x402 client for DocsBuddy"""

    def __init__(self):
        self.service_url = os.getenv('X402_SERVICE_URL', 'http://localhost:3000')
        self.facilitator_url = os.getenv('X402_FACILITATOR_URL', 'https://open.x402.host')
        self.network = os.getenv('X402_NETWORK', 'base')

        # Wallet for payments (DocsBuddy's wallet)
        self.private_key = os.getenv('X402_WALLET_PRIVATE_KEY')
        self.wallet_address = os.getenv('X402_WALLET_ADDRESS')

        if self.private_key:
            self.account = Account.from_key(self.private_key)
        else:
            print("⚠️  X402_WALLET_PRIVATE_KEY not set - payments will fail")

    def _generate_payment_payload(self, amount: str) -> Dict:
        """Generate x402 payment payload"""
        timestamp = int(time.time())

        payload = {
            'network': self.network,
            'scheme': 'exact',
            'amount': amount,
            'currency': 'USDC',
            'timestamp': timestamp,
            'client_address': self.wallet_address or '',
        }

        # Create message for signing
        message = json.dumps(payload, sort_keys=True, separators=(',', ':'))

        # Sign the message
        if self.account:
            signature = self.account.sign_message(
                encode_defunct(text=message)
            )
            payload['signature'] = signature.signature.hex()
        else:
            print("⚠️  No wallet configured - payment signature missing")

        return payload

    def _make_payment_request(self, endpoint: str, data: Dict, amount: str) -> Dict:
        """Make request with x402 payment verification"""
        payment_payload = self._generate_payment_payload(amount)

        headers = {
            'Content-Type': 'application/json',
            'X402-Payment': json.dumps(payment_payload),
        }

        print(f"💳 Making x402 payment request: {endpoint} (${amount}¢)")
        print(f"   Payload: {payment_payload}")

        try:
            response = requests.post(
                f"{self.service_url}{endpoint}",
                json=data,
                headers=headers,
                timeout=30
            )

            if response.status_code == 402:
                # Payment required - return the payment details
                payment_info = response.json()
                print(f"💰 Payment required: {payment_info}")
                raise Exception(f"Payment required: {payment_info}")

            response.raise_for_status()
            result = response.json()
            print(f"✅ Payment successful, received response")
            return result

        except requests.exceptions.RequestException as e:
            print(f"❌ x402 request failed: {e}")
            raise

    def k2_generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """Call K2 via x402 service"""
        cost = os.getenv('X402_K2_CHAT_COST', '50')  # Default $0.50

        result = self._make_payment_request('/v1/k2/chat/completions', {
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens,
            'temperature': temperature,
        }, cost)

        return result['choices'][0]['message']['content']

    def cohere_rerank(self, query: str, documents: List[str], top_n: int = 5) -> List[Dict]:
        """Call Cohere rerank via x402 service"""
        cost = os.getenv('X402_COHERE_RERANK_COST', '10')  # Default $0.10

        result = self._make_payment_request('/v1/cohere/rerank', {
            'query': query,
            'documents': documents,
            'top_n': top_n,
        }, cost)

        return result['results']

    def cohere_chat(self, message: str, max_tokens: int = 100, temperature: float = 0.2) -> str:
        """Call Cohere chat via x402 service"""
        cost = os.getenv('X402_COHERE_CHAT_COST', '5')  # Default $0.05

        result = self._make_payment_request('/v1/cohere/chat', {
            'message': message,
            'max_tokens': max_tokens,
            'temperature': temperature,
        }, cost)

        return result['text']

    def cohere_embed(self, texts: List[str], model: str = 'embed-multilingual-v3.0',
                     input_type: str = 'search_document') -> List[List[float]]:
        """Call Cohere embed via x402 service"""
        cost = os.getenv('X402_COHERE_EMBED_COST', '2')  # Default $0.02

        result = self._make_payment_request('/v1/cohere/embed', {
            'texts': texts,
            'model': model,
            'input_type': input_type,
        }, cost)

        return result['embeddings']

    def test_connection(self) -> bool:
        """Test connection to x402 service"""
        try:
            response = requests.get(f"{self.service_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False</contents>
</xai:function_call name="write">
<parameter name="file_path">/Users/dpbmaverick98/docsBuddy/docBuddy/backend/env.example
