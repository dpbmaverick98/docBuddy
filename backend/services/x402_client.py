"""
x402 HTTP client for DocsBuddy
Makes payment-enabled requests to x402 AI service
"""
import os
import requests
import json
import time
from typing import Dict, List, Optional

# Optional imports for web3 and ethereum functionality
try:
    from web3 import Web3
    from eth_account.account import Account
    from eth_account.messages import encode_defunct
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    print("⚠️ web3 library not available - wallet functionality disabled")

# Optional imports for fallbacks
try:
    import cohere
    COHERE_AVAILABLE = True
except ImportError:
    COHERE_AVAILABLE = False
    print("⚠️ Cohere library not available for fallback")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI library not available for fallback")

class X402Client:
    """HTTP-based x402 client for DocsBuddy"""

    def __init__(self):
        self.service_url = os.getenv('X402_SERVICE_URL', 'http://localhost:3000')
        self.facilitator_url = os.getenv('X402_FACILITATOR_URL', 'https://open.x402.host')
        self.network = os.getenv('X402_NETWORK', 'base')

        # Wallet for payments (DocsBuddy's wallet)
        self.private_key = os.getenv('X402_WALLET_PRIVATE_KEY')
        self.wallet_address = os.getenv('X402_WALLET_ADDRESS')

        if WEB3_AVAILABLE and self.private_key:
            self.account = Account.from_key(self.private_key)
        elif not WEB3_AVAILABLE:
            print("⚠️  web3 not available - wallet functionality disabled")
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

        # Sign the message if web3 is available
        if WEB3_AVAILABLE and hasattr(self, 'account') and self.account:
            try:
                signature = self.account.sign_message(
                    encode_defunct(text=message)
                )
                payload['signature'] = signature.signature.hex()
            except Exception as e:
                print(f"⚠️  Failed to sign payment: {e}")
                payload['signature'] = ''
        elif not WEB3_AVAILABLE:
            print("⚠️  web3 not available - payment signature disabled")
            payload['signature'] = ''
        else:
            print("⚠️  No wallet configured - payment signature missing")
            payload['signature'] = ''

        return payload

    def _make_payment_request(self, endpoint: str, data: Dict, amount: str) -> Dict:
        """Make request with x402 payment verification"""
        payment_payload = self._generate_payment_payload(amount)

        headers = {
            'Content-Type': 'application/json',
            'X402-Payment': json.dumps(payment_payload),
        }

        print(f"💳 Making x402 payment request: {endpoint} (${amount}¢)")

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
            # Return None to trigger fallback mechanism
            return None

    def k2_generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """Call K2 via x402 service with fallback to direct API"""
        cost = os.getenv('X402_K2_CHAT_COST', '50')  # Default $0.50

        try:
            result = self._make_payment_request('/v1/k2/chat/completions', {
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': max_tokens,
                'temperature': temperature,
            }, cost)

            if result:
                return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"⚠️ x402 K2 request failed, falling back to direct API: {e}")

        # Fallback to direct HuggingFace API
        try:
            import openai
            client = openai.OpenAI(
                base_url="https://router.huggingface.co/v1",
                api_key=os.getenv('HF_TOKEN')
            )
            completion = client.chat.completions.create(
                model="moonshotai/Kimi-K2-Instruct:novita",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            print("✅ Fallback to direct K2 API successful")
            return completion.choices[0].message.content.strip()
        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")
            raise Exception("Both x402 and direct K2 API failed")

    def cohere_rerank(self, query: str, documents: List[str], top_n: int = 5) -> List[Dict]:
        """Call Cohere rerank via x402 service with fallback"""
        cost = os.getenv('X402_COHERE_RERANK_COST', '10')  # Default $0.10

        try:
            result = self._make_payment_request('/v1/cohere/rerank', {
                'query': query,
                'documents': documents,
                'top_n': top_n,
            }, cost)

            if result:
                return result['results']
        except Exception as e:
            print(f"⚠️ x402 Cohere rerank failed, falling back to direct API: {e}")

        # Fallback to direct Cohere API
        if COHERE_AVAILABLE:
            try:
                client = cohere.Client(api_key=os.getenv('COHERE_API_KEY'))
                response = client.rerank(
                    query=query,
                    documents=documents,
                    top_n=min(top_n, len(documents)),
                    model="rerank-english-v3.0"
                )
                print("✅ Fallback to direct Cohere rerank successful")
                return [{
                    "index": r.index,
                    "relevance_score": r.relevance_score,
                    "document": {"text": r.document.text if hasattr(r.document, 'text') else str(r.document)}
                } for r in response.results]
            except Exception as fallback_error:
                print(f"❌ Cohere rerank fallback failed: {fallback_error}")

        # Ultimate fallback: return documents with default scores
        print("⚠️ Using basic fallback for rerank (no Cohere API)")
        return [{"index": i, "relevance_score": 0.5, "document": {"text": doc}}
                for i, doc in enumerate(documents[:top_n])]

    def cohere_chat(self, message: str, max_tokens: int = 100, temperature: float = 0.2) -> str:
        """Call Cohere chat via x402 service with fallback"""
        cost = os.getenv('X402_COHERE_CHAT_COST', '5')  # Default $0.05

        try:
            result = self._make_payment_request('/v1/cohere/chat', {
                'message': message,
                'max_tokens': max_tokens,
                'temperature': temperature,
            }, cost)

            if result:
                return result['text']
        except Exception as e:
            print(f"⚠️ x402 Cohere chat failed, falling back to direct API: {e}")

        # Fallback to direct Cohere API
        if COHERE_AVAILABLE:
            try:
                client = cohere.Client(api_key=os.getenv('COHERE_API_KEY'))
                response = client.chat(
                    message=message,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                print("✅ Fallback to direct Cohere chat successful")
                return response.text
            except Exception as fallback_error:
                print(f"❌ Cohere chat fallback failed: {fallback_error}")

        raise Exception("Both x402 and direct Cohere chat API failed")

    def cohere_embed(self, texts: List[str], model: str = 'embed-multilingual-v3.0',
                     input_type: str = 'search_document') -> List[List[float]]:
        """Call Cohere embed via x402 service with fallback"""
        cost = os.getenv('X402_COHERE_EMBED_COST', '2')  # Default $0.02

        try:
            result = self._make_payment_request('/v1/cohere/embed', {
                'texts': texts,
                'model': model,
                'input_type': input_type,
            }, cost)

            if result:
                return result['embeddings']
        except Exception as e:
            print(f"⚠️ x402 Cohere embed failed, falling back to direct API: {e}")

        # Fallback to direct Cohere API
        if COHERE_AVAILABLE:
            try:
                client = cohere.Client(api_key=os.getenv('COHERE_API_KEY'))
                response = client.embed(
                    texts=texts,
                    model=model,
                    input_type=input_type
                )
                print("✅ Fallback to direct Cohere embed successful")
                return response.embeddings
            except Exception as fallback_error:
                print(f"❌ Cohere embed fallback failed: {fallback_error}")

        raise Exception("Both x402 and direct Cohere embed API failed")

    def test_connection(self) -> bool:
        """Test connection to x402 service"""
        try:
            response = requests.get(f"{self.service_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
