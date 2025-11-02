#!/usr/bin/env python3
"""
Launch script for Finance Copilot Application
Starts both API backend and React frontend
"""
import sys
import os
import subprocess
import signal
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def launch_api():
    """Launch the FastAPI backend."""
    print("🚀 Launching Finance Copilot API backend...")
    try:
        # Change to project root
        os.chdir(Path(__file__).parent)
        
        # Launch API using run_api.py
        api_process = subprocess.Popen([
            sys.executable, "run_api.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print(f"✅ API backend started (PID: {api_process.pid})")
        print("   API will be available at: http://localhost:8050")
        print("   API docs: http://localhost:8050/docs")
        return api_process
    except Exception as e:
        print(f"❌ Failed to start API backend: {e}")
        return None

def launch_frontend():
    """Launch the React frontend."""
    print("🌐 Launching Finance Copilot React frontend...")
    try:
        # Change to webapp directory
        webapp_dir = Path(__file__).parent / "webapp"
        os.chdir(webapp_dir)
        
        # Check if npm is available
        try:
            subprocess.run(["npm", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  npm not found. Please install Node.js and npm to run the frontend.")
            return None
        
        # Install dependencies if needed
        if not (webapp_dir / "node_modules").exists():
            print("📦 Installing frontend dependencies...")
            subprocess.run(["npm", "install"], check=True)
        
        # Launch frontend
        frontend_process = subprocess.Popen([
            "npm", "run", "dev"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print(f"✅ React frontend started (PID: {frontend_process.pid})")
        print("   Frontend will be available at: http://localhost:5173")
        return frontend_process
    except Exception as e:
        print(f"❌ Failed to start React frontend: {e}")
        return None

def main():
    """Main launch function."""
    print("🎯 Finance Copilot - Full Stack Launcher")
    print("=" * 50)
    
    # Launch API
    api_process = launch_api()
    if not api_process:
        print("⚠️  API backend failed to start. Continuing with frontend only...")
    
    # Give API time to start
    time.sleep(2)
    
    # Launch frontend
    frontend_process = launch_frontend()
    if not frontend_process:
        print("⚠️  React frontend failed to start.")
        if api_process:
            print("   API backend is still running.")
        return
    
    print("\n" + "=" * 50)
    print("🎉 Finance Copilot is now running!")
    print("=" * 50)
    print("🔗 API Backend:     http://localhost:8050")
    print("📘 API Documentation: http://localhost:8050/docs")
    print("🌐 React Frontend:   http://localhost:5173")
    print("\n📝 Press Ctrl+C to stop both servers")
    
    # Wait for processes
    try:
        while True:
            time.sleep(1)
            # Check if processes are still running
            if api_process and api_process.poll() is not None:
                print("❌ API backend has stopped unexpectedly")
                break
            if frontend_process and frontend_process.poll() is not None:
                print("❌ React frontend has stopped unexpectedly")
                break
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
        if api_process:
            api_process.terminate()
            api_process.wait()
            print("✅ API backend stopped")
        if frontend_process:
            frontend_process.terminate()
            frontend_process.wait()
            print("✅ React frontend stopped")
        print("👋 Finance Copilot shutdown complete")

if __name__ == "__main__":
    main()