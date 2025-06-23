#!/usr/bin/env python3
"""Test script for the multi-agent research system."""

import json
from datetime import datetime
from pathlib import Path

from agents.research_crew import ResearchCrew
from src.config import config

def test_research():
    """Run a test research query."""
    # Test query
    query = "What are the key considerations when implementing a retrieval-augmented generation (RAG) system for enterprise use?"
    
    print(f"\n🔍 Testing Multi-Agent Research System")
    print(f"Query: {query}")
    print("-" * 80)
    
    # Create research crew with default settings
    num_researchers = config.get_agent_config().default_sub_researchers
    print(f"Using {num_researchers} sub-researchers")
    
    # Initialize crew
    crew = ResearchCrew(
        num_sub_researchers=num_researchers,
        max_iterations=2  # Limit iterations for testing
    )
    
    # Conduct research
    print("\n🚀 Starting research...")
    results = crew.conduct_research(query)
    
    # Display results
    print("\n✅ Research Complete!")
    print("-" * 80)
    print("\n📊 Statistics:")
    print(f"- Duration: {results['duration_seconds']:.1f} seconds")
    print(f"- Total Cost: ${results['statistics']['total_cost']:.4f}")
    print(f"- Researchers Used: {results['statistics']['num_researchers']}")
    print(f"- Total Searches: {results['statistics']['total_searches']}")
    print(f"- Research Angles: {len(results['research_angles'])}")
    
    print("\n📝 Research Angles Explored:")
    for i, angle in enumerate(results['research_angles'], 1):
        print(f"{i}. {angle}")
    
    print("\n📄 Synthesis Preview:")
    print("-" * 80)
    # Show first 1000 characters of synthesis
    preview = results['synthesis'][:1000]
    if len(results['synthesis']) > 1000:
        preview += "...\n\n[Truncated for preview]"
    print(preview)
    
    # Save full results
    output_dir = Path("data/test_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"test_results_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Full results saved to: {output_file}")
    
    return results

if __name__ == "__main__":
    try:
        test_research()
    except KeyboardInterrupt:
        print("\n\n⚠️  Research interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during research: {e}")
        raise