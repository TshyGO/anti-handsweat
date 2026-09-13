#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
source "$ROOT/mac_common.sh"
check_macos
mkdir -p "$ROOT/logs"
LOG="$ROOT/logs/install_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1
trap 'rc=$?; printf "\n安装中断。请保留日志：%s\n" "$LOG"; pause_mac; exit "$rc"' ERR
printf '涂层图像准备 V0.1.1 Mac：首次安装\n目录：%s\n' "$ROOT"
PY="$(select_python)" || fail_mac "未找到带 Tk 的 Python 3.13 或 3.12。请先打开 00_Mac开始这里.html，安装 python.org 的 universal2 版本。"
ARCH="$("$PY" -c 'import platform; print(platform.machine())')"
if [ "$(/usr/sbin/sysctl -in hw.optional.arm64 2>/dev/null || echo 0)" = "1" ] && [ "$ARCH" != "arm64" ]; then
    fail_mac "当前 Python 正在 Intel/Rosetta 模式运行。请安装并使用原生 universal2 Python，关闭终端的 Rosetta 模式后重试。"
fi
case "$ARCH" in arm64|x86_64) ;; *) fail_mac "不支持的 Python 架构：$ARCH" ;; esac
printf 'Python：%s\n进程架构：%s\n' "$PY" "$ARCH"
if [ -e "$ROOT/.venv" ]; then
    [ -x "$ROOT/.venv/bin/python" ] || fail_mac ".venv 不完整。请在 Finder 用 Command+Shift+. 显示隐藏文件，只移除本工具目录的 .venv 后重试。"
    OLD_ARCH="$("$ROOT/.venv/bin/python" -c 'import platform; print(platform.machine())')"
    [ "$OLD_ARCH" = "$ARCH" ] || fail_mac "现有 .venv 的架构不同。请仅移除本工具目录的 .venv，然后重新安装。"
else
    "$PY" -m venv "$ROOT/.venv"
fi
rm -f "$ROOT/.installation_ready"
VPY="$ROOT/.venv/bin/python"
"$VPY" -c 'import sys, tkinter; assert sys.version_info[:2] in ((3,12),(3,13)); r=tkinter.Tk(); r.withdraw(); r.update_idletasks(); r.destroy()'
printf '\n安装固定版本依赖，只使用预编译包；首次安装需要联网。\n'
"$VPY" -m pip install --only-binary=:all: -r "$ROOT/requirements.txt"
"$VPY" -m pip check
"$VPY" -m pip freeze > "$ROOT/installed_environment.txt"
"$VPY" -m unittest discover -s "$ROOT/tests" -p 'test_*.py' -v
"$VPY" "$ROOT/check_environment.py" --output "$ROOT/logs/environment_after_install.json"
"$VPY" -c 'from pathlib import Path; Path(".installation_ready").write_text("0.1.1-mac-development\n")'
printf '\n安装完成。以后双击 02_start_mac.command 打开转换窗口。\n安装日志：%s\n' "$LOG"
pause_mac
