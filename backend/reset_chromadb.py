"""
Reset ChromaDB database to fix schema errors
"""
import os
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Disable ChromaDB telemetry
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_DISABLED"] = "1"

from dotenv import load_dotenv

load_dotenv()

# Use same path logic as VectorStore
default_path = os.path.join(os.path.dirname(__file__), 'chroma_db')
db_path = os.getenv('CHROMA_DB_PATH', default_path)

print(f"🗄️ ChromaDB path: {os.path.abspath(db_path)}")
print("=" * 60)

if not os.path.exists(db_path):
    print("✅ Database directory doesn't exist - nothing to reset")
    sys.exit(0)

# List what will be deleted
print("\n📋 Contents to be deleted:")
try:
    items = os.listdir(db_path)
    for item in items:
        item_path = os.path.join(db_path, item)
        if os.path.isdir(item_path):
            print(f"   📁 {item}/")
        else:
            size = os.path.getsize(item_path)
            print(f"   📄 {item} ({size:,} bytes)")
except Exception as e:
    print(f"   ⚠️  Could not list contents: {e}")

print("\n⚠️  WARNING: This will delete all ChromaDB data!")
print("   All indexed documents will be lost and need to be reindexed.")
response = input("\n   Continue? (yes/no): ").lower().strip()

if response != 'yes':
    print("❌ Reset cancelled")
    sys.exit(0)

try:
    # Remove the entire directory
    shutil.rmtree(db_path)
    print(f"\n✅ Deleted database directory: {db_path}")
    
    # Recreate empty directory
    os.makedirs(db_path, exist_ok=True)
    print(f"✅ Created fresh database directory")
    
    print("\n" + "=" * 60)
    print("✅ Database reset complete!")
    print("\n💡 Next steps:")
    print("   1. Reindex your documents:")
    print("      python backend/indexer/index_docs.py --base-url https://docs.privy.io --project privy --clear")
    print("   2. Verify indexing worked:")
    print("      python backend/indexer/verify_chunks.py --collection privy")
    
except Exception as e:
    print(f"\n❌ Error resetting database: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

