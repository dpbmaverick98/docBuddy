"""
RAG engine with post-processing
Uses ChromaDB directly (with Cohere embeddings) + post-processing filters
Simplified to avoid LlamaIndex's OpenAI embedding requirement
"""
import os
from typing import List, Dict, Optional
from indexer.vector_store import VectorStore
from dotenv import load_dotenv

load_dotenv()


class RAGEngine:
    def __init__(self, collection_name: str = "docs"):
        """
        Initialize RAG engine with ChromaDB (uses existing Cohere embeddings)
        
        Args:
            collection_name: ChromaDB collection name
        """
        # Use direct vector store (has Cohere embeddings)
        self.vector_store = VectorStore(collection_name=collection_name)
    
    def query(
        self,
        query: str,
        top_k: int = 20,
        similarity_cutoff: float = 0.7,
        required_keywords: Optional[List[str]] = None,
        response_mode: str = "compact"
    ) -> List[Dict]:
        """
        Query with optimized context retrieval and post-processing
        
        Args:
            query: Search query
            top_k: Number of results to retrieve
            similarity_cutoff: Minimum similarity score (0.0-1.0)
            required_keywords: Keywords that must be present
            response_mode: "compact" or "tree_summarize" (for future use)
        
        Returns:
            List of relevant doc chunks with metadata
        """
        # Get more results than needed for filtering
        # Get 3x more to account for filtering
        search_results = self.vector_store.search(query, n_results=top_k * 3)
        
        # Format and filter results
        formatted = []
        for result in search_results:
            metadata = result.get('metadata', {})
            distance = result.get('distance', 1.0)
            score = 1.0 - distance  # Convert distance to similarity score
            
            # Apply similarity cutoff (but be lenient - distance is already sorted)
            # Only filter if score is really low (very high distance)
            if score < similarity_cutoff and len(formatted) >= top_k:
                # If we already have enough results, skip low-scoring ones
                continue
            
            # Apply keyword filter if specified (but don't be too strict)
            if required_keywords:
                content_lower = result.get('content', '').lower()
                metadata_str = ' '.join([str(v) for v in metadata.values()]).lower()
                combined_text = f"{content_lower} {metadata_str}"
                
                # Check if any required keyword is present
                # Only filter if we have enough results already
                if len(formatted) >= top_k:
                    if not any(keyword.lower() in combined_text for keyword in required_keywords):
                        continue
            
            # Format to match VectorStore.search() output format
            formatted.append({
                'doc_path': metadata.get('doc_path', ''),
                'doc_url': metadata.get('doc_url', ''),
                'doc_title': metadata.get('doc_title', ''),
                'heading': metadata.get('heading', ''),
                'content': result.get('content', ''),
                'distance': distance,  # Keep distance for compatibility
                'metadata': metadata,
                'score': score
            })
        
        # If filtering was too strict and we have no results, return top results anyway
        if not formatted and search_results:
            print(f"⚠️  RAG filtering too strict, returning top {top_k} results without filters")
            for result in search_results[:top_k]:
                metadata = result.get('metadata', {})
                formatted.append({
                    'doc_path': metadata.get('doc_path', ''),
                    'doc_url': metadata.get('doc_url', ''),
                    'doc_title': metadata.get('doc_title', ''),
                    'heading': metadata.get('heading', ''),
                    'content': result.get('content', ''),
                    'distance': result.get('distance', 1.0),
                    'metadata': metadata,
                    'score': 1.0 - result.get('distance', 1.0)
                })
        
        # Return top_k after filtering
        return formatted[:top_k]
    
    def query_with_intent(
        self,
        query: str,
        intent: Dict,
        top_k: int = 20
    ) -> List[Dict]:
        """
        Query with extracted intent for better results
        
        Args:
            query: Search query
            intent: Extracted intent dict (from IntentExtractor)
            top_k: Number of results
        
        Returns:
            List of relevant doc chunks
        """
        # Build enhanced query with intent
        enhanced_query = self._build_enhanced_query(query, intent)
        
        # Use keywords from intent for filtering
        required_keywords = intent.get('keywords', [])[:3]  # Top 3 keywords
        
        # Adjust similarity cutoff based on complexity
        similarity_cutoff = {
            'beginner': 0.65,  # More lenient for beginners
            'intermediate': 0.7,
            'advanced': 0.75  # Stricter for advanced
        }.get(intent.get('complexity', 'intermediate'), 0.7)
        
        return self.query(
            query=enhanced_query,
            top_k=top_k,
            similarity_cutoff=similarity_cutoff,
            required_keywords=required_keywords if required_keywords else None
        )
    
    def _build_enhanced_query(self, query: str, intent: Dict) -> str:
        """
        Build enhanced query using intent
        
        Args:
            query: Original query
            intent: Extracted intent
        
        Returns:
            Enhanced query string
        """
        parts = [query]
        
        # Add platform context if available
        if intent.get('platform'):
            parts.append(f"for {intent['platform']}")
        
        # Add key concepts
        if intent.get('keywords'):
            parts.extend(intent['keywords'][:2])
        
        return " ".join(parts)
