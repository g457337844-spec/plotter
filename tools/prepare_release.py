from pathlib import Path
import shutil,json,hashlib,zipfile,sys
ROOT=Path(__file__).resolve().parents[1]
OUTPUTS=ROOT.parents[1]/'outputs'
RELEASE=OUTPUTS/'绘图器_1.0'
DESKTOP=Path(r'E:\Desktop\文件\工具\绘图器\绘图器 1.0')

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def write(path,text): path.write_text(text,encoding='utf-8-sig')

def main():
    RELEASE.mkdir(parents=True,exist_ok=True)
    software=RELEASE/'软件'
    shutil.copytree(ROOT/'dist'/'Plotter',software,dirs_exist_ok=True)
    source=RELEASE/'源码'; source.mkdir(exist_ok=True)
    for name in ('main.py','mcp_entry.py','requirements.txt','requirements-dev.txt','build.spec','version_info.txt','mcp_version_info.txt','README.txt','README.md','.gitignore'):
        shutil.copy2(ROOT/name,source/name)
    for name in ('studio','assets','tests','tools'):
        shutil.copytree(ROOT/name,source/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','*.pyc'))
    guide=r'''绘图器 1.0 · 使用说明

这是合并后的 XPS / XRD 绘图软件。双击“软件”里的“绘图器.exe”，或桌面绘图器文件夹里的同名快捷方式。
整个软件文件夹都需要保留；绘图器-MCP.exe 和 _internal 是自动化接口及运行库。
本机无需另装 Python。Origin 需要正常安装；xlsx 可直接读取，xls / xlsb 和“读取当前 Excel”需要 Excel。

三步使用
1. 点击“导入数据”或拖入文件。TC.xlsx 会识别出 5 个 XPS 谱区；1.txt 是 XRD。
2. 勾选需要绘制的数据，查看预览和右侧设置。双击样品名称可改名，双击颜色圆点可改色。
   点击 ↑ / ↓ 或 Alt+↑ / Alt+↓ 调整绘图顺序。“全选”只作用于当前分类。
3. 选择 Origin 目标并点击“在 Origin 中绘图”。图页、曲线和数据表都可以继续在 Origin 编辑。

绘图方式
分别绘图：每个 XPS 谱区或每份 XRD 数据独立成页。
分层对比：XPS 按能级分组，XRD 放在同一页；保留默认外框，各层横坐标关联。
曲线叠加：同一坐标比较样品。XPS 比较实测曲线，分峰数据仍保存在工作区；分别绘图和分层绘图保留分峰。
一页最多 8 层，每层最多叠加 8 个样品；PDF 参考卡可选，与 XRD 一起勾选。
“PDF 参考卡”指 PDF#21-1276 等衍射卡片的 txt 文本，不是 .pdf 文档。

尺寸和轴标题
默认使用本机 Origin 的 Origin 模板。不会改写页宽、页高、绘图区宽度或坐标轴字体。
这台电脑实测默认页尺寸为 10.72 × 8.205 in；这个值来自本机模板，软件没有把它写死。
预览 PNG 的宽度是 1600 像素，属于预览清晰度，不改变 Origin 图页实际尺寸。
使用 Origin 原生 xb / yl 轴标题，保留字体及坐标轴关联；多曲线缩放后恢复模板的中心和边距。
纵轴单位优先读取数据表，未提供单位时会显示提示，不会把首行数值当成单位。
Origin 本身把原生轴标题实现为特殊文字对象；关键是保留其轴标题身份，而不是额外叠一个普通文字框。
如果你的手绘图使用其他自定义模板，可在“更多设置”填写同名 Origin 模板，以统一排版。

数据和选项
原始文件不会被修改。重新导入同一来源会更新数据，保留名称、颜色和勾选状态。
列含缺失点时保留曲线并断开；NaN、无穷大、非法数值和无数据的范围会阻止成图，并给出提示。
XPS 使用表格已有的实测、分峰、包络和背景列；本软件不执行新的分峰拟合。
XRD 归一化为 (I-Imin)/(Imax-Imin) × 100%，恒定强度显示为 0；原始强度仍保留在独立列中。
没有参考卡也可以画 XRD。参考峰是可编辑的 Origin 数据曲线。
“显示 XPS 峰位数值”显示已有分峰曲线的最大值位置，不代表独立重新拟合出的峰位。
XPS 和 XRD 共同勾选时建议使用自动范围；手动范围需要按数据类型分别设置。

工作区和 Origin 工程
“保存”保存 .json 工作区，包括数据快照、名称、颜色和绘图选项，不是保存 Origin .opju 工程。
工作区修改会自动恢复到 %LOCALAPPDATA%\Plotter\recovery.json。
成图需在 Origin 中自行保存为 .opju。已有 Origin 工程不会被本软件自动保存、重置或关闭。
“当前 Origin 窗口”要求只打开一个 Origin 进程。多个窗口时，选择“新建独立 Origin 窗口”。
独立模式会验证新进程及空工程；不能确认时停止。Origin 工程切换后需重新连接。
关闭工作台不会关闭 Origin；绘图正在进行时会等待完成后关闭。

MCP 自动化
在软件左下角点击“自动化接口”，可以复制当前安装位置的配置。
同目录 MCP配置.json 给出了这台电脑桌面版本的标准 stdio 配置，供支持 MCP 的客户端使用。
MCP 不需要一直进行屏幕点击，可导入、改名、改色、设置范围、校验、绘图、回读尺寸、打开成图、保存工作区和渲染本软件窗口。
桌面软件已打开时，MCP 连接同一个工作区；未打开时，运行独立工作区。
自动化入口使用 绘图器-MCP.exe，不是双击 GUI 程序来运行 MCP。
这次已经实际验证标准 MCP 客户端与打包软件、真实 Origin 的联动；未自动修改其他客户端的全局 MCP 设置。
只提供本软件的业务操作，不提供任意脚本执行。桌面连接仅监听本机，并使用随机令牌。

查看诊断
%LOCALAPPDATA%\Plotter 中保存错误诊断和预览图。
本次测试记录、成图和示例工作区放在本目录“验证与预览”中。
源码及构建说明在“源码”中；原来两个软件和其源码备份另行保留。

官方参考
Origin 原生轴标题：https://docs.originlab.com/labtalk/guide/creating-and-accessing-graphical-objs/
Origin 图层及尺寸：https://docs.originlab.com/labtalk/ref/layer-obj/
Origin 图层关联：https://docs.originlab.com/x-function/ref/laylink/
标准 MCP Python SDK：https://github.com/modelcontextprotocol/python-sdk
界面参考 Apple 的简约材质、圆角与导航设计：https://developer.apple.com/design/human-interface-guidelines/materials
'''
    write(RELEASE/'使用说明.txt',guide)
    changes=r'''本轮优化 · 1.0

两个独立绘图器合并为一个绘图器，共用导入、数据检查、绘图计划、Origin 连接和保存逻辑。
界面重做为浅色、圆角、简约的 iOS 26 风格，增加分类、拖入、预览、样品排序及更清楚的操作步骤。

已修复及防护的主要问题：
实测列被辅助 Index 列抢先识别；单位行与首行数据混淆；一个缺失分峰点使整列消失；空行截断后续数据；
XRD 中 100oops 等数值前缀误接受；无穷大和溢出输入；非法范围在连接 Origin 后才发现；PDF# 空格识别不一致；
不同强度单位混入同一对比图；恒定强度归一化；重复导入产生重复条目；多层图首条曲线被一起隐藏；
多层图标题、图例和刻度挤压；GUI 与自动化状态不同步；缩小窗口后控件重叠；打包运行库冲突；MCP 关闭时的标准流错误。

成图以本机 Origin 模板为基准，保留页尺寸、绘图区宽度和原生轴标题，不再使用额外普通文本框模拟纵轴标题。
XPS 保留现有分峰、包络、背景和实测曲线；XRD 支持单独绘图、对比以及可选参考卡。
原始数据通过 Origin 回读验证。绘图失败清理本次新增页面，不删除原有页面。

已提供 12 个标准 MCP 工具，并验证与桌面窗口共用工作区。源码、便携程序、配置和测试记录一起备份。

测试期间的 Origin 会话事件：早期探测意外复用了并关闭了原有 FTIR 窗口，没有保存或覆盖原工程文件。
随后已从 E:\Desktop\小图\第一体系\FTIR.opju 恢复打开，确认有 3 个页面；原窗口当时是否有未保存修改无法确认。
新版增加新进程、空工程、工程身份和多窗口校验，禁止退出已有会话。相应防护有独立回归测试。
'''
    write(RELEASE/'本轮优化说明.txt',changes)
    config={'mcpServers':{'plotter':{'command':str(DESKTOP/'软件'/'绘图器-MCP.exe'),'args':[]}}}
    (RELEASE/'MCP配置.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    if DESKTOP.exists() and not (DESKTOP/'本轮优化说明.txt').is_file():
        raise RuntimeError('桌面目标文件夹已存在且不是本次发布，已停止覆盖')
    shutil.copytree(RELEASE,DESKTOP,dirs_exist_ok=True)
    import win32com.client
    shell=win32com.client.Dispatch('WScript.Shell')
    shortcut=shell.CreateShortcut(str(DESKTOP.parent/'绘图器.lnk'))
    shortcut.TargetPath=str(DESKTOP/'软件'/'绘图器.exe'); shortcut.WorkingDirectory=str(DESKTOP/'软件')
    shortcut.IconLocation=str(DESKTOP/'软件'/'绘图器.exe')+',0'; shortcut.Description='统一 XPS / XRD Origin 绘图工作台'; shortcut.Save()
    print(json.dumps({'release':str(RELEASE),'desktop':str(DESKTOP),'software_files':sum(1 for p in software.rglob('*') if p.is_file()),'software_MB':round(sum(p.stat().st_size for p in software.rglob('*') if p.is_file())/1024**2,1)},ensure_ascii=True))

if __name__=='__main__': main()
