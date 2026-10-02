import subprocess,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
XPS=r'E:\Desktop\小图\第二体系\表征\XPS\TC.xlsx'
XRD=r'E:\Desktop\表征\第二体系\XRD\T TC C CAG\高树良-XRD-5°-四个样品\1.txt'
exe=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'dist'/'Plotter'/'绘图器.exe'
image=ROOT/'validation'/'packaged_ui.png'
result=subprocess.run([str(exe),'--ui-snapshot',str(image),'--open',XPS,XRD],cwd=ROOT,capture_output=True,timeout=35,creationflags=subprocess.CREATE_NO_WINDOW)
assert result.returncode==0,result.stderr
assert image.is_file()
print(json.dumps(dict(exit_code=result.returncode,image=str(image)),ensure_ascii=True))
