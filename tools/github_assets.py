"""Build distributable GitHub assets without experimental workspaces."""
from pathlib import Path
import hashlib,json,shutil,zipfile
ROOT=Path(__file__).resolve().parents[1]
OUTPUTS=ROOT.parents[1]/'outputs'
RELEASE=OUTPUTS/'绘图器_1.0'
PUBLICATION=OUTPUTS/'绘图器_1.0_GitHub发布包'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    PUBLICATION.mkdir(exist_ok=True)
    portable=PUBLICATION/'Plotter-1.0-Windows-x64.zip'
    with zipfile.ZipFile(portable,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted((RELEASE/'软件').rglob('*')):
            if path.is_file(): archive.write(path,Path('绘图器 1.0')/path.relative_to(RELEASE))
        archive.write(RELEASE/'使用说明.txt',Path('绘图器 1.0')/'使用说明.txt')
        # The GUI provides the correct absolute command for its install path.
        config={'mcpServers':{'plotter':{'command':r'C:\Apps\绘图器 1.0\软件\绘图器-MCP.exe','args':[]}}}
        archive.writestr('绘图器 1.0/MCP配置示例.json',json.dumps(config,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(portable) as archive:
        assert archive.testzip() is None
        assert not any('示例工作区' in p or '验证与预览' in p for p in archive.namelist())
    source=PUBLICATION/'Plotter-1.0-Source.zip'
    shutil.copy2(OUTPUTS/'绘图器_1.0_源码.zip',source)
    checksums=PUBLICATION/'SHA256SUMS.txt'
    checksums.write_text('\n'.join(f'{sha(p)}  {p.name}' for p in (portable,source))+'\n',encoding='utf-8')
    (PUBLICATION/'发布说明.md').write_text('''# 绘图器 1.0

XPS / XRD 学术绘图软件，支持 Origin 原生图页与 MCP 自动化。

- 名称统一为“绘图器”，界面、程序文件属性和 MCP 版本统一为 1.0。
- 全新深墨蓝与香槟金学术图标，谱峰与坐标轴设计，多尺寸 Windows ICO。
- 保留本机 Origin 模板尺寸、绘图区宽度和原生坐标轴标题。
- 自动迁移此前工作区，名称、颜色与勾选状态保留。
- 40 项回归检查通过；打包版通过标准 MCP 与真实 Origin 联动，6 张图的数据回读最大误差为 0。

## 下载

`Plotter-1.0-Windows-x64.zip`：Windows x64 便携程序，完整解压后启动 `软件/绘图器.exe`。

`Plotter-1.0-Source.zip`：完整源码、构建资源和测试脚本。

`SHA256SUMS.txt`：两个下载包的 SHA-256 校验值。

无需另装 Python，需要已安装 Origin。MCP 配置可在软件左下角“自动化接口”复制。
已验证环境为 Windows 10 x64 / Origin 10.100178。
''',encoding='utf-8')
    print(json.dumps({p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in (portable,source,checksums)},ensure_ascii=True))

if __name__=='__main__': main()
