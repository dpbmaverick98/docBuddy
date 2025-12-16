"""
Diagnostic script to inspect ChromaDB collections and documents
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Disable ChromaDB telemetry
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_DISABLED"] = "1"

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

load_dotenv()

# Use same path logic as VectorStore
default_path = os.path.join(os.path.dirname(__file__), 'chroma_db')
db_path = os.getenv('CHROMA_DB_PATH', default_path)

print(f"🗄️ ChromaDB path: {os.path.abspath(db_path)}")
print("=" * 60)

try:
    client = chromadb.PersistentClient(
        path=db_path,
        settings=Settings(anonymized_telemetry=False)
    )

    # List all collections
    try:
        collections = client.list_collections()
    except Exception as schema_error:
        if "no such column" in str(schema_error).lower() or "topic" in str(schema_error).lower():
            print("⚠️  ChromaDB schema error detected!")
            print(f"   Error: {schema_error}")
            print("\n🔧 This usually means the database was created with an older ChromaDB version.")
            print("   The database needs to be reset to work with the current version.")
            print("\n💡 To fix this, run:")
            print("   python backend/reset_chromadb.py")
            print("\n   Or manually delete the chroma_db directory and reindex.")
            sys.exit(1)
        else:
            raise
    
    print(f"\n📋 Found {len(collections)} collections:")
    print("=" * 60)
    
    for col in collections:
        count = col.count()
        print(f"\n📦 Collection: '{col.name}'")
        print(f"   Documents: {count}")
        
        if count > 0:
            # Get sample documents
            try:
                sample = col.get(limit=3)
                if sample.get('ids'):
                    print(f"   Sample IDs: {sample['ids'][:3]}")
                    print(f"   Sample metadata keys: {list(sample.get('metadatas', [{}])[0].keys()) if sample.get('metadatas') else 'None'}")
                    
                    # Check metadata field names
                    if sample.get('metadatas') and len(sample['metadatas']) > 0:
                        first_meta = sample['metadatas'][0]
                        print(f"   Metadata fields: {list(first_meta.keys())}")
                        
                        # Check for field name mismatches
                        expected_fields = ['doc_title', 'doc_url', 'doc_path', 'heading', 'level']
                        actual_fields = list(first_meta.keys())
                        missing_fields = [f for f in expected_fields if f not in actual_fields]
                        if missing_fields:
                            print(f"   ⚠️  Missing expected fields: {missing_fields}")
                        old_fields = [f for f in actual_fields if f in ['doc', 'url', 'path']]
                        if old_fields:
                            print(f"   ⚠️  Found old field names (should be fixed): {old_fields}")
                else:
                    print(f"   ⚠️  No IDs found in collection")
            except Exception as e:
                print(f"   ❌ Error getting sample: {e}")
        else:
            print(f"   ⚠️  Collection is empty!")
    
    print("\n" + "=" * 60)
    print("💡 If collections are empty, try reindexing:")
    print("   python backend/indexer/index_docs.py --base-url https://docs.privy.io --project privy --clear")
    
except Exception as e:
    print(f"❌ Error accessing ChromaDB: {e}")
    import traceback
    traceback.print_exc()

