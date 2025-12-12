"""
Journey generation service
Takes user goal → searches docs → generates step-by-step journey
Now with LlamaIndex RAG, intent extraction, and prompt chaining
"""
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from indexer.vector_store import VectorStore
from services.rag_engine import RAGEngine
from services.intent_extractor import IntentExtractor
from services.prompt_chain import PromptChain
from services.llm_service import get_llm_service
from services.x402_client import X402Client

load_dotenv()


class JourneyGenerator:
    def __init__(
        self,
        collection_name: str = "docs",
        use_rag: bool = True,
        temperature: float = 0.7,
        model_name: str = "claude"
    ):
        """
        Initialize journey generator

        Args:
            collection_name: ChromaDB collection name
            use_rag: Use LlamaIndex RAG engine (default: True)
            temperature: Temperature for journey generation (0.0-1.0)
            model_name: LLM model to use ("claude", "hf-k2-openai")
        """
        self.use_rag = use_rag
        self.temperature = temperature
        self.model_name = model_name

        # Initialize x402 client for payment-enabled services
        self.x402_client = X402Client()
        
        if use_rag:
            # Use LlamaIndex-powered RAG engine
            try:
                self.rag_engine = RAGEngine(collection_name=collection_name, x402_client=self.x402_client)
                self.vector_store = None
            except Exception as e:
                print(f"⚠️  Failed to initialize RAG engine: {e}")
                print("   Falling back to direct vector store")
                self.use_rag = False
                self.vector_store = VectorStore(collection_name=collection_name, x402_client=self.x402_client)
                self.rag_engine = None
        else:
            # Use direct vector store (legacy)
            self.vector_store = VectorStore(collection_name=collection_name, x402_client=self.x402_client)
            self.rag_engine = None
        
        # Initialize intent extractor
        self.intent_extractor = IntentExtractor(model_name=model_name, x402_client=self.x402_client)

        # Initialize prompt chain
        self.prompt_chain = PromptChain(temperature=temperature, model_name=model_name, x402_client=self.x402_client)

        # Use selected model for journey generation
        if model_name == "hf-k2-openai":
            # Will use x402 client
            self.llm = None
        else:
        self.llm = get_llm_service(model_name)
    
    def generate_journey(
        self,
        user_query: str,
        max_steps: int = 10
    ) -> Dict:
        """
        Generate a step-by-step journey from user query
        Simplified: Search → LLM generates steps → Validate

        Args:
            user_query: User's goal (e.g., "I want to set up authentication")
            max_steps: Maximum number of steps to generate

        Returns:
            Dict with goal, steps, etc.
        """

        print("🚀 Starting journey generation with x402 payments...")

        # Step 1: Extract intent (x402 payment)
        print("💰 Step 1: Extracting intent (x402 payment required)...")
        intent = self.intent_extractor.extract_intent(user_query)
        print(f"✅ Intent extracted: {intent.get('goal')}")
        # 💰 Payment: $0.50 USDC (if using K2)

        # Step 2: Search for relevant docs (x402 payments)
        print("💰 Step 2: Searching docs with RAG (x402 payments required)...")
        if self.use_rag:
            docs = self._search_with_rag(user_query, intent, top_k=25)  # More docs for better context
        else:
            docs = self._search_relevant_docs(user_query, top_k=25)

        if not docs:
            return {'error': 'No relevant documentation found'}

        print(f"✅ Found {len(docs)} docs")
        # 💰 Total Payments: ~$0.17 USDC (embed + chat + rerank)

        # Step 3: Generate journey with LLM (x402 payment)
        print("💰 Step 3: Generating steps (x402 payment required)...")
        steps = self._generate_steps_with_llm(user_query, intent, docs, max_steps)

        if not steps:
            return {'error': 'Failed to generate steps'}

        # Step 4: Validate and clean up
        print("✅ Step 4: Validating steps (no payment)...")
        validated_steps = self._validate_steps(steps, docs)

        # Total x402 Payments: ~$1.17 USDC per journey

        response_data = {
            'goal': user_query,
            'intent': intent,  # Store intent for step detail
            'steps': validated_steps,
            'total_steps': len(validated_steps),
            'estimated_time': self._estimate_total_time(validated_steps),
            'enhanced_context': {
                'docs': docs,  # Store the enhanced RAG docs for step detail
                'query': user_query,
                'intent': intent,
                'model': self.model_name  # Store selected model for use in step details/chat
            }
        }

        # Debug: Validate response structure and check for serialization issues
        print(f"📦 Response structure: goal='{response_data['goal'][:50]}...', steps={len(response_data['steps'])}, model={response_data['enhanced_context']['model']}")

        # Sanitize the docs to ensure JSON serializability
        try:
            import json
            # Test full serialization
            json_str = json.dumps(response_data, default=str)
            print(f"✅ Full response JSON serializable, size: {len(json_str)} chars")
        except Exception as e:
            print(f"❌ JSON serialization failed: {e}")
            # Sanitize the docs by converting them to simple dicts
            sanitized_docs = []
            for doc in response_data['enhanced_context']['docs']:
                try:
                    # Try to create a clean dict with only serializable fields
                    clean_doc = {
                        'doc_path': doc.get('doc_path', ''),
                        'doc_url': doc.get('doc_url', ''),
                        'doc_title': doc.get('doc_title', ''),
                        'heading': doc.get('heading', ''),
                        'content': str(doc.get('content', ''))[:500],  # Ensure content is string
                        'distance': float(doc.get('distance', 1.0)) if doc.get('distance') is not None else 1.0
                    }
                    sanitized_docs.append(clean_doc)
                except Exception as doc_error:
                    print(f"⚠️ Skipping problematic doc: {doc_error}")
                    continue

            response_data['enhanced_context']['docs'] = sanitized_docs
            print(f"📝 Sanitized {len(sanitized_docs)} docs")

            # Test serialization again
            try:
                json_str = json.dumps(response_data, default=str)
                print(f"✅ Sanitized response JSON serializable, size: {len(json_str)} chars")
            except Exception as retry_error:
                print(f"❌ Even sanitized response failed: {retry_error}")
                # Last resort: remove docs entirely
                response_data['enhanced_context']['docs'] = []
                print("📝 Removed docs entirely as last resort")

        return response_data