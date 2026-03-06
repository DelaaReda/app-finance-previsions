#!/usr/bin/env bash

runner_normalize_role() {
  local role="${1:-}"
  local po_scrum_enabled="${2:-0}"
  local scrum_mode="${3:-${FC_SCRUM_MASTER_MODE:-operational}}"
  case "$role" in
    vision-architect-tasks-planner|vision_architect_tasks_planner)
      printf "planner\n"
      ;;
    analyst|architect|po)
      printf "planner\n"
      ;;
    scrum_master)
      if [[ "$scrum_mode" == "operational" ]]; then
        printf "scrum_master\n"
      elif [[ "$po_scrum_enabled" == "1" ]]; then
        printf "scrum_master\n"
      else
        printf "planner\n"
      fi
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
    planner|dev|admin|scrum_master) return 0 ;;
    *) return 1 ;;
  esac
}
