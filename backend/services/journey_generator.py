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
        self.prompt_chain = PromptChain(temperature=temperature, model_name=model_name)

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
    
    def _search_with_rag(self, user_query: str, intent: Dict, top_k: int = 25) -> List[Dict]:
        """
        Search for relevant docs using RAG engine with intent
        """
        if not self.rag_engine:
            raise Exception("RAG engine not initialized")
        
        return self.rag_engine.query_with_intent(
            query=user_query,
            intent=intent,
            top_k=top_k,
            use_cohere_optimizations=True
        )
    
    def _search_relevant_docs(self, user_query: str, top_k: int = 25) -> List[Dict]:
        """
        Search for relevant docs using vector store (non-RAG mode)
        """
        if not self.vector_store:
            raise Exception("Vector store not initialized")
        
        results = self.vector_store.search(query=user_query, n_results=top_k)
        return results
    
    def _generate_steps_with_llm(self, user_query: str, intent: Dict, docs: List[Dict], max_steps: int) -> List[Dict]:
        """
        Generate step-by-step journey using LLM
        """
        try:
            # Build context from docs
            context = ""
            for i, doc in enumerate(docs[:5]):  # Use top 5 docs for context
                context += f"\nDocument {i+1}: {doc.get('content', '')[:1000]}...\n"

            # Build prompt
            prompt = f"""Based on the user query and intent, generate a detailed step-by-step implementation guide.

User Query: {user_query}

User Intent: {intent}

Available Documentation:
{context}

Generate {max_steps} clear, actionable steps for implementing this feature. Each step should include:
- A clear title
- Detailed description of what to do
- Any prerequisites or dependencies
- Expected outcome

Format as JSON array:
[{{"step_number": 1, "title": "Step Title", "description": "Detailed description", "prerequisites": ["item1"], "outcome": "Expected result"}}]

Output only valid JSON:"""

            # Use x402 if available
            if self.model_name == "hf-k2-openai" and self.x402_client:
                print("💳 Generating steps with x402 K2 service...")
                response_text = self.x402_client.k2_generate(
                    prompt=prompt,
                    max_tokens=3000,
                    temperature=0.3
                )
                # 💰 x402 Payment: $0.50 USDC
                if response_text:
                    print("✅ Steps generated via x402")
                else:
                    print("⚠️ x402 failed, falling back to direct LLM")
                    response_text = self.llm.generate(
                        prompt=prompt,
                        max_tokens=3000,
                        temperature=0.3
                    )
            else:
                response_text = self.llm.generate(
                    prompt=prompt,
                    max_tokens=3000,
                    temperature=0.3
                )

            if not response_text:
                print("❌ No response from LLM")
                return []

            response_text = response_text.strip()
            
            # Log raw response for debugging (first 500 chars)
            print(f"📝 Raw K2 response (first 500 chars): {response_text[:500]}")

            # Try to extract JSON from markdown code blocks
            if "```json" in response_text:
                parts = response_text.split("```json")
                if len(parts) > 1:
                    json_part = parts[1].split("```")[0].strip()
                    if json_part:
                        response_text = json_part
            elif "```" in response_text:
                parts = response_text.split("```")
                if len(parts) > 1:
                    json_part = parts[1].split("```")[0].strip()
                    if json_part:
                        response_text = json_part
            
            # Try to find JSON array/object in the text
            # Look for first '[' or '{' and last ']' or '}'
            first_bracket = response_text.find('[')
            first_brace = response_text.find('{')
            
            if first_bracket != -1 and (first_brace == -1 or first_bracket < first_brace):
                # Array format
                last_bracket = response_text.rfind(']')
                if last_bracket != -1 and last_bracket > first_bracket:
                    response_text = response_text[first_bracket:last_bracket + 1]
            elif first_brace != -1:
                # Object format
                last_brace = response_text.rfind('}')
                if last_brace != -1 and last_brace > first_brace:
                    response_text = response_text[first_brace:last_brace + 1]

            # Parse JSON with better error handling
            try:
                steps = json.loads(response_text)
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error: {e}")
                print(f"📝 Attempted to parse: {response_text[:200]}...")
                print(f"📝 Full response length: {len(response_text)} chars")
                # Try to fix common JSON issues
                # Remove trailing commas before closing brackets/braces
                import re
                # Fix trailing commas in arrays/objects
                fixed_text = re.sub(r',\s*}', '}', response_text)
                fixed_text = re.sub(r',\s*]', ']', fixed_text)
                try:
                    steps = json.loads(fixed_text)
                    print("✅ Fixed JSON by removing trailing commas")
                except json.JSONDecodeError:
                    # If still fails, try to extract just the array part
                    print("⚠️  JSON parsing failed, attempting to extract valid JSON...")
                    raise Exception(f"Failed to parse JSON from K2 response. Error: {e}. Response preview: {response_text[:300]}")

            # Validate and clean steps
            validated_steps = []
            for i, step in enumerate(steps[:max_steps]):
                if isinstance(step, dict) and 'title' in step and 'description' in step:
                    # Extract doc_paths and doc_urls from top docs
                    top_docs = docs[:3]
                    doc_paths = [doc.get('doc_path', '') for doc in top_docs]
                    doc_urls = [doc.get('doc_url', '') for doc in top_docs]
                    
                    validated_step = {
                        'step_number': i + 1,
                        'title': step.get('title', f'Step {i+1}'),
                        'description': step.get('description', ''),
                        'prerequisites': step.get('prerequisites', []),
                        'outcome': step.get('outcome', ''),
                        'doc_paths': doc_paths,  # Link to top docs
                        'doc_urls': doc_urls     # URLs for display
                    }
                    validated_steps.append(validated_step)

            print(f"✅ Generated {len(validated_steps)} steps")
            return validated_steps

        except Exception as e:
            print(f"❌ Error generating steps: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _validate_steps(self, steps: List[Dict], docs: List[Dict]) -> List[Dict]:
        """
        Validate and clean up generated steps
        
        Args:
            steps: List of step dicts from LLM
            docs: List of relevant docs
            
        Returns:
            Validated and cleaned steps
        """
        validated_steps = []
        
        for i, step in enumerate(steps):
            if isinstance(step, dict) and 'title' in step and 'description' in step:
                # Preserve doc_paths and doc_urls if they exist, otherwise use top docs
                doc_paths = step.get('doc_paths', [doc.get('doc_path', '') for doc in docs[:3]])
                doc_urls = step.get('doc_urls', [doc.get('doc_url', '') for doc in docs[:3]])
                
                # Ensure step has all required fields
                validated_step = {
                    'step_number': step.get('step_number', i + 1),
                    'title': step.get('title', f'Step {i+1}'),
                    'description': step.get('description', ''),
                    'prerequisites': step.get('prerequisites', []),
                    'outcome': step.get('outcome', ''),
                    'doc_paths': doc_paths,
                    'doc_urls': doc_urls
                }
                validated_steps.append(validated_step)
        
        return validated_steps
    
    def _estimate_total_time(self, steps: List[Dict]) -> str:
        """
        Estimate total time to complete all steps
        
        Args:
            steps: List of step dicts
            
        Returns:
            Estimated time string (e.g., "30 minutes", "2 hours")
        """
        if not steps:
            return "0 minutes"
        
        # Rough estimate: 10-15 minutes per step on average
        # Adjust based on step complexity if available
        base_time_per_step = 12  # minutes
        
        total_minutes = len(steps) * base_time_per_step
        
        if total_minutes < 60:
            return f"{total_minutes} minutes"
        else:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            if minutes == 0:
                return f"{hours} hour{'s' if hours > 1 else ''}"
            else:
                return f"{hours} hour{'s' if hours > 1 else ''} {minutes} minutes"