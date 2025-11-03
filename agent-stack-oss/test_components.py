#!/usr/bin/env python3
"""
Simple test script for the enhanced agent components.
"""

from __future__ import annotations
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_model_selector():
    """Test the G4F model selector."""
    print("Testing G4F model selector...")
    try:
        from agent.nodes.g4f_model_selector import get_best_g4f_model, select_model_for_task
        from agent.config import AgentConfig
        
        cfg = AgentConfig()
        best_model = get_best_g4f_model(cfg)
        print(f"Best G4F model: {best_model}")
        
        # Test model selection for different complexities
        simple_model = select_model_for_task("simple")
        complex_model = select_model_for_task("complex")
        print(f"Model for simple tasks: {simple_model}")
        print(f"Model for complex tasks: {complex_model}")
        return True
    except Exception as e:
        print(f"Error testing model selector: {e}")
        return False

def test_architecture_planner():
    """Test the architecture planner components."""
    print("\nTesting architecture planner components...")
    try:
        # Import and test the architecture planner functions
        from agent.nodes.architecture_planner import node_architecture_planner, node_priority_definer, node_sprint_planner
        
        # Create a mock state
        mock_state = {
            "goal": "Test the enhanced agent",
            "plan": {},
            "context_docs": [],
            "patch": {},
            "tests": {},
            "result": {},
            "retrieval_error": None,
            "architecture_plan": None,
            "sprint_plan": None,
            "priorities": None,
            "recent_commits": None,
        }
        
        print("Architecture planner components imported successfully")
        return True
    except Exception as e:
        print(f"Error testing architecture planner: {e}")
        return False

def test_enhanced_qa():
    """Test the enhanced QA components."""
    print("\nTesting enhanced QA components...")
    try:
        from agent.nodes.enhanced_qa import enhanced_qa_check, _get_timestamp
        
        print("Enhanced QA components imported successfully")
        print(f"Current timestamp: {_get_timestamp()}")
        return True
    except Exception as e:
        print(f"Error testing enhanced QA: {e}")
        return False

def test_browser_qa():
    """Test the browser QA components."""
    print("\nTesting browser QA components...")
    try:
        from agent.tools.browser_qa import BrowserQA
        
        # Test browser QA tool creation
        browser_qa = BrowserQA(timeout=10, max_retries=1)
        print("Browser QA tool created successfully")
        
        # Test URL validation (simple test with a quick URL)
        test_urls = [
            "https://httpbin.org/status/200",  # This should be accessible
        ]
        
        validation_results = browser_qa.validate_links(test_urls)
        print(f"Validated {validation_results['total_checked']} URLs")
        print(f"Working URLs: {validation_results['working_count']}")
        print(f"Success rate: {validation_results['success_rate']:.2%}")
        
        return True
    except Exception as e:
        print(f"Error testing browser QA: {e}")
        return False

def main():
    """Run all tests."""
    print("Running enhanced agent component tests...\n")
    
    tests = [
        test_model_selector,
        test_architecture_planner,
        test_enhanced_qa,
        test_browser_qa,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print(f"\nTest Results: {sum(results)}/{len(results)} passed")
    if all(results):
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())