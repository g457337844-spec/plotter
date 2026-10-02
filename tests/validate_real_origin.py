from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from studio.service import Broker, atomic_json

XPS=r'E:\Desktop\小图\第二体系\表征\XPS\TC.xlsx'
XRD=r'E:\Desktop\表征\第二体系\XRD\T TC C CAG\高树良-XRD-5°-四个样品\1.txt'

def main():
    out=ROOT/'validation'; out.mkdir(exist_ok=True)
    broker=Broker(recovery=False,preview_root=out/'graphs')
    report={}
    try:
        report['import']=broker.call('import',{'paths':[XPS,XRD]})
        assert not report['import']['issues']
        report['origin_before']=broker.call('origin_status')
        broker.call('options',{'connection':'new'})
        report['validate']=broker.call('validate')
        report['plot']=broker.call('plot',timeout=240)
        atomic_json(out/'real_origin.json',report)
        print(json.dumps({'graphs':[(g['title'],g['graph'],g['size_inches']) for g in report['plot']['graphs']],
                          'origin':report['plot']['origin'],'max_error':max(b['roundtrip_max_error'] for b in report['plot']['workbooks'])},ensure_ascii=True,indent=2))
    finally:
        try:
            if broker.engine.session.owned: broker.call('cleanup_test')
        finally: broker.close()

if __name__=='__main__': main()
