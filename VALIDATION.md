# V0.1.1 Mac 检查记录

## 状态

DEVELOPMENT_NOT_VALIDATED。Mac 启动流程已编写，当前执行环境为 Linux，未在 Mac 实机验证。

## 本次修改

1. Windows BAT 入口替换为三个 macOS command 入口，支持 Finder 双击及带空格的目录。
2. 自动发现 python.org / Homebrew 的 Python 3.13 或 3.12，要求带 Tk；不调用系统 Xcode Python。
3. Apple 芯片选择 rawpy 0.27.1，Intel 选择有官方 wheel 的 0.25.1。采用固定版本和 binary-only 安装，遇到不支持组合停止。
4. ExifTool 自动搜索 PATH、官方及 Homebrew 位置；选择文件时使用 Mac 说明。
5. 元数据额外记录并核对操作系统与进程架构，防止把不同解码环境直接作为同一配置使用。
6. 原有 TIFF 示例和两个 ImageJ 宏原样保留。没有改变灰度公式、固定 ROI 或 V 的定义。

## 已检查的范围

18 项 Python 测试全部通过。具体结果与环境见 tests/test_run_log.txt。所有测试均为合成数据、文件读写或路径解析逻辑。
脚本已执行 bash -n 语法检查。这无法替代 macOS Bash 3.2、Finder、Gatekeeper 及本机依赖安装测试。
Python 源文件已执行 py_compile 语法检查。
已在 Linux/Xvfb 中完成 GUI 构建、忙碌状态切换和退出检查，记录在 tests/gui_smoke.txt；Linux Tk 的检查不能代表 Mac Tk 的显示和权限行为。

## 尚未完成

未在 Apple 芯片或 Intel Mac 上执行安装和 GUI 操作。
未实际安装/导入 rawpy，也未解码用户的真实 RAW。
未执行 ExifTool 的真实元数据读取或正式图像配准。
未运行完整 Fiji 宏。两个宏原样保留，其预期值已由 Python 独立核对。
未完成色彩/亮度标定、重复性、跨设备等效性或真实涂层性能验证。
官方提供 wheel 是安装兼容性依据，不能替代实机测试。

## 首次现场检查

先运行 Fiji 算术宏核对 0.03125，再用 demo TIFF 核对 0.0078125。
成功安装后，使用一张已有 RAW 建立练习配置，核查读取、位深、元数据和日志。
用同一 RAW、同一配置重复转换，比较分析数组。日志时间戳可不同。
收到拍摄装置后建立正式配置，与练习结果隔离保存。
