import sys,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
import pythoncom
from studio.origin import OriginSession,execute,snapshot
from studio.service import atomic_json

def main():
    pythoncom.CoInitialize(); session=OriginSession(); report={}
    try:
        report['connection']=session.connect('new',False); app=session.app
        book=str(app.CreatePage(2,'ManualSource','Origin',2)); app.PutWorksheet(book,[[i,100+i*i] for i in range(12)],0,0)
        execute(app,f'plotxy iy:=[{book}]1!(1,2) plot:=200;')
        graph=str(app.LTStr('%H')); report['manual_plotxy']=snapshot(app)
        for template in ('Origin','Line',''):
            name=str(app.CreatePage(3,'DefaultProbe',template,2)); execute(app,f'win -a {name};')
            report[template or 'empty']=snapshot(app)
            app.DestroyPage(name)
        atomic_json(ROOT/'validation'/'manual_defaults.json',report)
        print(json.dumps({k:{p:v[p] for p in ('page.width','page.height','layer.left','layer.width','xb','yl')} for k,v in report.items() if k!='connection'},ensure_ascii=True,indent=2))
    finally:
        if session.owned: session.discard_private_test()
        pythoncom.CoUninitialize()

if __name__=='__main__': main()
