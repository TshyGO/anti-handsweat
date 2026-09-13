#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
source "$ROOT/mac_common.sh"
check_macos
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] && [ -f "$ROOT/.installation_ready" ] || fail_mac "请先成功运行 01_install_mac.command。"
mkdir -p "$ROOT/logs"
LOG="$ROOT/logs/gui_$(date +%Y%m%d_%H%M%S).log"
"$PY" "$ROOT/check_environment.py" --output "$ROOT/logs/environment_last_start.json" > "$LOG" 2>&1 || fail_mac "环境检查失败，请打开日志：$LOG"
# Detach safely: the Terminal window may be closed after the GUI appears.
nohup "$PY" "$ROOT/converter_gui.py" >> "$LOG" 2>&1 < /dev/null &
PID=$!
sleep 2
if kill -0 "$PID" 2>/dev/null; then
    printf '已启动转换窗口。此终端窗口可以关闭。\n日志：%s\n' "$LOG"
else
    cat "$LOG"
    fail_mac "窗口没有成功启动，请保留上面的日志。"
fi
