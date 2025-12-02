"""
Journey generation service
Takes user goal → searches docs → generates step-by-step journey
"""
import os
import json
from typing import List, Dict, Optional
from anthropic import Anthropic
from indexer.vector_store import VectorStore
from dotenv import load_dotenv

load_dotenv()


class JourneyGenerator:
    def __init__(self, collection_name: str = "docs"):
        """
        Initialize journey generator
        
        Args:
            collection_name: ChromaDB collection name
        """
        self.vector_store = VectorStore(collection_name=collection_name)
        
        # Initialize Claude
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self.claude = Anthropic(api_key=api_key)
        # Use correct model name for Anthropic messages API
        self.model = "claude-sonnet-4-5"  # Correct model name format
    
    def generate_journey(self, user_query: str, max_steps: int = 10) -> Dict:
        """
        Generate a step-by-step journey from user query
        
        Args:
            user_query: User's goal (e.g., "I want to set up authentication")
            max_steps: Maximum number of steps to generate
        
        Returns:
            Dict with journey_id, goal, steps, etc.
        """
        # Step 1: Search for relevant documentation
        print(f"🔍 Searching docs for: {user_query}")
        relevant_docs = self._search_relevant_docs(user_query, top_k=20)
        
        if not relevant_docs:
            return {
                'error': 'No relevant documentation found',
                'query': user_query
            }
        
        print(f"✅ Found {len(relevant_docs)} relevant doc sections")
        
        # Step 2: Generate journey steps using Claude
        print(f"🧠 Generating journey steps...")
        steps = self._generate_steps_with_claude(
            user_query=user_query,
            relevant_docs=relevant_docs,
            max_steps=max_steps
        )
        
        if not steps:
            return {
                'error': 'Failed to generate journey steps',
                'query': user_query
            }
        
        # Step 3: Validate steps (verify docs exist)
        print(f"✅ Validating {len(steps)} steps...")
        validated_steps = self._validate_steps(steps, relevant_docs)
        
        # Step 4: Format response
        journey = {
            'goal': user_query,
            'steps': validated_steps,
            'total_steps': len(validated_steps),
            'estimated_time': self._estimate_total_time(validated_steps)
        }
        
        return journey
    
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
        relevant_docs: List[Dict],
        max_steps: int
    ) -> List[Dict]:
        """
        Use Claude to generate ordered journey steps
        
        Returns:
            List of step dicts
        """
        # Format docs for prompt
        docs_text = self._format_docs_for_prompt(relevant_docs)
        
        prompt = f"""You are a documentation expert helping users navigate complex documentation.

User wants to: {user_query}

Available documentation sections:
{docs_text}

Create a step-by-step journey that helps the user achieve their goal. Each step should:
1. Reference specific documentation sections from the list above
2. Be in logical order (prerequisites first)
3. Include clear, actionable instructions
4. Reference exact doc_path values from the available sections

Return ONLY valid JSON in this exact format:
{{
  "steps": [
    {{
      "step_number": 1,
      "title": "Step title",
      "description": "Brief description of what this step covers",
      "doc_paths": ["/path/to/doc.md"],
      "doc_urls": ["https://docs.privy.io/path/to/doc.md"],
      "prerequisites": [],
      "estimated_time": "5 min",
      "complexity": "beginner"
    }}
  ]
}}

Rules:
- Only reference doc_paths that exist in the available sections above
- Steps should be ordered logically (dependencies first)
- Include 3-{max_steps} steps
- Each step should reference 1-3 relevant doc sections
- Prerequisites should reference step_numbers of previous steps
- Complexity: beginner, intermediate, or advanced
- Estimated time: realistic (e.g., "5 min", "10 min", "15 min")

Return ONLY the JSON, no other text."""

        try:
            # Use messages API (Anthropic SDK v0.34+)
            response = self.claude.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Extract text from response
            # Response structure: response.content is a list of TextBlock objects
            response_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    response_text += block.text
                elif isinstance(block, str):
                    response_text += block
            
            response_text = response_text.strip()
            
            # Try to extract JSON if wrapped in markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            journey_data = json.loads(response_text)
            return journey_data.get('steps', [])
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse Claude response as JSON: {e}")
            print(f"Response: {response_text[:500]}")
            return []
        except Exception as e:
            print(f"❌ Error calling Claude: {e}")
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
        # Create lookup for available docs
        available_paths = {doc['doc_path'] for doc in available_docs}
        available_urls = {doc['doc_url'] for doc in available_docs}
        
        validated = []
        
        for step in steps:
            # Validate doc_paths
            valid_paths = []
            valid_urls = []
            
            doc_paths = step.get('doc_paths', [])
            doc_urls = step.get('doc_urls', [])
            
            # Check each path
            for path in doc_paths:
                if path in available_paths:
                    valid_paths.append(path)
                else:
                    print(f"  ⚠️  Invalid doc_path: {path}")
            
            # Check each URL
            for url in doc_urls:
                if url in available_urls:
                    valid_urls.append(url)
            
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

