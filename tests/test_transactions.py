import pytest
from studio.models import Dataset,Curve,Options,DataError
from studio.planning import validate_selection
from studio.origin import render
from studio.service import Engine

class FailingOrigin:
    def __init__(self): self.destroyed=[]
    def CreatePage(self,*args): return 'OnlyNewBook'
    def PutWorksheet(self,*args): return False
    def DestroyPage(self,name): self.destroyed.append(name)

class Session:
    def __init__(self): self.app=FailingOrigin()
    def connect(self,*args): pass
    def guard(self): pass

def ds(): return Dataset('one','xrd','sample.txt','sample',[0,1],[Curve('measured','Intensity',[10,20])])

def test_failed_write_cleans_new_page():
    d=ds(); options=Options(); session=Session()
    with pytest.raises(RuntimeError): render(session,validate_selection([d],options),options,[d])
    assert session.app.destroyed==['OnlyNewBook']

def test_failed_options_do_not_change_workspace():
    engine=Engine(recovery=False)
    before=engine.options.to_dict()
    with pytest.raises(DataError): engine.handle('options',{'x_min':10,'x_max':float('inf')})
    assert engine.options.to_dict()==before

def test_invalid_selection_never_connects_origin():
    engine=Engine(recovery=False); engine.datasets=[ds()]
    with pytest.raises(DataError): engine.handle('plot',{'options':{'x_min':10,'x_max':20}})
    assert engine.session.app is None

def test_failed_workspace_load_is_atomic():
    engine=Engine(recovery=False); engine.datasets=[ds()]
    bad=engine.workspace(); bad['options']['x_max']=10
    with pytest.raises(DataError): engine.restore(bad)
    assert engine.datasets[0].id=='one' and engine.options.x_max is None

def test_reorder_preserves_values_and_checkbox_state():
    engine=Engine(recovery=False); a=ds(); b=ds(); b.id='two'; b.enabled=False
    engine.datasets=[a,b]; engine.handle('reorder',{'ids':['two','one']})
    assert [d.id for d in engine.datasets]==['two','one'] and not engine.datasets[0].enabled
    assert engine.datasets[1].measured.values==[10,20]

def test_invalid_reorder_is_atomic():
    engine=Engine(recovery=False); engine.datasets=[ds()]
    with pytest.raises(DataError): engine.handle('reorder',{'ids':['other']})
    assert engine.datasets[0].id=='one'
