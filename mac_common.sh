#!/bin/bash
# Shared helpers; compatible with the Bash 3.2 provided by macOS.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
pause_mac() { if [ -t 0 ]; then printf '\n按回车关闭此窗口。'; IFS= read -r _answer || true; fi; }
fail_mac() { printf '\n未完成：%s\n' "$1" >&2; pause_mac; exit 1; }
check_macos() {
    [ "$(uname -s)" = "Darwin" ] || fail_mac "此启动脚本用于 macOS。"
    mac_major=$(/usr/bin/sw_vers -productVersion | /usr/bin/cut -d. -f1)
    [ "$mac_major" -ge 11 ] || fail_mac "本包的起步安装方案要求 macOS 11 或更高；旧系统可先单独使用兼容的 Fiji。"
}
select_python() {
    # Prefer native python.org frameworks, avoiding /usr/bin/python3 (Xcode stub).
    for p in       /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13       /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12       /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3.12       /opt/homebrew/opt/python@3.13/bin/python3.13 /opt/homebrew/opt/python@3.12/bin/python3.12       /usr/local/bin/python3.13 /usr/local/bin/python3.12       /usr/local/opt/python@3.13/bin/python3.13 /usr/local/opt/python@3.12/bin/python3.12
    do
        [ -x "$p" ] || continue
        if "$p" -c 'import sys, tkinter; assert sys.version_info[:2] in ((3,12),(3,13))' >/dev/null 2>&1; then
            if "$p" -c 'import sysconfig; assert not sysconfig.get_config_var("Py_GIL_DISABLED")' >/dev/null 2>&1; then
                printf '%s\n' "$p"; return 0
            fi
        fi
    done
    return 1
}
