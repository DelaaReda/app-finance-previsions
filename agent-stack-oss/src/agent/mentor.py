#!/usr/bin/env python3
"""
Agent Launcher & Mentor - Launches and guides the enhanced agent through its learning journey.
"""

from __future__ import annotations
import sys
import os
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class AgentMentor:
    """Mentors the enhanced agent through its development journey."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.logs_dir = self.project_root / "data" / "mentor_logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = self._generate_session_id()
        self.session_log = self.logs_dir / f"session_{self.session_id}.log"
    
    def launch_agent(self, goal: str, mode: str = "full", complexity: str = "medium") -> Dict[str, Any]:
        """
        Launch the agent with guidance and mentoring.
        
        Args:
            goal: Objective for the agent
            mode: Execution mode (planning, sprint, qa, full)
            complexity: Task complexity (simple, medium, complex)
            
        Returns:
            Dictionary with launch results and mentoring observations
        """
        self._log(f"🚀 Launching agent session {self.session_id}")
        self._log(f"🎯 Goal: {goal}")
        self._log(f"🎮 Mode: {mode}")
        self._log(f"🧠 Complexity: {complexity}")
        
        # Prepare the command
        cmd = [
            sys.executable, "-m", "src.agent.enhanced_run",
            "--goal", goal,
            "--mode", mode,
            "--complexity", complexity,
            "--verbose"
        ]
        
        self._log(f"🔧 Command: {' '.join(cmd)}")
        
        # Launch the agent
        start_time = time.time()
        try:
            # Run the agent in a subprocess
            process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitor the agent's progress
            stdout_lines = []
            stderr_lines = []
            
            # Read output in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    stdout_lines.append(line)
                    self._log(f"🤖 Agent: {line}")
                    
                    # Provide real-time mentoring based on output
                    self._provide_real_time_guidance(line)
            
            # Capture stderr
            stderr_output, _ = process.communicate()
            if stderr_output:
                stderr_lines = stderr_output.strip().split('\n')
                for line in stderr_lines:
                    if line.strip():
                        self._log(f"⚠️  Agent Error: {line}")
            
            # Wait for process to complete
            return_code = process.wait()
            elapsed_time = time.time() - start_time
            
            self._log(f"⏱️  Session completed in {elapsed_time:.2f} seconds")
            self._log(f"🏁 Return code: {return_code}")
            
            # Analyze results
            results = self._analyze_results(stdout_lines, stderr_lines, return_code, elapsed_time)
            
            # Provide post-session mentoring
            self._provide_post_session_feedback(results)
            
            return results
            
        except Exception as e:
            self._log(f"💥 Launch failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": self.session_id,
                "timestamp": self._get_timestamp()
            }
    
    def _provide_real_time_guidance(self, line: str) -> None:
        """Provide real-time guidance based on agent output."""
        # Look for common patterns that need mentoring
        if "error" in line.lower() or "failed" in line.lower():
            self._log("💡 Mentor Tip: Check error details and consider fallback strategies")
        
        elif "warning" in line.lower():
            self._log("💡 Mentor Tip: Address warnings to improve code quality")
        
        elif "loading" in line.lower():
            self._log("💡 Mentor Tip: Loading operations can be optimized with caching")
        
        elif "processing" in line.lower():
            self._log("💡 Mentor Tip: Consider progress indicators for long operations")
        
        elif "saving" in line.lower():
            self._log("💡 Mentor Tip: Always validate data before saving")
    
    def _provide_post_session_feedback(self, results: Dict[str, Any]) -> None:
        """Provide feedback after session completion."""
        success = results.get("success", False)
        duration = results.get("duration", 0)
        
        if success:
            self._log("✅ Excellent work! The agent completed its task successfully.")
            
            if duration < 30:
                self._log("⚡ Impressive speed! The agent is performing efficiently.")
            elif duration > 120:
                self._log("🐢 The agent took longer than expected. Consider optimization opportunities.")
        else:
            error = results.get("error", "Unknown error")
            self._log(f"❌ The agent encountered an issue: {error}")
            self._log("💡 Mentor Tip: Review the error, check inputs, and try again with adjustments.")
    
    def _analyze_results(self, stdout_lines: list[str], stderr_lines: list[str], 
                        return_code: int, duration: float) -> Dict[str, Any]:
        """Analyze agent execution results."""
        # Parse output for key information
        success = return_code == 0
        error_messages = [line for line in stderr_lines if line.strip()]
        output_messages = [line for line in stdout_lines if line.strip()]
        
        # Look for JSON results in output
        results_data = None
        for line in reversed(output_messages):
            if line.startswith('{') and line.endswith('}'):
                try:
                    results_data = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
        
        return {
            "success": success,
            "return_code": return_code,
            "duration": duration,
            "stdout_lines": len(stdout_lines),
            "stderr_lines": len(stderr_lines),
            "error_messages": error_messages[:5],  # Limit to first 5 errors
            "output_messages": output_messages[-10:],  # Limit to last 10 outputs
            "results_data": results_data,
            "session_id": self.session_id,
            "timestamp": self._get_timestamp()
        }
    
    def train_agent(self, curriculum_phase: str, tasks: list[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Train the agent through a specific curriculum phase.
        
        Args:
            curriculum_phase: Name of the training phase
            tasks: List of tasks to execute with goals and expected outcomes
            
        Returns:
            Training results with success metrics
        """
        self._log(f"🎓 Starting training phase: {curriculum_phase}")
        self._log(f"📋 Tasks to complete: {len(tasks)}")
        
        results = {
            "phase": curriculum_phase,
            "tasks_total": len(tasks),
            "tasks_completed": 0,
            "tasks_failed": 0,
            "task_results": [],
            "start_time": self._get_timestamp(),
            "duration": 0
        }
        
        start_time = time.time()
        
        for i, task in enumerate(tasks):
            self._log(f"📝 Task {i+1}/{len(tasks)}: {task.get('goal', 'Unnamed task')}")
            
            # Launch agent for this task
            task_result = self.launch_agent(
                goal=task.get("goal", ""),
                mode=task.get("mode", "full"),
                complexity=task.get("complexity", "medium")
            )
            
            # Record task result
            task_result["task_index"] = i
            task_result["expected_outcome"] = task.get("expected_outcome", "success")
            results["task_results"].append(task_result)
            
            # Update counters
            if task_result.get("success", False):
                results["tasks_completed"] += 1
                self._log(f"✅ Task {i+1} completed successfully")
            else:
                results["tasks_failed"] += 1
                self._log(f"❌ Task {i+1} failed")
        
        results["duration"] = time.time() - start_time
        results["end_time"] = self._get_timestamp()
        results["success_rate"] = results["tasks_completed"] / len(tasks) if tasks else 0
        
        self._log(f"🏁 Training phase completed: {results['tasks_completed']}/{len(tasks)} tasks successful")
        self._log(f"📈 Success rate: {results['success_rate']:.2%}")
        
        return results
    
    def evaluate_agent_progress(self, previous_sessions: list[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate agent progress based on previous sessions.
        
        Args:
            previous_sessions: List of previous session results
            
        Returns:
            Progress evaluation with recommendations
        """
        if not previous_sessions:
            return {"evaluation": "No previous sessions to evaluate", "recommendations": []}
        
        # Analyze trends
        success_rates = [session.get("success_rate", 0) for session in previous_sessions]
        durations = [session.get("duration", 0) for session in previous_sessions]
        
        # Calculate trends
        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Check for improvement
        recent_success_rate = success_rates[-1] if success_rates else 0
        improvement = recent_success_rate - (success_rates[0] if len(success_rates) > 1 else 0)
        
        # Generate recommendations
        recommendations = []
        if improvement > 0.1:
            recommendations.append("🎉 Excellent improvement! Continue current approach.")
        elif improvement < -0.1:
            recommendations.append("⚠️  Performance declined. Review recent changes and adjust approach.")
        else:
            recommendations.append("📊 Steady performance. Look for optimization opportunities.")
        
        if avg_success_rate < 0.8:
            recommendations.append("🎯 Focus on error handling and fallback strategies.")
        
        if avg_duration > 120:
            recommendations.append("⚡ Consider optimizing slow operations with caching or parallelization.")
        
        return {
            "evaluation": {
                "average_success_rate": avg_success_rate,
                "average_duration": avg_duration,
                "recent_improvement": improvement,
                "sessions_analyzed": len(previous_sessions)
            },
            "recommendations": recommendations,
            "timestamp": self._get_timestamp()
        }
    
    def _log(self, message: str) -> None:
        """Log a message to both console and session log."""
        timestamp = self._get_timestamp()
        log_entry = f"[{timestamp}] {message}"
        
        # Print to console
        print(log_entry)
        
        # Write to session log
        try:
            with open(self.session_log, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except Exception:
            pass  # Ignore logging errors
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()


def main():
    """Main entry point for the agent mentor."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Launcher & Mentor")
    parser.add_argument("--goal", help="Objective for the agent")
    parser.add_argument("--mode", choices=["planning", "sprint", "qa", "full"], 
                       default="full", help="Execution mode")
    parser.add_argument("--complexity", choices=["simple", "medium", "complex"], 
                       default="medium", help="Task complexity")
    parser.add_argument("--train", action="store_true", 
                       help="Run training curriculum instead of single task")
    parser.add_argument("--phase", help="Training phase to execute")
    
    args = parser.parse_args()
    
    # Create mentor
    mentor = AgentMentor("/Users/venom/Documents/analyse-financiere/agent-stack-oss")
    
    if args.train:
        # Run training curriculum
        print("🎓 Starting agent training curriculum...")
        
        # Sample training tasks for demonstration
        sample_tasks = [
            {
                "goal": "Prepare architecture documentation for G4F integration",
                "mode": "planning",
                "complexity": "medium",
                "expected_outcome": "success"
            },
            {
                "goal": "Generate sprint plan for news integration",
                "mode": "sprint",
                "complexity": "medium",
                "expected_outcome": "success"
            },
            {
                "goal": "Validate recent code changes",
                "mode": "qa",
                "complexity": "simple",
                "expected_outcome": "success"
            }
        ]
        
        training_results = mentor.train_agent(args.phase or "foundation", sample_tasks)
        print(f"\n📊 Training Results: {training_results['tasks_completed']}/{training_results['tasks_total']} tasks completed")
        print(f"📈 Success Rate: {training_results['success_rate']:.2%}")
        
    elif args.goal:
        # Launch single task
        print(f"🚀 Launching agent with goal: {args.goal}")
        result = mentor.launch_agent(args.goal, args.mode, args.complexity)
        
        if result.get("success"):
            print("✅ Agent completed successfully!")
        else:
            print(f"❌ Agent failed: {result.get('error', 'Unknown error')}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()