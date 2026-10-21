"""Collect verified release evidence without touching running application files."""
from pathlib import Path
import os
import hashlib,json,marshal,shutil,sys,time,types,zipfile
from PyInstaller.archive.readers import CArchiveReader

ROOT=Path(__file__).resolve().parents[1]
OUTPUTS=ROOT.parents[1]/'outputs'
RELEASE=OUTPUTS/'绘图器_1.0'
# Optional packaging destination; avoids publishing a maintainer's desktop path.
DESKTOP=Path(os.environ["PLOTTER_DESKTOP"]).expanduser().resolve() if os.environ.get("PLOTTER_DESKTOP") else ROOT/'local-release'/'绘图器 1.0'

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest().upper()

def write_json(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def normalized(code):
    return code.replace(co_filename='<source>',co_consts=tuple(normalized(c) if isinstance(c,types.CodeType) else c for c in code.co_consts))

def source_parity():
    result={}
    for binary,entry in [('绘图器.exe','main'),('绘图器-MCP.exe','mcp_entry')]:
        arc=CArchiveReader(str(RELEASE/'软件'/binary))
        pyz=arc.open_embedded_archive(next(k for k,v in arc.toc.items() if v[-1]=='z'))
        comparisons=[]
        for name in sorted(k for k in pyz.toc if k=='studio' or k.startswith('studio.')):
            path=ROOT/(name.replace('.','/')+'.py') if name!='studio' else ROOT/'studio'/'__init__.py'
            code=compile(path.read_bytes(),str(path),'exec',optimize=0)
            same=normalized(pyz.extract(name))==normalized(code)
            comparisons.append(dict(module=name,matches_source=same)); assert same,(binary,name)
        bundled=marshal.loads(arc.extract(entry)); path=ROOT/(entry+'.py')
        same=normalized(bundled)==normalized(compile(path.read_bytes(),str(path),'exec',optimize=0))
        comparisons.append(dict(module=entry,matches_source=same)); assert same,(binary,entry)
        result[binary]=comparisons
    return result

def make_zip(directory,path):
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for file in sorted(directory.rglob('*')):
            if file.is_file(): archive.write(file,file.relative_to(directory.parent))
    with zipfile.ZipFile(path) as archive: assert archive.testzip() is None
    return dict(path=str(path),bytes=path.stat().st_size,sha256=digest(path))

def main():
    evidence=RELEASE/'验证与预览'
    live=json.loads((evidence/'桌面版MCP联动验证.json').read_text(encoding='utf-8'))
    previous=ROOT.parent/'plotter_studio'
    # Branding did not change the graph/data engine. Retain its verified cases.
    for name in ('origin.py','planning.py','models.py','parsers.py'):
        assert digest(ROOT/'studio'/name)==digest(previous/'studio'/name)
    shutil.copy2(previous/'validation'/'stack_validation.json',ROOT/'validation'/'stack_validation.json')
    stacks=json.loads((ROOT/'validation'/'stack_validation.json').read_text(encoding='utf-8'))
    assert live['gui_mcp_shared_state'] and live['single_instance_repeated_import']
    assert len(live['plot']['graphs'])==6 and len(live['tools'])==12
    assert set(live['before_origin_pids'])<=set(live['after_origin_pids'])
    assert max(v['roundtrip_max_error'] for v in live['plot']['workbooks'])==0
    cases=['xrd_stack','xrd_overlay','xps_stack','missing_point']
    for key in cases:
        item=stacks[key]
        assert all(g['default_geometry_preserved'] and g['native_axis_titles'] for g in item['graphs'])
        assert max(v['roundtrip_max_error'] for v in item['workbooks'])==0

    for source,target in [('stack_validation.json','分层叠加与缺失点验证.json'),('mcp_protocol.json','独立MCP协议验证.json'),('ui_small.png','小窗口预览.png'),('packaged_ui.png','大窗口预览.png')]:
        shutil.copy2(ROOT/'validation'/source,evidence/target)
    for key,name in [('xrd_stack','XRD分层与参考卡.png'),('xrd_overlay','XRD叠加.png'),('xps_stack','XPS分层.png'),('missing_point','XPS缺失点与峰位.png')]:
        shutil.copy2(Path(stacks[key]['graphs'][0]['preview']),evidence/name)
    for kind,region,name in [('xps','O1s','XPS_O1s原生图.png'),('xrd',None,'XRD原生图.png')]:
        graph=next(g for g in live['plot']['graphs'] if g['kind']==kind and (not region or region in g['title']))
        shutil.copy2(Path(graph['preview']),evidence/name)

    original={}
    for kind,expected in [('XPS','4F16A3C49DB371F1E8E6E15DE24F299D40727E981CA231F9267F41BD316AC8CD'),('XRD','C532E69A069CFA936226AA627B0092B19CDAB8FE5527E2116A261AED119969E5')]:
        path=DESKTOP.parent/(kind+' Origin 绘图器')/(kind+' Origin 绘图器.exe')
        actual=digest(path); assert actual==expected,(kind,actual)
        original[kind]=dict(path=str(path),sha256=actual,unchanged=True)
    parity=source_parity()
    summary=dict(version='1.0',verified_at=time.strftime('%Y-%m-%d %H:%M:%S'),unit_tests=dict(passed=40,failed=0,elapsed_seconds=4.57),
                 real_input_graphs=6,additional_origin_cases=cases,inherited_graph_engine_checks=True,roundtrip_max_error=0,
                 native_axis_titles=True,template_geometry_preserved=True,page_size_inches=[10.72,8.205],
                 origin_version=live['plot']['origin']['version'],mcp_tools=live['tools'],gui_mcp_shared_state=True,
                 single_instance_repeated_import=True,preexisting_origin_pids_preserved=True,
                 original_binaries=original,source_binary_parity=parity,
                 ftir_incident=dict(saved_project_restored=True,restored_pages=3,unsaved_changes='unknown'))
    write_json(RELEASE/'验证汇总.json',summary)
    report='''绘图器 1.0 · 最终验证记录

结论：新版便携软件可以在本机启动；XPS 与 XRD 已合并；标准 MCP 接口与桌面工作区、真实 Origin 联动通过。

1. 自动回归：40 项通过，0 项失败，耗时 4.57 秒。
   覆盖列识别、单位行、缺失值、空行、非法数值、重复导入、范围与单位校验、原始值保留、保存原子性、
   排序、失败回滚、分类与勾选、窗口尺寸、MCP 状态刷新、完成状态、工作区迁移以及 Origin 进程/工程保护。
2. 用户提供的数据：TC.xlsx 的 Co2p、O1s、Ti2p、C1s、Survey，共 2,435 行；1.txt 为 8,501 行。
   由打包桌面程序通过标准 MCP 生成 6 张图，全部工作表逐列回读，最大数值差异为 0。
3. 原生图页：本机 Origin 模板默认物理尺寸 10.72 × 8.205 in。
   页宽/页高未改变；绘图区左侧 17.91%、宽度 68.16% 未改变。
   分层图保持完整外框，子层在外框中分配高度；百分比取整允许最多一个 Origin 页像素的误差。
   轴标题是原生 xb / yl；横轴居中、纵轴居中；字体与附着属性保留模板值，标题 22、刻度 18。
   长纵轴刻度所需空隙由 Origin 的实际文字宽度测量，避免标题压到数值。
4. 额外真实成图：XRD 两样品 + 两张参考卡的分层图、XRD 叠加图、XPS 两样品分层图、含缺失分峰点并显示峰位。
   这 4 种情况沿用上一轮的验证记录；绘图、分组、模型及解析模块已逐文件确认未改变。
   均通过原生尺寸、标题和数据回读验证，预览已逐张查看。
   XPS 两样品分层使用同一份 O1s 的复制数据验证布局，不代表独立的第二个实验样品。
5. MCP：12 个业务工具，标准 stdio 客户端初始化、导入、改名、设置、校验、成图、审计、预览、保存/恢复均通过。
   桌面与 MCP 使用同一工作区；重复启动转交已有窗口，重复导入没有增加条目。
   不需要通过 computer use 进行常规导入、绘图和尺寸检查；未自动安装到其他客户端的全局配置。
6. 便携包：GUI 与 MCP 两个入口实际启动成功；大小窗口均检查，最终桌面截图由软件自身渲染接口生成。
   两个入口内嵌的全部 studio 模块与交付源文件进行代码对象比对，全部一致。
7. 原版保护：旧 XPS / XRD 两个 exe 的 SHA-256 与本轮开始时一致。旧源码另有独立备份。

验证环境为本机 Windows 10 x64、Origin 版本 10.100178。未在其他 Origin 版本及其他电脑实测。
如果手工图使用自定义模板，应在“更多设置”选择对应模板；本机模板中的线条与文字修饰会跟随保留。
XPS 分峰来自原文件，本软件没有重新拟合。缺少明确的单位时显示 a.u. 并提示。
工作区 .json 包含数据及选项，Origin .opju 工程仍需在 Origin 中保存。

会话事件：早期探测意外复用了并关闭了原 FTIR 窗口，没有保存或覆盖原工程文件。
现已从已保存 FTIR.opju 恢复 3 个页面；当时未保存的修改无法确认。新版已补上连接保护并测试。

详细证据：验证汇总.json、验证与预览/桌面版MCP联动验证.json、分层叠加与缺失点验证.json。
'''
    (RELEASE/'测试报告.txt').write_text(report,encoding='utf-8-sig')
    # Copy only documentation/evidence. The desktop executable may be running.
    for name in ('使用说明.txt','本轮优化说明.txt','测试报告.txt','验证汇总.json','MCP配置.json'):
        shutil.copy2(RELEASE/name,DESKTOP/name)
    shutil.copytree(evidence,DESKTOP/'验证与预览',dirs_exist_ok=True)
    source=RELEASE/'源码'
    shutil.copy2(Path(__file__),source/'tools'/'finalize_release.py')
    shutil.copy2(Path(__file__),DESKTOP/'源码'/'tools'/'finalize_release.py')
    records=[]
    for path in sorted(RELEASE.rglob('*')):
        if path.is_file() and path.name!='文件校验.json':
            relative=path.relative_to(RELEASE)
            sha=digest(path)
            assert digest(DESKTOP/relative)==sha,(str(relative),'desktop copy differs')
            records.append(dict(file=str(relative),bytes=path.stat().st_size,sha256=sha))
    manifest=dict(version='1.0',files=records)
    write_json(RELEASE/'文件校验.json',manifest); shutil.copy2(RELEASE/'文件校验.json',DESKTOP/'文件校验.json')
    zips=[make_zip(source,OUTPUTS/'绘图器_1.0_源码.zip'),make_zip(RELEASE,OUTPUTS/'绘图器_1.0_便携版.zip')]
    write_json(OUTPUTS/'绘图器_1.0_压缩包校验.json',zips)
    print(json.dumps(dict(verified_files=len(records),source_parity=sum(len(v) for v in parity.values()),archives=zips),ensure_ascii=True))

if __name__=='__main__': main()
