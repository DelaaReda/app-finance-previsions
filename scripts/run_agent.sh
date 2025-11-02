#!/usr/bin/env bash
set -euo pipefail

# Simple wrapper to run the OSS agent with G4F + strong embeddings
# Usage: bash scripts/run_agent.sh -g "Your goal" [-e HF_EMBED_MODEL] [-m G4F_MODELS]

AGENT_DIR="agent-stack-oss"
VENV="$AGENT_DIR/.venv"

GOAL=""
EMBED_MODEL="intfloat/multilingual-e5-large-instruct"
G4F_MODELS_DEFAULT="deepseek-ai/DeepSeek-R1-0528,deepseek-ai/DeepSeek-V3-0324-Turbo,deepseek-ai/DeepSeek-V3,Qwen/Qwen3-235B-A22B-Thinking-2507,Qwen/Qwen3-235B-A22B-Instruct-2507,Qwen/Qwen3-Next-80B-A3B-Instruct,zai-org/GLM-4.5,meta-llama/Llama-3.3-70B-Instruct-Turbo,openai/gpt-oss-120b"
MODELS="$G4F_MODELS_DEFAULT"

while getopts ":g:e:m:" opt; do
  case $opt in
    g) GOAL="$OPTARG" ;;
    e) EMBED_MODEL="$OPTARG" ;;
    m) MODELS="$OPTARG" ;;
    *) echo "Usage: $0 -g \"goal\" [-e HF_EMBED_MODEL] [-m G4F_MODELS]" >&2; exit 2 ;;
  esac
done

if [[ -z "$GOAL" ]]; then
  echo "ERROR: provide -g \"goal\"" >&2
  exit 1
fi

if [[ ! -d "$VENV" ]]; then
  echo "Creating venv at $VENV"
  python3 -m venv "$VENV"
fi

source "$VENV/bin/activate"
pip install -q --disable-pip-version-check -r "$AGENT_DIR/requirements.txt"

pushd "$AGENT_DIR" >/dev/null
export LLM_PROVIDER="g4f"
export HF_EMBED_MODEL="$EMBED_MODEL"
export G4F_TEMPERATURE="${G4F_TEMPERATURE:-0.2}"
export G4F_MAX_TOKENS="${G4F_MAX_TOKENS:-2048}"
export G4F_TIMEOUT="${G4F_TIMEOUT:-60}"
export G4F_RETRIES="${G4F_RETRIES:-1}"
export G4F_MODELS="${G4F_MODELS:-$MODELS}"

mkdir -p docs
[[ -f docs/README.md ]] || echo "Agent OSS doc placeholder" > docs/README.md

echo "Running agent with HF_EMBED_MODEL=$HF_EMBED_MODEL"
PYTHONPATH=. python -m src.agent.run --goal "$GOAL"
popd >/dev/null

