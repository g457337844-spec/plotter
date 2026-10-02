"""Rename release documentation and helper paths for the 1.0 product."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
for relative in ('README.txt','tools/prepare_release.py','tools/finalize_release.py','tests/probe_dlls.py'):
    path=root/relative
    text=path.read_text(encoding='utf-8-sig')
    for old,new in [('图谱工作台_3.0.0','绘图器_1.0'),('图谱工作台','绘图器'),('OriginStudio-MCP','绘图器-MCP'),
                    ('Origin Studio','Plotter'),('3.0.0','1.0'),("'OriginStudio'","'Plotter'"),
                    ('dist/OriginStudio','dist/Plotter'),('%LOCALAPPDATA%\\OriginStudio','%LOCALAPPDATA%\\Plotter'),
                    ("'origin-studio':","'plotter':")]:
        text=text.replace(old,new)
    path.write_text(text,encoding='utf-8')
