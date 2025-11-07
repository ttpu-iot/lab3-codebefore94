#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REQUIREMENTS_FILE="${WORKSPACE_DIR}/client/requirements.txt"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

VENVPY="${WORKSPACE_DIR}/.venv/bin/python"
if [ ! -x "${VENVPY}" ]; then
  "${PYTHON_BIN}" -m venv "${WORKSPACE_DIR}/.venv"
fi

"${VENVPY}" -m pip install --upgrade pip

if [ -f "${REQUIREMENTS_FILE}" ]; then
  "${WORKSPACE_DIR}/.venv/bin/pip" install -r "${REQUIREMENTS_FILE}"
else
  echo "Warning: ${REQUIREMENTS_FILE} not found; skipping dependency installation." >&2
fi
