from pathlib import Path
import pefile,sys,os
root=Path(__file__).resolve().parents[1]/'dist'/'Plotter'/'_internal'
folders=[root,root/'PySide6',root/'shiboken6',Path(sys.base_prefix),Path(os.environ['WINDIR'])/'System32']
def resolve(name):
    for p in folders:
        f=p/name
        if f.is_file(): return f
def check(f):
    pe=pefile.PE(str(f)); missing=[]
    for imp in pe.DIRECTORY_ENTRY_IMPORT:
        dep=resolve(imp.dll.decode())
        if not dep: continue
        dp=pefile.PE(str(dep)); exports={e.name for e in getattr(dp,'DIRECTORY_ENTRY_EXPORT',type('X',(),{'symbols':[]})()).symbols}
        for name in imp.imports:
            if name.name and name.name not in exports: missing.append((imp.dll.decode(),name.name.decode()))
    print(f.name,missing)
for name in ['PySide6/QtCore.pyd','PySide6/Qt6Core.dll','PySide6/pyside6.abi3.dll','shiboken6/shiboken6.abi3.dll']:
    check(root/name)
