#!/usr/bin/env bash

RUNNER_MODULE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# shellcheck source=/dev/null
source "${RUNNER_MODULE_DIR}/config.sh"
# shellcheck source=/dev/null
source "${RUNNER_MODULE_DIR}/bootstrap.sh"
# shellcheck source=/dev/null
source "${RUNNER_MODULE_DIR}/role_routing.sh"
# shellcheck source=/dev/null
source "${RUNNER_MODULE_DIR}/retries.sh"
# shellcheck source=/dev/null
source "${RUNNER_MODULE_DIR}/retries_transport.sh"
# shellcheck source=/dev/null
source "${RUNNER_MODULE_DIR}/retry_policy.sh"
# shellcheck source=/dev/null
source "${RUNNER_MODULE_DIR}/prompt_contract.sh"
# shellcheck source=/dev/null
source "${RUNNER_MODULE_DIR}/contracts.sh"
# shellcheck source=/dev/null
source "${RUNNER_MODULE_DIR}/telemetry.sh"
# shellcheck source=/dev/null
source "${RUNNER_MODULE_DIR}/runtime_context.sh"
# shellcheck source=/dev/null
source "${RUNNER_MODULE_DIR}/locks.sh"
# shellcheck source=/dev/null
source "${RUNNER_MODULE_DIR}/message_bus.sh"
# shellcheck source=/dev/null
source "${RUNNER_MODULE_DIR}/tshape.sh"
# shellcheck source=/dev/null
source "${RUNNER_MODULE_DIR}/session_channel.sh"
# shellcheck source=/dev/null
source "${RUNNER_MODULE_DIR}/tshape_dispatch.sh"

runner_modules_init() {
  export RUNNER_MODULES_LOADED=1
  export RUNNER_MODULES_VERSION="v1"
}
