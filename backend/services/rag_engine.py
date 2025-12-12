"""
RAG engine with post-processing and Cohere optimizations
Uses ChromaDB directly (with Cohere embeddings) + post-processing filters + Cohere rerank + query expansion
Simplified to avoid LlamaIndex's OpenAI embedding requirement
"""
import os
from typing import List, Dict, Optional, Tuple
from indexer.vector_store import VectorStore
from cohere import Client as CohereClient
from dotenv import load_dotenv

load_dotenv()


class RAGEngine:
    def __init__(self, collection_name: str = "docs", x402_client=None):
        """
        Initialize RAG engine with ChromaDB (uses existing Cohere embeddings)

        Args:
            collection_name: ChromaDB collection name
            x402_client: x402 client for payment-enabled requests
        """
        # Use direct vector store (has Cohere embeddings)
        self.vector_store = VectorStore(collection_name=collection_name, x402_client=x402_client)
        self.x402_client = x402_client

        # Initialize Cohere client for rerank and query expansion
        api_key = os.getenv('COHERE_API_KEY')
        if api_key:
            self.cohere = CohereClient(api_key=api_key)
        else:
            self.cohere = None
            print("⚠️  COHERE_API_KEY not found - rerank and query expansion will be disabled")
    
    def query(
        self,
        query: str,
        top_k: int = 20,
        similarity_cutoff: float = 0.7,
        required_keywords: Optional[List[str]] = None,
        response_mode: str = "compact",
        use_cohere_optimizations: bool = True,
        intent: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Query with optimized context retrieval, Cohere rerank, and post-processing

        Args:
            query: Search query
            top_k: Number of results to retrieve
            similarity_cutoff: Minimum similarity score (0.0-1.0)
            required_keywords: Keywords that must be present
            response_mode: "compact" or "tree_summarize" (for future use)
            use_cohere_optimizations: Whether to use Cohere rerank/expansion/compression

        Returns:
            List of relevant doc chunks with metadata
        """
        # Stage 1: Query expansion (get multiple query variations)
        if use_cohere_optimizations:
            expanded_queries = self.expand_query(query, intent)
        else:
            expanded_queries = [query]

        # Stage 2: Multi-query search - search all variations and merge results
        all_candidates = []
        seen_ids = set()

        for expanded_query in expanded_queries:
            # Get candidates for each query variation
            candidates = self.vector_store.search(expanded_query, n_results=top_k * 2)

            for candidate in candidates:
                candidate_id = candidate.get('id')
                if candidate_id not in seen_ids:
                    seen_ids.add(candidate_id)
                    all_candidates.append(candidate)

        # Limit to reasonable number of candidates for reranking
        all_candidates = all_candidates[:min(len(all_candidates), top_k * 4)]

        # Stage 3: Rerank with Cohere for better relevance
        if use_cohere_optimizations and all_candidates:
            candidate_texts = [c.get('content', '') for c in all_candidates]
            reranked_results = self.rerank_documents(query, candidate_texts, top_n=top_k * 2)

            # Reconstruct full results with metadata using rerank indices
            reranked_candidates = []
            for rerank_result in reranked_results:
                original_index = rerank_result['index']
                if original_index < len(all_candidates):
                    original_candidate = all_candidates[original_index].copy()
                    original_candidate['relevance_score'] = rerank_result['relevance_score']
                    original_candidate['reranked_content'] = rerank_result['content']
                    reranked_candidates.append(original_candidate)
        else:
            # Fallback to original candidates
            reranked_candidates = all_candidates[:top_k * 2]
            for candidate in reranked_candidates:
                candidate['relevance_score'] = 0.5  # Default score

        # Stage 4: Apply traditional filtering and format results
        formatted = []
        for result in reranked_candidates:
            metadata = result.get('metadata', {})
            distance = result.get('distance', 1.0)
            score = result.get('relevance_score', 1.0 - distance)

            # Apply similarity cutoff (be more lenient with reranked results)
            if score < similarity_cutoff and len(formatted) >= top_k:
                continue

            # Apply keyword filter if specified
            if required_keywords:
                content_lower = result.get('reranked_content', result.get('content', '')).lower()
                metadata_str = ' '.join([str(v) for v in metadata.values()]).lower()
                combined_text = f"{content_lower} {metadata_str}"

                if len(formatted) >= top_k:
                    if not any(keyword.lower() in combined_text for keyword in required_keywords):
                        continue

            # Use compressed content if available, otherwise original
            final_content = result.get('reranked_content', result.get('content', ''))

            formatted.append({
                'doc_path': metadata.get('doc_path', ''),
                'doc_url': metadata.get('doc_url', ''),
                'doc_title': metadata.get('doc_title', ''),
                'heading': metadata.get('heading', ''),
                'content': final_content,
                'distance': distance,
                'metadata': metadata,
                'score': score,
                'relevance_score': result.get('relevance_score', score)
            })

        # If filtering was too strict, return top results anyway
        if not formatted and reranked_candidates:
            print(f"⚠️  RAG filtering too strict, returning top {top_k} results without filters")
            for result in reranked_candidates[:top_k]:
                metadata = result.get('metadata', {})
                formatted.append({
                    'doc_path': metadata.get('doc_path', ''),
                    'doc_url': metadata.get('doc_url', ''),
                    'doc_title': metadata.get('doc_title', ''),
                    'heading': metadata.get('heading', ''),
                    'content': result.get('reranked_content', result.get('content', '')),
                    'distance': result.get('distance', 1.0),
                    'metadata': metadata,
                    'score': result.get('relevance_score', 0.5),
                    'relevance_score': result.get('relevance_score', 0.5)
                })

        return formatted[:top_k]
    
    def query_with_intent(
        self,
        query: str,
        intent: Dict,
        top_k: int = 20,
        use_cohere_optimizations: bool = True
    ) -> List[Dict]:
        """
        Query with extracted intent and Cohere optimizations for better results

        Args:
            query: Search query
            intent: Extracted intent dict (from IntentExtractor)
            top_k: Number of results
            use_cohere_optimizations: Whether to use Cohere features

        Returns:
            List of relevant doc chunks
        """
        # Use keywords from intent for filtering
        required_keywords = intent.get('keywords', [])[:3]  # Top 3 keywords

        # Adjust similarity cutoff based on complexity
        similarity_cutoff = {
            'beginner': 0.65,  # More lenient for beginners
            'intermediate': 0.7,
            'advanced': 0.75  # Stricter for advanced
        }.get(intent.get('complexity', 'intermediate'), 0.7)

        # Pass intent to query method for use in expansion
        return self.query(
            query=query,  # Pass original query, intent will be used in expansion
            top_k=top_k,
            similarity_cutoff=similarity_cutoff,
            required_keywords=required_keywords if required_keywords else None,
            use_cohere_optimizations=use_cohere_optimizations,
            intent=intent  # Pass intent for better expansion
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

    def rerank_documents(self, query: str, documents: List[str], top_n: int = 5) -> List[Dict]:
        """
        Rerank documents using Cohere rerank for better relevance

        Args:
            query: Search query
            documents: List of document contents
            top_n: Number of top results to return

        Returns:
            List of reranked documents with scores
        """
        if not self.cohere:
            print("⚠️  Cohere client not available - skipping rerank")
            return [{"content": doc, "relevance_score": 0.5, "index": i} for i, doc in enumerate(documents[:top_n])]

        try:
            rerank_response = self.cohere.rerank(
                query=query,
                documents=documents,
                top_n=min(top_n, len(documents)),
                model="rerank-english-v3.0"
            )

            return [
                {
                    "content": r.document["text"] if isinstance(r.document, dict) else r.document.text,
                    "relevance_score": r.relevance_score,
                    "index": r.index
                }
                for r in rerank_response.results
            ]
        except Exception as e:
            print(f"⚠️  Rerank failed: {e} - returning original order")
            return [{"content": doc, "relevance_score": 0.5, "index": i} for i, doc in enumerate(documents[:top_n])]

    def expand_query(self, query: str, intent: Optional[Dict] = None) -> List[str]:
        """
        Generate multiple query variations using Cohere for better search coverage

        Args:
            query: Original query
            intent: Extracted intent (optional)

        Returns:
            List of expanded queries including original
        """
        if not self.cohere:
            print("⚠️  Cohere client not available - using original query only")
            return [query]

        try:
            # Build context for better expansion
            context_parts = []
            if intent:
                if intent.get('platform'):
                    context_parts.append(f"for {intent['platform']}")
                if intent.get('keywords'):
                    context_parts.extend(intent['keywords'][:2])

            context = " ".join(context_parts)
            full_context = f"{query} {context}".strip()

            prompt = f"""Generate 3 alternative ways to ask: '{full_context}'
Focus on technical documentation search.
Consider synonyms, different phrasings, and related technical concepts.
Output only the queries, one per line."""

            if self.x402_client:
                # Use x402 Cohere chat
                response_text = self.x402_client.cohere_chat(
                    message=prompt,
                    max_tokens=100,
                    temperature=0.2
                )
                # 💰 x402 Payment: $0.05 USDC
                # Create mock response object
                response = type('MockResponse', (), {'text': response_text})()
            else:
            response = self.cohere.chat(
                message=prompt,
                max_tokens=100,
                temperature=0.2
            )

            # Extract queries from response
            generated_queries = response.text.strip().split('\n')
            generated_queries = [q.strip() for q in generated_queries if q.strip()]

            # Return original + up to 3 variations
            expanded_queries = [query] + generated_queries[:3]

            print(f"🔍 Expanded query from '{query}' to {len(expanded_queries)} variations")
            return expanded_queries

        except Exception as e:
            print(f"⚠️  Query expansion failed: {e} - using original query")
            return [query]

    def compress_context(self, query: str, documents: List[str]) -> List[str]:
        """
        Compress documents to only relevant content using Cohere

        Args:
            query: Search query
            documents: List of document contents

        Returns:
            List of compressed document contents
        """
        if not self.cohere:
            print("⚠️  Cohere client not available - skipping compression")
            return documents

        compressed_docs = []

        for doc in documents:
            try:
                prompt = f"""Query: '{query}'

Document:
{doc}

Extract only the sentences directly answering or relevant to the query.
Remove boilerplate, navigation, and irrelevant content.
If no relevant content found, output 'N/A'.
Output only the relevant text:"""

                if self.x402_client:
                    # Use x402 Cohere chat for compression
                    compressed = self.x402_client.cohere_chat(
                        message=prompt,
                        max_tokens=300,
                        temperature=0.0
                    )
                    # 💰 x402 Payment
                else:
                response = self.cohere.chat(
                    message=prompt,
                    max_tokens=300,
                    temperature=0.0
                )
                    compressed = response.text.strip()

                compressed = response.text.strip()
                if compressed and compressed != 'N/A':
                    compressed_docs.append(compressed)
                else:
                    # If compression fails, keep original but truncate
                    compressed_docs.append(doc[:500] + "..." if len(doc) > 500 else doc)

            except Exception as e:
                print(f"⚠️  Compression failed for document: {e}")
                compressed_docs.append(doc[:500] + "..." if len(doc) > 500 else doc)

        print(f"🗜️  Compressed {len(documents)} documents to {len(compressed_docs)} relevant chunks")
        return compressed_docs
