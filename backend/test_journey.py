"""
Test script for journey generation
Tests with a hardcoded goal to verify output quality
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.journey_generator import JourneyGenerator
from dotenv import load_dotenv

load_dotenv()


def test_journey_generation():
    """Test journey generation with a hardcoded goal"""
    print("=" * 60)
    print("🧪 Testing Journey Generation")
    print("=" * 60)
    
    # Test query
    test_query = "I want to set up authentication with Privy"
    
    print(f"\n📝 User Query: {test_query}")
    print("\n" + "-" * 60)
    
    try:
        generator = JourneyGenerator()
        journey = generator.generate_journey(test_query, max_steps=5)
        
        if 'error' in journey:
            print(f"❌ Error: {journey['error']}")
            return
        
        print(f"\n✅ Generated Journey:")
        print(f"   Goal: {journey['goal']}")
        print(f"   Total Steps: {journey['total_steps']}")
        print(f"   Estimated Time: {journey['estimated_time']}")
        
        print(f"\n📋 Steps:")
        for i, step in enumerate(journey['steps'], 1):
            print(f"\n   Step {step.get('step_number', i)}: {step.get('title', 'Untitled')}")
            print(f"   Description: {step.get('description', 'N/A')}")
            print(f"   Complexity: {step.get('complexity', 'N/A')}")
            print(f"   Time: {step.get('estimated_time', 'N/A')}")
            
            doc_paths = step.get('doc_paths', [])
            if doc_paths:
                print(f"   Docs: {', '.join(doc_paths[:2])}")
                if len(doc_paths) > 2:
                    print(f"          ... and {len(doc_paths) - 2} more")
            
            prerequisites = step.get('prerequisites', [])
            if prerequisites:
                print(f"   Prerequisites: Steps {', '.join(map(str, prerequisites))}")
        
        print("\n" + "=" * 60)
        print("✅ Journey generation test complete!")
        print("\n💡 Check:")
        print("   - Are steps in logical order?")
        print("   - Do doc references exist?")
        print("   - Are descriptions clear?")
        print("   - Is the journey actionable?")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_journey_generation()

