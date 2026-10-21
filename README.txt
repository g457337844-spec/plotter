绘图器 / Plotter 1.0

统一 XPS 和 XRD 数据导入、检查、预览及 Origin 原生绘图。
桌面入口：main.py；标准 stdio MCP 入口：mcp_entry.py。
所有 Origin COM 调用由 service.Broker 的同一线程执行；GUI 和 MCP 共用同一业务服务。

开发环境：Windows 10/11 x64，Python 3.13。
安装 requirements.txt 中的依赖后，运行 python main.py。
打包还需要 PyInstaller 6.21.0：python -m PyInstaller build.spec --noconfirm。
完整 dist/Plotter 文件夹是便携软件，不可只复制 exe。

测试：
  python -m pytest tests/test_core.py tests/test_transactions.py tests/test_gui.py tests/test_origin_safety.py -q
  python tests/validate_mcp.py
  python tests/validate_packaged_ui.py

真实 Origin 验证脚本会创建独立进程；仅在确认新进程且返回空工程后开始绘图。
  tests/validate_real_origin.py：两份真实数据的 6 页分别绘图及回读校验。
  tests/validate_stacks.py：XRD 多层、参考卡、叠加、XPS 多层及缺失分峰点。
  tests/validate_mcp_gui.py <软件目录> <验证输出目录>：打包程序与 MCP、Origin 联动；保留成图和桌面窗口供复核。
这些脚本中的样本路径需要按测试电脑调整。

关键目录：
  studio/models.py：数据模型及有限数值校验
  studio/parsers.py：表格、XRD 文本及 PDF 参考卡文本解析
  studio/planning.py：绘图分组、单位及范围检查
  studio/origin.py：进程和工程保护、原生图页、轴标题、数据回读与失败回滚
  studio/service.py：共享工作区、串行任务服务、自动恢复
  studio/bridge.py：仅本机、随机令牌验证的桌面接口
  studio/mcp_server.py：标准 MCP 工具，未开放任意脚本执行
  studio/gui.py：Qt 桌面界面、自身渲染接口

图页使用用户 Origin 的 Origin 模板；页尺寸、绘图区宽度、坐标轴字体来自模板。
保留原生 xb/yl 轴标题。多曲线缩放后恢复模板的标题中心与边距；长 Y 刻度的宽度由 Origin 自己测量。
分层图保留完整默认外框，并将子层的 X 轴链接到共享轴层。
程序不保存、重置或退出已存在的 Origin 工程。

打包说明：Qt 的 VC 运行库在软件目录中保持一致，使用 Windows 的系统 ICU。
构建电脑 PATH 中其他程序（如 Poppler）的 ICU 不能混入；build.spec 已处理这一冲突。

项目源码和便携运行库应一并备份。旧版 XPS/XRD 的原始代码另有独立备份，未被本版覆盖。


## 关联项目与开源说明

[Origin Spectra MCP](https://github.com/g457337844-spec/origin-spectra-mcp) 是工具组的核心 MCP 服务；[Avantage MCP](https://github.com/g457337844-spec/avantage-mcp) 提供光谱处理和曲线导出。现有能力与跨工具一键绘图目标见 [docs/ecosystem.md](docs/ecosystem.md)。独立 Plotter 已能直接连接 Origin，不必再启动 Origin Spectra MCP。

[MIT 许可](LICENSE) · [第三方说明](NOTICE) · [贡献指南](CONTRIBUTING.md) · [安全说明](SECURITY.md)。Origin 商业软件不随项目提供。
