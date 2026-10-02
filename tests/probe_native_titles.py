import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from studio.service import Broker,atomic_json
from studio.origin import execute,snapshot

DATA=Path(r'E:\Desktop\表征\第二体系\XRD\T TC C CAG\高树良-XRD-5°-四个样品')

def main():
    out=ROOT/'validation'/'title_probe'; broker=Broker(recovery=False,preview_root=out); report={}
    try:
        broker.call('import',dict(paths=[str(DATA/'1.txt'),str(DATA/'2.txt')]))
        broker.call('options',{'connection':'new','mode':'overlay','normalize_xrd':True})
        report['before']=broker.call('plot',timeout=240)
        def probe(command):
            app=broker.engine.session.app
            if command=='reset':
                execute(app,'label -yl "Normalized intensity (%)"; label -xb "2θ (°)";')
                info=snapshot(app)
                execute(app,f'expGraph type:=png path:="{out}" filename:="reset" overwrite:=1 tr1.width:=1600 tr1.unit:=2;')
                return info
            raise ValueError(command)
        # Run COM inspection on the same apartment thread as the service.
        original=broker.engine.handle
        broker.engine.handle=lambda command,args=None:probe(args['probe']) if command=='probe' else original(command,args)
        report['reset']=broker.call('probe',{'probe':'reset'})
        atomic_json(out/'report.json',report)
        print(json.dumps({'before':report['before']['graphs'][0]['audit'][0]['yl'],'reset':report['reset']['yl']},ensure_ascii=True))
    finally:
        if broker.engine.session.owned: broker.call('cleanup_test')
        broker.close()

if __name__=='__main__': main()
