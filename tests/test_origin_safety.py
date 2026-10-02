import pytest
from types import SimpleNamespace
from studio.models import DataError
from studio.origin import OriginSession
import studio.origin as origin
import win32com.client

class ExistingProject:
    Pages=SimpleNamespace(Count=3)
    def __init__(self): self.resets=0
    def LTStr(self,name): return 'FTIR'
    def NewProject(self): self.resets+=1; return True

def test_reused_process_is_never_reset(monkeypatch):
    app=ExistingProject()
    monkeypatch.setattr(origin,'origin_processes',lambda:{101:'Origin64.exe'})
    monkeypatch.setattr(win32com.client,'DispatchEx',lambda *a:app)
    with pytest.raises(DataError): OriginSession().connect('new')
    assert app.resets==0

def test_nonempty_returned_session_is_never_reset(monkeypatch):
    app=ExistingProject(); states=iter([{101:'Origin64.exe'},{101:'Origin64.exe',202:'Origin64.exe'}])
    monkeypatch.setattr(origin,'origin_processes',lambda:next(states))
    monkeypatch.setattr(win32com.client,'DispatchEx',lambda *a:app)
    with pytest.raises(DataError): OriginSession().connect('new')
    assert app.resets==0

def test_ambiguous_existing_session_never_attaches(monkeypatch):
    monkeypatch.setattr(origin,'origin_processes',lambda:{101:'Origin64.exe',202:'Origin64.exe'})
    monkeypatch.setattr(win32com.client,'Dispatch',lambda *a:pytest.fail('must not attach'))
    with pytest.raises(DataError): OriginSession().connect('existing')
