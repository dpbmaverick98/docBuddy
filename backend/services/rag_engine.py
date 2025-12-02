"""
LlamaIndex-powered RAG engine
Wraps ChromaDB with LlamaIndex for better context optimization
"""
import os
from typing import List, Dict, Optional
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.postprocessor import SimilarityPostprocessor, KeywordNodePostprocessor
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from indexer.vector_store import VectorStore
from dotenv import load_dotenv

load_dotenv()


class RAGEngine:
    def __init__(self, collection_name: str = "docs"):
        """
        Initialize RAG engine with LlamaIndex + ChromaDB
        
        Args:
            collection_name: ChromaDB collection name
        """
        # Get ChromaDB collection from existing VectorStore
        vector_store = VectorStore(collection_name=collection_name)
        chroma_collection = vector_store.collection
        
        # Wrap ChromaDB with LlamaIndex
        chroma_store = ChromaVectorStore(chroma_collection=chroma_collection)
        
        # Create index from vector store
        # Note: We use Claude directly, not through LlamaIndex's LLM abstraction
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=chroma_store
        )
    
    def query(
        self,
        query: str,
        top_k: int = 20,
        similarity_cutoff: float = 0.7,
        required_keywords: Optional[List[str]] = None,
        response_mode: str = "compact"
    ) -> List[Dict]:
        """
        Query with optimized context retrieval
        
        Args:
            query: Search query
            top_k: Number of results to retrieve
            similarity_cutoff: Minimum similarity score
            required_keywords: Keywords that must be present
            response_mode: "compact" or "tree_summarize" for context optimization
        
        Returns:
            List of relevant doc chunks with metadata
        """
        # Create retriever
        retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=top_k
        )
        
        # Create postprocessors for filtering
        postprocessors = [
            SimilarityPostprocessor(similarity_cutoff=similarity_cutoff)
        ]
        
        # Add keyword filter if specified
        if required_keywords:
            postprocessors.append(
                KeywordNodePostprocessor(required_keywords=required_keywords)
            )
        
        # Create query engine
        query_engine = RetrieverQueryEngine(
            retriever=retriever,
            node_postprocessors=postprocessors,
            response_mode=response_mode
        )
        
        # Query and get nodes
        nodes = query_engine.retrieve(query)
        
        # Format results
        results = []
        for node in nodes:
            # Extract metadata from node
            metadata = {}
            if hasattr(node, 'metadata') and node.metadata:
                metadata = node.metadata
            elif hasattr(node, 'node') and hasattr(node.node, 'metadata'):
                metadata = node.node.metadata
            
            # Get text content
            text = ""
            if hasattr(node, 'text'):
                text = node.text
            elif hasattr(node, 'node') and hasattr(node.node, 'text'):
                text = node.node.text
            
            # Get score
            score = None
            if hasattr(node, 'score'):
                score = node.score
            elif hasattr(node, 'similarity'):
                score = node.similarity
            
            results.append({
                'content': text,
                'metadata': metadata,
                'score': score,
                'node_id': getattr(node, 'node_id', None) or (getattr(node.node, 'node_id', None) if hasattr(node, 'node') else None)
            })
        
        return results
    
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

