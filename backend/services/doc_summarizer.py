"""
Documentation summarizer service
Generates summaries from doc content stored in vector DB
"""
from typing import List, Dict, Optional
from indexer.vector_store import VectorStore
from anthropic import Anthropic
import os
from dotenv import load_dotenv

load_dotenv()


class DocSummarizer:
    def __init__(self, collection_name: str = "docs"):
        """
        Initialize doc summarizer
        
        Args:
            collection_name: ChromaDB collection name
        """
        self.vector_store = VectorStore(collection_name=collection_name)
        
        # Initialize Claude for summarization
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self.claude = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5"
    
    def get_summaries(
        self,
        doc_paths: List[str],
        max_length: int = 3000
    ) -> List[Dict]:
        """
        Get summaries for multiple doc paths
        
        Args:
            doc_paths: List of doc paths to summarize
            max_length: Maximum length of summary in characters
        
        Returns:
            List of dicts with doc_path, summary, url, title
        """
        summaries = []
        
        for doc_path in doc_paths:
            try:
                # Search for doc content in vector store
                # First try with filter
                results = self.vector_store.search(
                    query=f"documentation about {doc_path}",
                    n_results=5,
                    filter_metadata={"doc_path": doc_path}
                )
                
                # If no results with filter, try without filter and filter manually
                if not results:
                    all_results = self.vector_store.search(
                        query=doc_path,
                        n_results=10
                    )
                    # Filter to only this doc_path
                    results = [
                        r for r in all_results
                        if r['metadata'].get('doc_path') == doc_path
                    ]
                
                if results:
                    # Get all chunks for this doc
                    doc_chunks = []
                    seen_content = set()
                    
                    for result in results:
                        content = result['content']
                        # Avoid duplicates
                        content_hash = content[:100]
                        if content_hash not in seen_content:
                            seen_content.add(content_hash)
                            doc_chunks.append({
                                'content': content,
                                'heading': result['metadata'].get('heading', ''),
                                'url': result['metadata'].get('doc_url', ''),
                                'title': result['metadata'].get('doc_title', '')
                            })
                    
                    if doc_chunks:
                        # Generate summary from chunks
                        summary = self._generate_summary(doc_chunks, max_length)
                        
                        summaries.append({
                            'doc_path': doc_path,
                            'summary': summary,
                            'url': doc_chunks[0].get('url', ''),
                            'title': doc_chunks[0].get('title', ''),
                            'heading': doc_chunks[0].get('heading', '')
                        })
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
        max_length: int
    ) -> str:
        """
        Generate a summary from doc chunks using Claude
        
        Args:
            doc_chunks: List of doc chunks with content
            max_length: Maximum summary length
        
        Returns:
            Summary text
        """
        # Combine chunks
        combined_content = "\n\n".join([
            f"## {chunk.get('heading', 'Content')}\n{chunk['content']}"
            for chunk in doc_chunks[:3]  # Use first 3 chunks
        ])
        
        prompt = f"""Summarize the following documentation section in {max_length} characters or less.

Focus on WHAT DEVELOPERS NEED TO DO:
- What code to write or configure
- What steps to take
- What APIs/functions to use
- What settings to change
- Practical implementation details

Write in an action-oriented, developer-focused style. Use imperative mood (e.g., "Set up...", "Configure...", "Call...", "Install...").

Documentation:
{combined_content[:2000]}  # Limit input size

Provide a concise, actionable summary for developers."""

        try:
            response = self.claude.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Extract text from response
            summary = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    summary += block.text
                elif isinstance(block, str):
                    summary += block
            
            summary = summary.strip()
            
            # Truncate if too long
            if len(summary) > max_length:
                summary = summary[:max_length].rsplit('.', 1)[0] + '.'
            
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

