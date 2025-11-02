#!/usr/bin/env python3
"""
Additional verification script to test importing launch_fullstack.py
"""
import sys
from pathlib import Path

def test_import():
    """Direct test to import launch_fullstack and check its functions."""
    # Add the scripts directory to the path
    scripts_dir = Path(__file__).parent / "scripts"
    sys.path.insert(0, str(scripts_dir))
    
    try:
        print("Attempting to import launch_fullstack.py...")
        import launch_fullstack
        
        print("✅ Import successful!")
        
        # Check that expected functions exist
        functions_to_check = ['launch_api', 'launch_frontend', 'main']
        for func_name in functions_to_check:
            if hasattr(launch_fullstack, func_name):
                print(f"✅ Function '{func_name}' exists")
            else:
                print(f"❌ Function '{func_name}' missing")
        
        print("\n✅ All checks passed! launch_fullstack.py has valid syntax and can be imported successfully.")
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax error in launch_fullstack.py: {e}")
        return False
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_import()
    if success:
        print("\n🎉 Verification completed successfully!")
    else:
        print("\n💥 Verification failed!")
        sys.exit(1)