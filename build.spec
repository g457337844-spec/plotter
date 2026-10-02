# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules,copy_metadata
from pathlib import Path
from importlib.util import find_spec

# Qt 6.11 requires the runtime bundled with its wheel. Keep the root runtime
# consistent so the bootloader cannot pre-load an older Python runtime DLL.
qt_runtime=Path(next(iter(find_spec('shiboken6').submodule_search_locations)))
runtime_files=[p for p in qt_runtime.glob('*.dll') if p.name.lower().startswith(('vcruntime140','msvcp140','concrt140'))]
def align_runtime(analysis):
    names={p.name.lower() for p in runtime_files}
    # Qt uses Windows' non-versioned ICU API. A Poppler ICU on the build host
    # exports different symbols and must never shadow the Windows system DLL.
    analysis.binaries=[item for item in analysis.binaries if item[0].lower() not in names
                       and 'poppler' not in str(item[1]).lower()]
    analysis.binaries.extend((p.name,str(p),'BINARY') for p in runtime_files)

shared=dict(pathex=[],binaries=[],datas=[('assets','assets')]+copy_metadata('mcp'),
    hiddenimports=['studio.gui','studio.mcp_server','studio.origin','win32timezone','PySide6.QtSvg']+collect_submodules('mcp',filter=lambda name:not name.startswith('mcp.cli')),
    hookspath=[],hooksconfig={},runtime_hooks=[],
    excludes=['PyQt5','PyQt6','PySide2','tkinter','matplotlib','numpy','pandas','scipy','IPython','jupyter','pytest'],noarchive=False)

a=Analysis(['main.py'],**shared)
align_runtime(a)
pyz=PYZ(a.pure)
gui=EXE(pyz,a.scripts,[],exclude_binaries=True,name='绘图器',debug=False,bootloader_ignore_signals=False,
        strip=False,upx=False,console=False,icon='assets/mark.ico',version='version_info.txt')
b=Analysis(['mcp_entry.py'],**shared)
align_runtime(b)
pyz2=PYZ(b.pure)
mcp=EXE(pyz2,b.scripts,[],exclude_binaries=True,name='绘图器-MCP',debug=False,bootloader_ignore_signals=False,
        strip=False,upx=False,console=True,icon='assets/mark.ico',version='mcp_version_info.txt')
coll=COLLECT(gui,mcp,a.binaries,a.datas,b.binaries,b.datas,strip=False,upx=False,name='Plotter')
