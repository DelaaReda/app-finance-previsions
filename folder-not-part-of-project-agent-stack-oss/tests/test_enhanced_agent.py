#!/usr/bin/env python3
"""
Quick integration test for the enhanced agent.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_enhanced_agent_imports():
    """Test that all enhanced agent components can be imported."""
    try:
        # Test core components
        from agent.enhanced_run import main as enhanced_main
        from agent.graph import build_graph as build_enhanced_graph
        print("✓ Core enhanced agent components imported successfully")
        
        # Test nodes
        from agent.nodes.architecture_planner import node_architecture_planner
        from agent.nodes.g4f_model_selector import get_best_g4f_model
        from agent.nodes.enhanced_qa import enhanced_qa_check
        print("✓ Enhanced agent nodes imported successfully")
        
        # Test tools
        from agent.tools.browser_qa import BrowserQA
        print("✓ Enhanced agent tools imported successfully")
        
        # Test configuration
        from agent.config import AgentConfig
        cfg = AgentConfig()
        print("✓ Configuration system working")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_basic_functionality():
    """Test basic enhanced agent functionality."""
    try:
        from agent.nodes.g4f_model_selector import get_best_g4f_model
        from agent.config import AgentConfig
        
        cfg = AgentConfig()
        best_model = get_best_g4f_model(cfg)
        print(f"✓ Best G4F model identified: {best_model}")
        
        from agent.tools.browser_qa import BrowserQA
        browser_qa = BrowserQA(timeout=5)
        test_result = browser_qa.validate_links(["https://httpbin.org/status/200"])
        print(f"✓ Browser QA working: {test_result['success_rate']:.0%} success rate")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def main():
    """Run integration tests."""
    print("🧪 Enhanced Agent Integration Tests\n")
    
    tests = [
        ("Import Tests", test_enhanced_agent_imports),
        ("Basic Functionality", test_basic_functionality),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        try:
            result = test_func()
            results.append(result)
            print()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}\n")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print(f"Integration Test Results: {passed}/{total} passed")
    
    if all(results):
        print("🎉 All integration tests passed!")
        print("✅ Enhanced agent is ready for use.")
        return 0
    else:
        print("❌ Some integration tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())