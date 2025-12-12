"""
ChromaDB integration for vector storage
"""
import os
import time
# Disable ChromaDB telemetry before importing
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_DISABLED"] = "1"

import chromadb
from chromadb.config import Settings
from typing import List, Dict
from cohere import Client as CohereClient
from cohere.error import CohereAPIError


class VectorStore:
    def __init__(self, collection_name: str = "docs", persist_directory: str = None, x402_client=None):
        """
        Initialize ChromaDB client and collection
        
        Args:
            collection_name: Name of the collection
            persist_directory: Directory to persist DB (None = in-memory)
        """
        self.collection_name = collection_name
        
        # Set up ChromaDB client
        # Disable telemetry to avoid errors
        # Suppress telemetry warnings
        import warnings
        import logging
        warnings.filterwarnings("ignore", message=".*telemetry.*")
        logging.getLogger("chromadb.telemetry").setLevel(logging.ERROR)
        
        if persist_directory:
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        else:
            # Default to local persistent storage
            db_path = os.getenv('CHROMA_DB_PATH', './chroma_db')
            self.client = chromadb.PersistentClient(
                path=db_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize Cohere client
        api_key = os.getenv('COHERE_API_KEY')
        if not api_key:
            raise ValueError("COHERE_API_KEY environment variable not set")
        
        self.cohere = CohereClient(api_key=api_key)
    
    def add_chunks(self, chunks: List[Dict], batch_size: int = 50, delay_between_batches: float = 2.0):
        """
        Add chunks to vector store with embeddings
        
        Args:
            chunks: List of chunk dicts with content, metadata, etc.
            batch_size: Process in batches to avoid rate limits (smaller = safer)
            delay_between_batches: Seconds to wait between batches (default: 2s)
        """
        total_chunks = len(chunks)
        print(f"\n📊 Adding {total_chunks} chunks to vector store...")
        print(f"   Batch size: {batch_size}, Delay: {delay_between_batches}s")
        
        for i in range(0, total_chunks, batch_size):
            batch = chunks[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_chunks + batch_size - 1) // batch_size
            
            print(f"  Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)...")
            
            # Extract texts for embedding
            texts = [chunk['content'] for chunk in batch]
            
            # Generate embeddings with retry logic
            embeddings = None
            max_retries = 3
            retry_delay = 60  # Start with 60 seconds
            
            for attempt in range(max_retries):
                try:
                    embeddings_response = self.cohere.embed(
                        texts=texts,
                        model='embed-multilingual-v3.0',
                        input_type='search_document'
                    )
                    embeddings = embeddings_response.embeddings
                    break  # Success!
                    
                except CohereAPIError as e:
                    if "rate limit" in str(e).lower() or "429" in str(e):
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                            print(f"  ⚠️  Rate limit hit. Waiting {wait_time}s before retry {attempt + 2}/{max_retries}...")
                            time.sleep(wait_time)
                        else:
                            print(f"  ❌ Rate limit exceeded after {max_retries} attempts")
                            print(f"  💡 Tip: Wait a few minutes and resume indexing")
                            raise
                    else:
                        # Other API error
                        print(f"  ❌ Error generating embeddings: {e}")
                        raise
                except Exception as e:
                    print(f"  ❌ Unexpected error: {e}")
                    raise
            
            if embeddings is None:
                raise Exception("Failed to generate embeddings after retries")
            
            # Prepare metadata and IDs
            ids = []
            metadatas = []
            documents = []
            
            for j, chunk in enumerate(batch):
                chunk_id = f"{chunk['doc_path']}_{chunk.get('chunk_index', j)}"
                ids.append(chunk_id)
                
                metadatas.append({
                    'doc_path': chunk['doc_path'],
                    'doc_url': chunk.get('doc_url', ''),
                    'doc_title': chunk.get('doc_title', ''),
                    'heading': chunk['heading'],
                    'level': str(chunk['level'])
                })
                
                documents.append(chunk['content'])
            
            # Add to ChromaDB
            try:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents
                )
                print(f"  ✅ Added batch {batch_num}")
            except Exception as e:
                print(f"  ❌ Error adding to ChromaDB: {e}")
                raise
            
            # Wait between batches to avoid rate limits (except for last batch)
            if i + batch_size < total_chunks:
                time.sleep(delay_between_batches)
        
        print(f"\n✅ Successfully indexed {total_chunks} chunks")
    
    def search(self, query: str, n_results: int = 5, filter_metadata: Dict = None):
        """
        Search for similar chunks
        
        Args:
            query: Search query
            n_results: Number of results to return
            filter_metadata: Optional metadata filters
        
        Returns:
            List of matching chunks with scores
        """
        # Generate query embedding with retry
        max_retries = 3
        query_embedding = None
        
        for attempt in range(max_retries):
            try:
                if self.x402_client:
                    # Use x402 Cohere embed
                    print("💳 x402 payment: Cohere embedding for query...")
                    embeddings = self.x402_client.cohere_embed(
                        texts=[query],
                        model='embed-multilingual-v3.0',
                        input_type='search_query'
                    )
                    query_embedding = embeddings[0]
                    # 💰 x402 Payment: $0.02 USDC
                    print("✅ Query embedded")
                    break
                else:
                    query_embedding = self.cohere.embed(
                        texts=[query],
                        model='embed-multilingual-v3.0',
                        input_type='search_query'
                    ).embeddings[0]
                    break
            except Exception as e:
                if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                    wait_time = 60 * (2 ** attempt)
                    print(f"⚠️  Rate limit hit. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise
        
        if query_embedding is None:
            raise Exception("Failed to generate query embedding")
        
        # Search in ChromaDB
        where = filter_metadata if filter_metadata else None
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )
        
        # Format results
        formatted_results = []
        if results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
        
        return formatted_results
    
    def clear_collection(self):
        """
        Clear all chunks from the collection
        """
        try:
            self.client.delete_collection(name=self.collection_name)
            # Recreate empty collection
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"✅ Cleared collection '{self.collection_name}'")
        except Exception as e:
            print(f"⚠️  Error clearing collection: {e}")
            # If delete fails, try to recreate
            try:
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
            except:
                pass
    
    def get_stats(self) -> Dict:
        """
        Get collection statistics
        """
        count = self.collection.count()
        return {
            'collection_name': self.collection_name,
            'total_chunks': count
        }

