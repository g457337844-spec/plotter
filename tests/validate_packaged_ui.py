import os
import subprocess,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
XPS=os.environ.get('PLOTTER_TEST_XPS', '')
XRD=os.environ.get('PLOTTER_TEST_XRD', '')
assert XPS and XRD and Path(XPS).is_file() and Path(XRD).is_file(), 'Set PLOTTER_TEST_XPS and PLOTTER_TEST_XRD'
exe=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'dist'/'Plotter'/'绘图器.exe'
image=ROOT/'validation'/'packaged_ui.png'
result=subprocess.run([str(exe),'--ui-snapshot',str(image),'--open',XPS,XRD],cwd=ROOT,capture_output=True,timeout=35,creationflags=subprocess.CREATE_NO_WINDOW)
assert result.returncode==0,result.stderr
assert image.is_file()
print(json.dumps(dict(exit_code=result.returncode,image=str(image)),ensure_ascii=True))
