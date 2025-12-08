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
        
        if use_rag:
            # Use LlamaIndex-powered RAG engine
            try:
                self.rag_engine = RAGEngine(collection_name=collection_name)
                self.vector_store = None
            except Exception as e:
                print(f"⚠️  Failed to initialize RAG engine: {e}")
                print("   Falling back to direct vector store")
                self.use_rag = False
                self.vector_store = VectorStore(collection_name=collection_name)
                self.rag_engine = None
        else:
            # Use direct vector store (legacy)
            self.vector_store = VectorStore(collection_name=collection_name)
            self.rag_engine = None
        
        # Initialize intent extractor
        self.intent_extractor = IntentExtractor(model_name=model_name)

        # Initialize prompt chain
        self.prompt_chain = PromptChain(temperature=temperature, model_name=model_name)

        # Use selected model for journey generation
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

        # Step 1: Extract intent
        print(f"🧠 Extracting intent...")
        intent = self.intent_extractor.extract_intent(user_query)
        print(f"✅ Intent: {intent.get('goal')}")
        print(f"🔍 Intent keys: {list(intent.keys()) if isinstance(intent, dict) else type(intent)}")

        # Step 2: Search for relevant docs
        print(f"🔍 Searching docs...")
        if self.use_rag:
            docs = self._search_with_rag(user_query, intent, top_k=25)  # More docs for better context
        else:
            docs = self._search_relevant_docs(user_query, top_k=25)

        if not docs:
            return {'error': 'No relevant documentation found'}

        print(f"✅ Found {len(docs)} docs")
        # Debug: Show available doc paths
        available_paths = [doc['doc_path'] for doc in docs]

        # Step 3: Generate journey with LLM
        print(f"🧠 Generating steps...")
        steps = self._generate_steps_with_claude(user_query, intent, docs, max_steps)

        if not steps:
            return {'error': 'Failed to generate steps'}

        # Step 4: Validate and clean up
        print(f"✅ Validating {len(steps)} steps...")
        validated_steps = self._validate_steps(steps, docs)

        # Step 5: Response
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
    
    def _search_with_rag(
        self,
        query: str,
        intent: Dict,
        top_k: int = 20
    ) -> List[Dict]:
        """
        Search using LlamaIndex RAG engine with intent
        
        Args:
            query: Search query
            intent: Extracted intent
            top_k: Number of results
        
        Returns:
            List of doc chunks
        """
        results = self.rag_engine.query_with_intent(query, intent, top_k=top_k)
        
        # Format results to match expected structure
        formatted = []
        seen_docs = set()
        
        for result in results:
            metadata = result.get('metadata', {})
            doc_path = metadata.get('doc_path', '')
            heading = metadata.get('heading', '')
            
            # Avoid duplicates
            key = f"{doc_path}:{heading}"
            if key not in seen_docs:
                seen_docs.add(key)
                formatted.append({
                    'doc_path': doc_path,
                    'doc_url': metadata.get('doc_url', ''),
                    'doc_title': metadata.get('doc_title', ''),
                    'heading': heading,
                    'content': result.get('content', '')[:500],
                    'distance': 1 - (result.get('score', 0) or 0)  # Convert score to distance
                })
        
        return formatted
    
    def _search_relevant_docs(self, query: str, top_k: int = 20) -> List[Dict]:
        """
        Search vector store for relevant documentation
        
        Returns:
            List of doc chunks with metadata
        """
        results = self.vector_store.search(query, n_results=top_k)
        
        # Format results
        formatted = []
        seen_docs = set()
        
        for result in results:
            doc_path = result['metadata'].get('doc_path', '')
            doc_url = result['metadata'].get('doc_url', '')
            doc_title = result['metadata'].get('doc_title', '')
            heading = result['metadata'].get('heading', '')
            
            # Avoid duplicates (same doc_path + heading)
            key = f"{doc_path}:{heading}"
            if key not in seen_docs:
                seen_docs.add(key)
                formatted.append({
                    'doc_path': doc_path,
                    'doc_url': doc_url,
                    'doc_title': doc_title,
                    'heading': heading,
                    'content': result['content'][:500],  # First 500 chars for context
                    'distance': result.get('distance')
                })
        
        return formatted
    
    def _generate_steps_with_claude(
        self,
        user_query: str,
        intent: Dict,
        docs: List[Dict],
        max_steps: int
    ) -> List[Dict]:
        """
        Generate journey steps with better LLM prompting
        """
        docs_text = self._format_docs_for_prompt(docs)

        prompt = f"""You are a technical writer creating step-by-step guides from documentation.

USER GOAL: {user_query}

AVAILABLE DOCS:
{docs_text}

Create a clear step-by-step guide. For each step:
- Choose the MOST RELEVANT docs from the list above
- Reference exact doc_path values shown in the "Path:" field
- Include the corresponding doc_url from the "URL:" field for each doc_path
- Make sure docs actually match the step content

Return ONLY JSON:
{{
  "steps": [
    {{
      "step_number": 1,
      "title": "Clear step title",
      "description": "What this step does",
      "doc_paths": ["/exact/path/from/list.md"],
      "doc_urls": ["https://docs.privy.io/exact/path"],
      "prerequisites": [],
      "estimated_time": "5 min",
      "complexity": "beginner"
    }}
  ]
}}

Rules:
- Use 3-8 steps maximum
- Each step needs 1-2 most relevant docs
- Use EXACT doc_paths and doc_urls as shown in the AVAILABLE DOCS section above
- Both doc_paths and doc_urls arrays must be populated for each step
- Make sure docs are actually about the step topic"""

        try:
            response = self.llm.generate(prompt=prompt, max_tokens=3000, temperature=0.3)
            response = response.strip()

            # Extract JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()

            data = json.loads(response)
            steps = data.get('steps', [])
            print(f"✅ Generated {len(steps)} steps")
            return steps

        except Exception as e:
            print(f"❌ LLM error: {e}")
            return []
    
    def _format_docs_for_prompt(self, docs: List[Dict]) -> str:
        """
        Format docs list for Claude prompt
        """
        formatted = []
        for i, doc in enumerate(docs, 1):
            formatted.append(
                f"{i}. {doc['doc_title']} - {doc['heading']}\n"
                f"   Path: {doc['doc_path']}\n"
                f"   URL: {doc['doc_url']}\n"
                f"   Preview: {doc['content'][:200]}..."
            )
        return "\n\n".join(formatted)
    
    
    def _validate_steps(
        self,
        steps: List[Dict],
        available_docs: List[Dict]
    ) -> List[Dict]:
        """
        Validate that referenced docs exist in vector store

        Args:
            steps: Generated steps from Claude
            available_docs: Docs that were found in search

        Returns:
            Validated steps (invalid references removed)
        """
        # Create lookup maps for available docs
        available_path_to_doc = {doc['doc_path']: doc for doc in available_docs}
        available_url_to_doc = {doc['doc_url']: doc for doc in available_docs}

        validated = []

        for step in steps:
            # Validate doc_paths and populate corresponding URLs
            valid_paths = []
            valid_urls = []

            doc_paths = step.get('doc_paths', [])
            doc_urls = step.get('doc_urls', [])

            # Check each path and populate corresponding URL
            for path in doc_paths:
                if path in available_path_to_doc:
                    valid_paths.append(path)
                    # Add the corresponding URL if not already present
                    corresponding_url = available_path_to_doc[path]['doc_url']
                    if corresponding_url and corresponding_url not in valid_urls:
                        valid_urls.append(corresponding_url)
                else:
                    print(f"  ⚠️  Invalid doc_path: {path} (not in available docs)")

            # Check each URL (in case LLM provided URLs directly)
            for url in doc_urls:
                if url in available_url_to_doc:
                    if url not in valid_urls:
                        valid_urls.append(url)
                    # Add corresponding path if not already present
                    corresponding_path = available_url_to_doc[url]['doc_path']
                    if corresponding_path and corresponding_path not in valid_paths:
                        valid_paths.append(corresponding_path)

            # Only include step if it has at least one valid reference
            if valid_paths or valid_urls:
                step['doc_paths'] = valid_paths
                step['doc_urls'] = valid_urls
                validated.append(step)
            else:
                print(f"  ⚠️  Skipping step '{step.get('title')}' - no valid doc references")

        return validated
    
    def _estimate_total_time(self, steps: List[Dict]) -> str:
        """
        Estimate total time for journey
        """
        total_minutes = 0
        
        for step in steps:
            time_str = step.get('estimated_time', '0 min')
            # Extract number from "5 min" or "10 min"
            try:
                minutes = int(time_str.split()[0])
                total_minutes += minutes
            except:
                pass
        
        if total_minutes < 60:
            return f"{total_minutes} min"
        else:
            hours = total_minutes // 60
            mins = total_minutes % 60
            return f"{hours}h {mins}min" if mins > 0 else f"{hours}h"

