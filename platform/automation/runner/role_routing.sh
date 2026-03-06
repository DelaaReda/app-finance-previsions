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
    analyst|architect|po)
      printf "planner\n"
      ;;
    scrum_master)
      printf "scrum_master\n"
      ;;
    backend_engineer|frontend_engineer|data_analyst|integrator)
      printf "dev\n"
      ;;
    infra_engineer|tester|qa|clawsentinel)
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
    planner|dev|admin|scrum_master) return 0 ;;
    *) return 1 ;;
  esac
}
