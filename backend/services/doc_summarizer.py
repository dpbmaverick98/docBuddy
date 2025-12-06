"""
Documentation summarizer service
Generates summaries from doc content stored in vector DB
Uses Claude Sonnet 4.5
"""
from typing import List, Dict, Optional
from indexer.vector_store import VectorStore
from services.llm_service import ClaudeService
import hashlib
import json
from dotenv import load_dotenv

load_dotenv()


class DocSummarizer:
    # Class-level cache to persist across instances
    _summary_cache: Dict[str, Dict] = {}

    def __init__(self, collection_name: str = "docs", temperature: float = 0.3):
        """
        Initialize doc summarizer

        Args:
            collection_name: ChromaDB collection name
            temperature: Temperature for summarization (lower = more focused, default: 0.3)
        """
        self.vector_store = VectorStore(collection_name=collection_name)
        self.temperature = temperature

        # Use Claude for summarization
        self.llm = ClaudeService()
    
    def _get_cache_key(self, doc_path: str, max_length: int, doc_chunks: List[Dict], step_title: Optional[str] = None, step_description: Optional[str] = None) -> str:
        """
        Generate a cache key from doc_path, max_length, content hash, and step context

        Args:
            doc_path: Document path
            max_length: Maximum summary length
            doc_chunks: Document chunks used for summary
            step_title: Step title for context
            step_description: Step description for context

        Returns:
            Cache key string
        """
        # Create a hash of the first chunk's content to ensure cache key uniqueness
        content_hash = ""
        if doc_chunks:
            # Use first chunk's content and heading for cache key
            first_chunk_content = doc_chunks[0].get('content', '')[:500]  # First 500 chars
            first_chunk_heading = doc_chunks[0].get('heading', '')
            content_hash = hashlib.md5(
                f"{first_chunk_heading}:{first_chunk_content}".encode()
            ).hexdigest()[:8]

        # Include step context in cache key for step-specific summaries
        step_context = ""
        if step_title:
            step_context += step_title[:50]  # First 50 chars of title
        if step_description:
            step_context += step_description[:100]  # First 100 chars of description

        step_hash = hashlib.md5(step_context.encode()).hexdigest()[:8] if step_context else ""

        return f"{doc_path}:{max_length}:{content_hash}:{step_hash}"
    
    def get_summaries(
        self,
        doc_paths: List[str],
        max_length: int = 3000,
        step_title: Optional[str] = None,
        step_description: Optional[str] = None,
        step_number: Optional[int] = None
    ) -> List[Dict]:
        """
        Get summaries for multiple doc paths, tailored to a specific step theme

        Args:
            doc_paths: List of doc paths to summarize
            max_length: Maximum length of summary in characters
            step_title: Title of the step for context-aware summarization
            step_description: Description of the step for context-aware summarization
            step_number: Step number in the journey for context

        Returns:
            List of dicts with doc_path, summary, url, title
        """
        summaries = []
        
        for doc_path in doc_paths:
            try:
                # Create step-aware search query
                base_query = doc_path
                if step_title:
                    # Use step title to find more relevant chunks
                    base_query = f"{step_title} {doc_path}"

                # Search for doc content in vector store with step context
                # First try with filter
                results = self.vector_store.search(
                    query=base_query,
                    n_results=8,  # Get more results to filter by relevance
                    filter_metadata={"doc_path": doc_path}
                )

                # If no results with filter, try without filter and filter manually
                if not results:
                    all_results = self.vector_store.search(
                        query=base_query,
                        n_results=15  # Get more results when no filter
                    )
                    # Filter to only this doc_path
                    results = [
                        r for r in all_results
                        if r['metadata'].get('doc_path') == doc_path
                    ]
                
                if results:
                    # Get all chunks for this doc and rank them by relevance to step
                    all_chunks = []
                    seen_content = set()

                    for result in results:
                        content = result['content']
                        # Avoid duplicates
                        content_hash = content[:100]
                        if content_hash not in seen_content:
                            seen_content.add(content_hash)

                            chunk_data = {
                                'content': content,
                                'heading': result['metadata'].get('heading', ''),
                                'url': result['metadata'].get('doc_url', ''),
                                'title': result['metadata'].get('doc_title', ''),
                                'score': result.get('score', 0) or 0
                            }

                            all_chunks.append(chunk_data)

                    # Select most relevant chunks based on step context
                    doc_chunks = self._select_relevant_chunks(all_chunks, step_title, step_description)

                    if doc_chunks:
                        # Check cache first
                        cache_key = self._get_cache_key(doc_path, max_length, doc_chunks, step_title, step_description)
                        cached_summary = DocSummarizer._summary_cache.get(cache_key)

                        if cached_summary:
                            # Use cached summary
                            summaries.append(cached_summary)
                        else:
                            # Generate summary from chunks with step context
                            summary_text = self._generate_summary(doc_chunks, max_length, step_title, step_description, step_number)
                            
                            summary_data = {
                                'doc_path': doc_path,
                                'summary': summary_text,
                                'url': doc_chunks[0].get('url', ''),
                                'title': doc_chunks[0].get('title', ''),
                                'heading': doc_chunks[0].get('heading', '')
                            }
                            
                            # Store in cache
                            DocSummarizer._summary_cache[cache_key] = summary_data
                            summaries.append(summary_data)
                    else:
                        summaries.append({
                            'doc_path': doc_path,
                            'summary': f"Documentation available at {doc_path}",
                            'url': '',
                            'title': '',
                            'heading': ''
                        })
                else:
                    summaries.append({
                        'doc_path': doc_path,
                        'summary': f"Documentation not found: {doc_path}",
                        'url': '',
                        'title': '',
                        'heading': ''
                    })
                    
            except Exception as e:
                summaries.append({
                    'doc_path': doc_path,
                    'summary': f"Error generating summary: {str(e)}",
                    'url': '',
                    'title': '',
                    'heading': ''
                })
        
        return summaries
    
    def _generate_summary(
        self,
        doc_chunks: List[Dict],
        max_length: int,
        step_title: Optional[str] = None,
        step_description: Optional[str] = None,
        step_number: Optional[int] = None
    ) -> str:
        """
        Generate a summary from doc chunks using Claude, tailored to step context

        Args:
            doc_chunks: List of doc chunks with content
            max_length: Maximum summary length
            step_title: Title of the step for context
            step_description: Description of the step for context
            step_number: Step number in the journey

        Returns:
            Summary text
        """
        # Combine chunks (already selected for relevance)
        combined_content = "\n\n".join([
            f"## {chunk.get('heading', 'Content')}\n{chunk['content']}"
            for chunk in doc_chunks  # Use all selected relevant chunks
        ])
        
        # Calculate max_tokens based on max_length (roughly 4 chars per token, add buffer)
        # Ensure minimum of 500 tokens and maximum reasonable limit
        calculated_max_tokens = max(500, min(int(max_length / 3), 4000))
        
        # Increase input content limit for longer summaries
        input_limit = min(4000, max_length * 2) if max_length > 1000 else 2000
        
        # Build step context for the prompt
        step_context = ""
        if step_title or step_description:
            step_context = "\n\nSTEP CONTEXT:"
            if step_number:
                step_context += f"\nThis is Step {step_number} in a journey."
            if step_title:
                step_context += f"\nStep Title: {step_title}"
            if step_description:
                step_context += f"\nStep Description: {step_description}"
            step_context += "\n\nGenerate a summary specifically focused on what developers need to know for this step."

        prompt = f"""Summarize the following documentation section in {max_length} characters or less.{step_context}

Focus on WHAT DEVELOPERS NEED TO DO for this specific step:
- What code to write or configure
- What steps to take
- What APIs/functions to use
- What settings to change
- Practical implementation details

Write in an action-oriented, developer-focused style. Use imperative mood (e.g., "Set up...", "Configure...", "Call...", "Install...").

Documentation:
{combined_content[:input_limit]}

Provide a concise, actionable summary for developers implementing this step."""

        try:
            # Use Claude for summarization
            summary = self.llm.generate(
                prompt=prompt,
                max_tokens=calculated_max_tokens,
                temperature=self.temperature
            )
            
            summary = summary.strip()
            
            # Truncate if too long, preserving complete sentences
            if len(summary) > max_length:
                # Try to find a good sentence boundary
                truncated = summary[:max_length]
                # Look for sentence endings (., !, ?) near the end
                for punct in ['.', '!', '?', '\n']:
                    last_punct = truncated.rfind(punct)
                    if last_punct > max_length * 0.7:  # If found in last 30% of text
                        summary = truncated[:last_punct + 1].strip()
                        break
                else:
                    # No good sentence boundary found, try word boundary
                    last_space = truncated.rfind(' ')
                    if last_space > max_length * 0.8:  # If found in last 20% of text
                        summary = truncated[:last_space].strip() + '...'
                    else:
                        summary = truncated.strip() + '...'
            
            return summary
            
        except Exception as e:
            # Fallback: extract actionable content
            if doc_chunks:
                first_chunk = doc_chunks[0]['content']
                # Look for code blocks, commands, or action verbs
                lines = first_chunk.split('\n')
                action_lines = []
                
                for line in lines[:10]:  # Check first 10 lines
                    line_lower = line.lower().strip()
                    # Look for action-oriented content
                    if any(keyword in line_lower for keyword in [
                        'install', 'configure', 'set', 'create', 'add', 'use',
                        'call', 'import', 'export', 'run', 'execute', 'enable',
                        'disable', 'update', 'implement', 'initialize'
                    ]):
                        action_lines.append(line.strip())
                
                if action_lines:
                    summary = ' '.join(action_lines[:2])  # Take first 2 action lines
                    if len(summary) > max_length:
                        summary = summary[:max_length].rsplit('.', 1)[0] + '.'
                    return summary
                
                # Fallback to first sentence
                sentences = first_chunk.split('.')
                if sentences:
                    summary = sentences[0].strip() + '.'
                    if len(summary) > max_length:
                        summary = summary[:max_length]
                    return summary
            
            return f"See documentation for implementation details."

    def _select_relevant_chunks(
        self,
        chunks: List[Dict],
        step_title: Optional[str] = None,
        step_description: Optional[str] = None,
        max_chunks: int = 3
    ) -> List[Dict]:
        """
        Select the most relevant chunks based on step context

        Args:
            chunks: List of chunk dictionaries
            step_title: Step title for relevance scoring
            step_description: Step description for relevance scoring
            max_chunks: Maximum number of chunks to return

        Returns:
            List of most relevant chunks
        """
        if not step_title and not step_description:
            # No step context, return first chunks
            return chunks[:max_chunks]

        # Score chunks based on relevance to step
        scored_chunks = []
        step_keywords = set()

        # Extract keywords from step title and description
        if step_title:
            step_keywords.update(step_title.lower().split())
        if step_description:
            step_keywords.update(step_description.lower().split())

        # Remove common words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'}
        step_keywords = step_keywords - common_words

        for chunk in chunks:
            relevance_score = 0
            content_lower = chunk['content'].lower()
            heading_lower = chunk.get('heading', '').lower()

            # Score based on keyword matches in content and heading
            for keyword in step_keywords:
                if keyword in content_lower:
                    relevance_score += 2  # Content match is worth more
                if keyword in heading_lower:
                    relevance_score += 3  # Heading match is worth even more

            # Add original search score
            relevance_score += chunk.get('score', 0) * 10

            scored_chunks.append({
                **chunk,
                'relevance_score': relevance_score
            })

        # Sort by relevance score and return top chunks
        scored_chunks.sort(key=lambda x: x['relevance_score'], reverse=True)
        return scored_chunks[:max_chunks]

