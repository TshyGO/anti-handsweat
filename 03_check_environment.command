#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
source "$ROOT/mac_common.sh"
check_macos
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || fail_mac "请先运行 01_install_mac.command。"
mkdir -p "$ROOT/logs"
"$PY" "$ROOT/check_environment.py" --output "$ROOT/logs/environment_manual_check.json" || fail_mac "环境检查未通过，请查看上面的信息。"
printf '\n环境记录已保存至 logs/environment_manual_check.json\n'
pause_mac
