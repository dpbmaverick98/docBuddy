import chromadb
from chromadb.config import Settings
import os
import hashlib
import numpy as np
import warnings
import logging
import time
import shutil
from typing import List, Dict, Optional, Any, Union
from .chunker import split_by_headings, get_chunk_stats
from .llms_parser import fetch_llms_txt, parse_llms_txt
from .doc_fetcher import fetch_all_docs

# Define Chunk locally to avoid import issues
class Chunk:
    def __init__(self, content: str, doc_title: str = "unknown", doc_url: str = "", doc_path: str = "", heading: str = "", level: int = 0):
        self.content = content
        self.doc_title = doc_title
        self.doc_url = doc_url
        self.doc_path = doc_path
        self.heading = heading
        self.level = level

# Disable telemetry to avoid errors
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_DISABLED"] = "1"

# Cache manager disabled to avoid dependency issues
get_cache_manager = None
def cache_embedding(func):
    """Simple cache decorator that does nothing"""
    return func


class VectorStore:
    """
    Vector store for document chunks using ChromaDB
    """

    def __init__(self, collection_name: str = "docs", persist_directory: str = None, x402_client=None):
        """
        Initialize ChromaDB client and collection
        
        Args:
            collection_name: Name of the collection
            persist_directory: Directory to persist DB (None = in-memory)
            x402_client: Optional x402 client for embedding generation
        """
        self.collection_name = collection_name
        self.x402_client = x402_client
        
        # Set up ChromaDB client
        # Disable telemetry to avoid errors
        # Suppress telemetry warnings
        warnings.filterwarnings("ignore", message=".*telemetry.*")
        logging.getLogger("chromadb.telemetry").setLevel(logging.ERROR)
        
        if persist_directory:
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False
                )
            )
        else:
            # Default to local persistent storage relative to backend directory
            default_path = os.path.join(os.path.dirname(__file__), '..', 'chroma_db')
            db_path = os.getenv('CHROMA_DB_PATH', default_path)
            print(f"🗄️  VectorStore using ChromaDB path: {os.path.abspath(db_path)} (collection: {self.collection_name})")
            self.client = chromadb.PersistentClient(
                path=db_path,
                settings=Settings(
                    anonymized_telemetry=False
                )
            )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Debug: List all collections to verify
        try:
            all_collections = self.client.list_collections()
            print(f"🔍 Available collections: {[c.name for c in all_collections]}")
            print(f"🔍 Current collection '{collection_name}' count: {self.collection.count()}")
        except Exception as e:
            print(f"⚠️  Could not list collections: {e}")

    def add_documents(self, chunks: List[Dict[str, Any]], batch_size: int = 50, delay_between_batches: float = 2.0):
        """
        Add document chunks to vector store with embeddings
        """
        print(f"\n💾 Step 5: Storing in vector database...")
        
        ids = []
        texts = []
        embeddings = []
        metadatas = []
        
        # Generate unique IDs using hash of content + metadata to avoid duplicates
        for i, chunk in enumerate(chunks):
            # Create unique ID based on content hash + index to ensure uniqueness
            content_hash = hashlib.md5(
                f"{chunk.get('doc_url', '')}{chunk.get('doc_path', '')}{chunk.get('heading', '')}{i}".encode()
            ).hexdigest()[:12]
            ids.append(f"{self.collection_name}_{content_hash}_{i}")
            texts.append(chunk['content'])
            metadatas.append({
                'doc_title': chunk.get('doc_title', 'unknown'),  # Fixed: Changed from 'doc' to 'doc_title'
                'doc_url': chunk.get('doc_url', ''),  # Fixed: Changed from 'url' to 'doc_url'
                'doc_path': chunk.get('doc_path', ''),  # Fixed: Changed from 'path' to 'doc_path'
                'heading': chunk.get('heading', ''),
                'level': chunk.get('level', 0)
            })

        print(f"📊 Adding {len(chunks)} chunks to vector store...")
        
        # Process in batches to avoid overwhelming ChromaDB
        for i in range(0, len(chunks), batch_size):
            batch_end = min(i + batch_size, len(chunks))
            batch_ids = ids[i:batch_end]
            batch_texts = texts[i:batch_end]
            batch_metadatas = metadatas[i:batch_end]
            
            # Generate embeddings in batch
            batch_embeddings = []
            if self.x402_client:
                # Try x402 first, fallback to direct API if it fails
                print(f"  💳 Processing batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1} with x402 payments...")
                try:
                    texts_for_batch = [chunk['content'] for chunk in chunks[i:batch_end]]
                    print(f"    📝 Embedding {len(texts_for_batch)} texts")
                    embeddings = self.x402_client.cohere_embed(
                        texts=texts_for_batch,
                        model='embed-multilingual-v3.0',
                        input_type='search_document'
                    )
                    print(f"    📊 Raw embeddings type: {type(embeddings)}, len: {len(embeddings) if embeddings else 0}")
                    if embeddings and len(embeddings) > 0:
                        print(f"    📊 First embedding type: {type(embeddings[0])}, len: {len(embeddings[0]) if isinstance(embeddings[0], list) else 'N/A'}")

                    # Handle response format
                    if isinstance(embeddings, list) and len(embeddings) > 0:
                        if isinstance(embeddings[0], list):
                            # Multiple embeddings: [[emb1], [emb2], ...]
                            batch_embeddings = embeddings
                            print(f"    ✅ Multiple embeddings format: {len(batch_embeddings)} vectors")
                        else:
                            # Single embedding flattened: [f1, f2, f3, ...]
                            batch_embeddings = [embeddings]
                            print(f"    ✅ Single embedding format: 1 vector")
                    print(f"    ✅ Batch {i//batch_size + 1} embeddings generated via x402")
                except Exception as x402_error:
                    # Fallback to direct Cohere API if x402 fails
                    error_msg = str(x402_error).lower()
                    if "connection" in error_msg or "refused" in error_msg or "network" in error_msg:
                        print(f"    ⚠️ x402 service unavailable ({x402_error}), falling back to direct Cohere API...")
                    else:
                        print(f"    ⚠️ x402 error: {x402_error}, falling back to direct Cohere API...")
                    
                    try:
                        import cohere
                        api_key = os.getenv('COHERE_API_KEY')
                        if not api_key:
                            raise Exception("COHERE_API_KEY not set in .env file (required when x402 is unavailable)")
                        co = cohere.Client(api_key)
                        texts_for_batch = [chunk['content'] for chunk in chunks[i:batch_end]]
                        response = co.embed(
                            texts=texts_for_batch,
                            model='embed-multilingual-v3.0',
                            input_type='search_document'
                        )
                        batch_embeddings = response.embeddings
                        print(f"    ✅ Batch {i//batch_size + 1} embeddings generated via direct API (fallback)")
                    except Exception as e:
                        print(f"    ❌ Batch {i//batch_size + 1} failed (both x402 and direct API): {e}")
                        continue
            else:
                # Use direct Cohere API
                print(f"  🔧 Processing batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1} with direct API...")
                try:
                    import cohere
                    api_key = os.getenv('COHERE_API_KEY')
                    if not api_key:
                        raise Exception("COHERE_API_KEY not set in .env file (required when USE_X402_PAYMENTS=false)")
                    co = cohere.Client(api_key)
                    texts_for_batch = [chunk['content'] for chunk in chunks[i:batch_end]]
                    response = co.embed(
                        texts=texts_for_batch,
                        model='embed-multilingual-v3.0',
                        input_type='search_document'
                    )
                    batch_embeddings = response.embeddings
                    print(f"    ✅ Batch {i//batch_size + 1} embeddings generated via direct API")
                except Exception as e:
                    print(f"    ❌ Batch {i//batch_size + 1} failed: {e}")
                    continue

            # Convert embeddings to proper format for ChromaDB
            embeddings_list = []
            for emb in batch_embeddings:
                if isinstance(emb, list):
                    embeddings_list.append(emb)
                else:
                    embeddings_list.append(list(emb))

            print(f"  📦 Adding to ChromaDB: {len(batch_ids)} docs, embeddings shape: {len(embeddings_list)}x{len(embeddings_list[0]) if embeddings_list else 0}")

            # Add to ChromaDB
            try:
                self.collection.add(
                    ids=batch_ids,
                    embeddings=embeddings_list,
                    metadatas=batch_metadatas,
                    documents=batch_texts
                )
                print(f"  ✅ Added batch {i//batch_size + 1}")
                # Verify the add worked
                current_count = self.collection.count()
                print(f"  📊 Collection now has {current_count} documents")
            except Exception as e:
                print(f"  ❌ Error adding to ChromaDB: {e}")
                raise
            
            # Wait between batches to avoid rate limits (except for last batch)
            if i + batch_size < len(chunks):
                time.sleep(delay_between_batches)
        
        print(f"\n✅ Successfully indexed {len(chunks)} chunks")

    def search(self, query: str, n_results: int = 5, filter_metadata: Optional[Dict] = None):
        """
        Search for similar chunks with caching
        """
        print(f"🔍 VectorStore.search called with query='{query}', n_results={n_results}, collection='{self.collection_name}'")

        # Generate cache key for embeddings
        cache_key = f"embed:{hashlib.md5(query.encode()).hexdigest()}"

        # Try to get cached embedding first (disabled for now)
        query_embedding = None
        if get_cache_manager:
            query_embedding = get_cache_manager().embeddings.get(cache_key)

        # Generate query embedding with retry if not cached
        max_retries = 3

        for attempt in range(max_retries):
            try:
                if query_embedding is None:
                    if self.x402_client:
                        # Try x402 first, fallback to direct API if it fails
                        try:
                            print("💳 x402 payment: Cohere embedding for query...")
                            embeddings = self.x402_client.cohere_embed(
                                texts=[query],
                                model='embed-multilingual-v3.0',
                                input_type='search_query'
                            )
                            query_embedding = embeddings[0]
                            print(f"✅ Query embedded via x402, shape: {len(query_embedding) if query_embedding else 'None'}")
                            print(f"   Sample values: {query_embedding[:5] if query_embedding else 'None'}")
                            # Cache the embedding
                            if get_cache_manager:
                                get_cache_manager().embeddings.set(cache_key, query_embedding)
                        except Exception as x402_error:
                            # Fallback to direct API if x402 fails
                            error_msg = str(x402_error).lower()
                            if "connection" in error_msg or "refused" in error_msg or "network" in error_msg:
                                print(f"⚠️ x402 service unavailable ({x402_error}), falling back to direct Cohere API...")
                            else:
                                print(f"⚠️ x402 error: {x402_error}, falling back to direct Cohere API...")
                            
                            # Fallback to direct Cohere API
                            import cohere
                            api_key = os.getenv('COHERE_API_KEY')
                            if not api_key:
                                raise Exception("COHERE_API_KEY not set in .env file (required when x402 is unavailable)")
                            co = cohere.Client(api_key)
                            response = co.embed(
                                texts=[query],
                                model='embed-multilingual-v3.0',
                                input_type='search_query'
                            )
                            query_embedding = response.embeddings[0]
                            print(f"✅ Query embedded via direct API, shape: {len(query_embedding) if query_embedding else 'None'}")
                            # Cache the embedding
                            if get_cache_manager:
                                get_cache_manager().embeddings.set(cache_key, query_embedding)
                    else:
                        # Use direct Cohere API
                        import cohere
                        api_key = os.getenv('COHERE_API_KEY')
                        if not api_key:
                            raise Exception("COHERE_API_KEY not set in .env file (required when USE_X402_PAYMENTS=false)")
                        co = cohere.Client(api_key)
                        response = co.embed(
                            texts=[query],
                            model='embed-multilingual-v3.0',
                            input_type='search_query'
                        )
                        query_embedding = response.embeddings[0]
                        print(f"✅ Query embedded via direct API, shape: {len(query_embedding) if query_embedding else 'None'}")
                        # Cache the embedding
                        if get_cache_manager:
                            get_cache_manager().embeddings.set(cache_key, query_embedding)
                break
            except Exception as e:
                if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                    wait_time = 60 * (2 ** attempt)
                    print(f"⚠️ Rate limit hit. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise
        
        if query_embedding is None:
            raise Exception("Failed to generate query embedding")

        # Search in ChromaDB
        where = filter_metadata if filter_metadata else None

        print(f"🔍 Executing ChromaDB query with n_results={n_results}, where={where}")
        try:
            count = self.collection.count()
            print(f"   Collection has {count} total documents")
            # Also try to get some documents directly
            try:
                docs = self.collection.get(limit=3)
                print(f"   Direct get() returned {len(docs.get('ids', []))} documents")
                if docs.get('ids'):
                    print(f"   Sample IDs: {docs['ids'][:3]}")
            except Exception as e3:
                print(f"   Error with direct get(): {e3}")
        except Exception as e:
            print(f"   Error getting count: {e}")
            # Try to list collections
            try:
                collections = self.client.list_collections()
                print(f"   Available collections: {[c.name for c in collections]}")
                if self.collection_name in [c.name for c in collections]:
                    print(f"   Collection '{self.collection_name}' exists")
                else:
                    print(f"   Collection '{self.collection_name}' does NOT exist")
            except Exception as e2:
                print(f"   Error listing collections: {e2}")

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )

        print(f"🔍 ChromaDB raw results: ids={len(results.get('ids', [[]])[0]) if results.get('ids') else 0}")
        if results.get('distances') and len(results['distances']) > 0:
            print(f"   Sample distances: {results['distances'][0][:5] if results['distances'][0] else 'None'}")
        
        # Format results
        formatted_results = []
        if results and results.get('ids') and len(results['ids']) > 0:
            ids = results['ids']
            documents = results.get('documents', [])
            metadatas = results.get('metadatas', [])
            distances = results.get('distances')
            
            # Handle ChromaDB response format (ids can be list of lists when using query_embeddings)
            if isinstance(ids, list) and len(ids) > 0 and isinstance(ids[0], list):
                # Flatten nested lists (ChromaDB returns list of lists for query_embeddings)
                ids = ids[0] if ids else []
                documents = documents[0] if documents else []
                metadatas = metadatas[0] if metadatas else []
                distances = distances[0] if distances else []
            elif isinstance(ids, list):
                ids = ids if ids else []
                documents = documents if documents else []
                metadatas = metadatas if metadatas else []
                distances = distances if distances else []
            
            for i in range(len(ids)):
                formatted_results.append({
                    'id': ids[i] if i < len(ids) else '',
                    'content': documents[i] if i < len(documents) else '',
                    'metadata': metadatas[i] if i < len(metadatas) else {},
                    'distance': distances[i] if distances and i < len(distances) else None
                })
        
        return formatted_results

    def get_stats(self):
        """
        Get collection statistics
        """
        try:
            count = self.collection.count()
            return {
                'total_chunks': count,
                'collection_name': self.collection_name
            }
        except Exception as e:
            print(f"⚠️  Error getting stats: {e}")
            return {'total_chunks': 0, 'collection_name': self.collection_name}

    def clear_collection(self):
        """
        Clear all chunks from collection
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