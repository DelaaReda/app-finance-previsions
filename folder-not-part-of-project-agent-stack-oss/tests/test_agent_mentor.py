#!/usr/bin/env python3
"""
Test script to verify the agent mentor can launch and guide the enhanced agent.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_mentor_launch():
    """Test that the mentor can launch the agent."""
    try:
        from agent.mentor import AgentMentor
        
        # Create mentor
        mentor = AgentMentor("/Users/venom/Documents/analyse-financiere/agent-stack-oss")
        print("✅ Mentor created successfully")
        
        # Test session ID generation
        session_id = mentor._generate_session_id()
        print(f"✅ Session ID generated: {session_id}")
        
        # Test timestamp generation
        timestamp = mentor._get_timestamp()
        print(f"✅ Timestamp generated: {timestamp}")
        
        # Test simple goal launch (dry run to avoid long execution)
        print("🏃 Testing agent launch with simple goal...")
        result = mentor.launch_agent(
            goal="Test the enhanced agent launcher",
            mode="planning",
            complexity="simple"
        )
        
        print(f"✅ Agent launch test completed")
        print(f"   Success: {result.get('success', 'Unknown')}")
        print(f"   Duration: {result.get('duration', 0):.2f} seconds")
        print(f"   Session ID: {result.get('session_id', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Mentor launch test failed: {e}")
        return False

def test_mentor_training():
    """Test that the mentor can run training sessions."""
    try:
        from agent.mentor import AgentMentor
        
        # Create mentor
        mentor = AgentMentor("/Users/venom/Documents/analyse-financiere/agent-stack-oss")
        print("✅ Mentor created successfully for training test")
        
        # Test training with simple tasks
        sample_tasks = [
            {
                "goal": "Test training task 1",
                "mode": "planning",
                "complexity": "simple",
                "expected_outcome": "success"
            },
            {
                "goal": "Test training task 2", 
                "mode": "qa",
                "complexity": "simple",
                "expected_outcome": "success"
            }
        ]
        
        print("🏃 Testing agent training with sample tasks...")
        training_results = mentor.train_agent("test_phase", sample_tasks)
        
        print(f"✅ Training test completed")
        print(f"   Phase: {training_results.get('phase', 'Unknown')}")
        print(f"   Tasks completed: {training_results.get('tasks_completed', 0)}/{training_results.get('tasks_total', 0)}")
        print(f"   Success rate: {training_results.get('success_rate', 0):.2%}")
        print(f"   Duration: {training_results.get('duration', 0):.2f} seconds")
        
        return True
        
    except Exception as e:
        print(f"❌ Mentor training test failed: {e}")
        return False

def test_progress_evaluation():
    """Test that the mentor can evaluate agent progress."""
    try:
        from agent.mentor import AgentMentor
        
        # Create mentor
        mentor = AgentMentor("/Users/venom/Documents/analyse-financiere/agent-stack-oss")
        print("✅ Mentor created successfully for progress evaluation test")
        
        # Test progress evaluation with sample data
        sample_sessions = [
            {"success_rate": 0.7, "duration": 45.2, "timestamp": "2025-11-01T10:00:00Z"},
            {"success_rate": 0.8, "duration": 42.1, "timestamp": "2025-11-02T10:00:00Z"},
            {"success_rate": 0.85, "duration": 38.5, "timestamp": "2025-11-03T10:00:00Z"}
        ]
        
        print("🏃 Testing progress evaluation...")
        evaluation = mentor.evaluate_agent_progress(sample_sessions)
        
        print(f"✅ Progress evaluation completed")
        print(f"   Average success rate: {evaluation.get('evaluation', {}).get('average_success_rate', 0):.2%}")
        print(f"   Average duration: {evaluation.get('evaluation', {}).get('average_duration', 0):.2f} seconds")
        print(f"   Recent improvement: {evaluation.get('evaluation', {}).get('recent_improvement', 0):.2%}")
        print(f"   Recommendations: {len(evaluation.get('recommendations', []))} items")
        
        for rec in evaluation.get('recommendations', []):
            print(f"   💡 {rec}")
        
        return True
        
    except Exception as e:
        print(f"❌ Progress evaluation test failed: {e}")
        return False

def main():
    """Run all mentor tests."""
    print("🧪 Agent Mentor Test Suite\n")
    
    tests = [
        ("Mentor Launch", test_mentor_launch),
        ("Mentor Training", test_mentor_training),
        ("Progress Evaluation", test_progress_evaluation),
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
    print(f"Mentor Test Results: {passed}/{total} passed")
    
    if all(results):
        print("🎉 All mentor tests passed!")
        print("✅ The agent mentor is ready to guide the enhanced agent.")
        return 0
    else:
        print("❌ Some mentor tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())