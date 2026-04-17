#!/usr/bin/env bash

runner_normalize_role() {
  local role="${1:-}"
  case "$role" in
    planner_architect_orchestrator)
      printf "planner\n"
      ;;
    vision-architect-tasks-planner|vision_architect_tasks_planner)
      printf "planner\n"
      ;;
    analyst|architect|po|guardian|prompt)
      printf "planner\n"
      ;;
    admin)
      printf "admin\n"
      ;;
    scrum_master)
      printf "scrum_master\n"
      ;;
    app-dev|app_dev)
      printf "app-dev\n"
      ;;
    verifier)
      printf "verifier\n"
      ;;
    dev|backend_engineer|frontend_engineer|data_analyst|integrator)
      printf "app-dev\n"
      ;;
    tester|qa)
      printf "verifier\n"
      ;;
    infra_engineer|clawsentinel)
      printf "admin\n"
      ;;
    *)
      printf "%s\n" "$role"
      ;;
  esac
}

runner_is_supported_role() {
  local role="${1:-}"
  case "$role" in
    planner_architect_orchestrator) return 0 ;;
    planner|app-dev|verifier|admin|scrum_master) return 0 ;;
    *) return 1 ;;
  esac
}
