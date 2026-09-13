# Anti-handsweat coating imaging tools

用于涂层留印/擦拭实验的 RAW 解码与 ImageJ 分析准备工具。

本项目负责将 RAW 转换为统一参数的分析 TIFF，并记录元数据与处理环境；图像差分分析继续使用独立的 Fiji/ImageJ 及 `imagej/` 下的宏。

当前版本为开发版，尚未完成真实设备、Mac/Windows 实机和方法学验证。请勿把输出指标直接解释为物理亮度、污染物质量或涂层合格判定。

## 目录

- `pipeline.py`：RAW 转换和输出核心
- `converter_gui.py`：桌面操作界面
- `imagej/`：Fiji/ImageJ 宏
- `demo/`：合成 TIFF 和预期数值
- `tests/`：自动化测试

真实照片、输出目录和本地虚拟环境不应提交到仓库。
