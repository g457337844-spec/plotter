import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from studio.service import Broker,atomic_json
from studio.models import Dataset,Curve

DATA=Path(r'E:\Desktop\表征\第二体系\XRD\T TC C CAG\高树良-XRD-5°-四个样品')
XPS=r'E:\Desktop\小图\第二体系\表征\XPS\TC.xlsx'

def main():
    out=ROOT/'validation'/'stacks'; broker=Broker(recovery=False,preview_root=out); report={}
    try:
        report['import']=broker.call('import',dict(paths=[str(DATA/'1.txt'),str(DATA/'2.txt'),str(DATA/'PDF#21-1276.txt'),str(DATA/'PDF#44-1294.txt'),XPS]))
        assert not report['import']['issues'],report['import']['issues']
        broker.call('options',{'connection':'new','mode':'stack','normalize_xrd':True})
        ids=[d.id for d in broker.engine.datasets if d.kind in {'xrd','reference'}]
        report['xrd_stack']=broker.call('plot',dict(ids=ids),timeout=240)
        broker.call('options',{'mode':'overlay','legend':True})
        report['xrd_overlay']=broker.call('plot',dict(ids=ids[:2]),timeout=240)
        # A fitted XPS stack with a distinct second sample preserves all fitted curves.
        first=next(d for d in broker.engine.datasets if d.region=='O1s')
        clone=Dataset.from_dict(first.to_dict()); clone.id+='B'; clone.label='TC 对照'; clone.color='#FF375F'
        broker.engine.datasets.append(clone)
        broker.call('options',{'mode':'stack','peak_labels':False,'legend':False})
        report['xps_stack']=broker.call('plot',dict(ids=[first.id,clone.id]),timeout=240)
        # Missing values survive the complete Excel -> Origin -> readback path.
        missing=Dataset.from_dict(first.to_dict()); missing.id+='Missing'; missing.label='Missing point test'; missing.curves[2].values[30]=None
        broker.engine.datasets.append(missing)
        broker.call('options',{'mode':'separate','peak_labels':True})
        report['missing_point']=broker.call('plot',dict(ids=[missing.id]),timeout=240)
        atomic_json(ROOT/'validation'/'stack_validation.json',report)
        print(json.dumps({k:[(g['graph'],g['title'],len(g['audit'])) for g in v['graphs']] for k,v in report.items() if k!='import'},ensure_ascii=True))
    finally:
        if broker.engine.session.owned: broker.call('cleanup_test')
        broker.close()

if __name__=='__main__': main()
