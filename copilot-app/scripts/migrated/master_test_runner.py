#!/usr/bin/env python3
"""
Master Test Runner - Exécute tous les tests pour vérifier l'intégration complète
"""
import sys
import os
import subprocess
import time
from pathlib import Path

def run_test_script(script_name: str, script_path: str) -> bool:
    """Run a test script and return success status."""
    print(f"\n{'='*60}")
    print(f"🧪 Running {script_name}")
    print(f"{'='*60}")
    
    try:
        # Change to project directory
        project_dir = Path(__file__).parent.parent
        os.chdir(project_dir)
        
        # Run the script
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(f"✅ {script_name}: PASSED")
            if result.stdout:
                # Only show first few lines of output to keep it readable
                lines = result.stdout.strip().split('\n')
                for line in lines[:10]:  # Show first 10 lines
                    print(f"   {line}")
                if len(lines) > 10:
                    print(f"   ... ({len(lines) - 10} more lines)")
            return True
        else:
            print(f"❌ {script_name}: FAILED")
            print(f"   Return code: {result.returncode}")
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines[-5:]:  # Show last 5 lines
                    print(f"   STDOUT: {line}")
            if result.stderr:
                lines = result.stderr.strip().split('\n')
                for line in lines[-5:]:  # Show last 5 lines
                    print(f"   STDERR: {line}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {script_name}: TIMEOUT")
        return False
    except Exception as e:
        print(f"💥 {script_name}: ERROR - {e}")
        return False

def main():
    """Run all test suites."""
    print("🚀 Master Test Runner - Finance Copilot")
    print("=" * 60)
    
    start_time = time.time()
    
    # Test scripts to run
    test_scripts = [
        ("UI Component Test", "scripts/test_ui_components.py"),
        ("UI Runner Test", "scripts/test_ui_runner.py"),
        ("Quick API Test", "scripts/quick_api_test.py"),
        ("Integration Test", "scripts/integration_test.py")
    ]
    
    # Check if scripts exist
    existing_scripts = []
    for name, path in test_scripts:
        if Path(path).exists():
            existing_scripts.append((name, path))
        else:
            print(f"⚠️  Skipping {name}: Script not found at {path}")
    
    if not existing_scripts:
        print("❌ No test scripts found!")
        return False
    
    print(f"Found {len(existing_scripts)} test scripts to run")
    
    # Run tests
    results = []
    for name, path in existing_scripts:
        success = run_test_script(name, path)
        results.append((name, success))
        
        # Add delay between tests
        time.sleep(1)
    
    # Summary
    end_time = time.time()
    
    print(f"\n{'='*60}")
    print("📊 MASTER TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = 0
    failed = 0
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:<10} {name}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"⏱️  TOTAL TIME: {end_time - start_time:.2f} seconds")
    print(f"✅ PASSED: {passed}")
    print(f"❌ FAILED: {failed}")
    print(f"📊 SUCCESS RATE: {passed/len(results)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All tests PASSED! The application is ready.")
        print("🔗 Visit http://localhost:5173 to use the UI")
        print("🌐 API available at http://localhost:8050")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        print("🔧 Check the errors above and fix the issues")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)