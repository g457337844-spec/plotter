import json
from studio.service import Engine
from studio.models import Dataset,Curve

def workspace(label):
    engine=Engine(recovery=False)
    engine.datasets=[Dataset('sample','xrd','sample.txt',label,[0,1],[Curve('measured','Intensity',[10,20])])]
    return engine.workspace()

def test_previous_working_data_migrates_without_modifying_legacy(tmp_path,monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    legacy=tmp_path/'OriginStudio'/'recovery.json'; legacy.parent.mkdir()
    legacy.write_text(json.dumps(workspace('保留名称'),ensure_ascii=False),encoding='utf-8')
    before=legacy.read_bytes()
    engine=Engine(recovery=True)
    assert engine.datasets[0].label=='保留名称'
    assert (tmp_path/'Plotter'/'recovery.json').is_file()
    assert legacy.read_bytes()==before

def test_existing_new_workspace_takes_priority_over_legacy(tmp_path,monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    for directory,label in [('Plotter','新版数据'),('OriginStudio','旧版数据')]:
        path=tmp_path/directory/'recovery.json'; path.parent.mkdir()
        path.write_text(json.dumps(workspace(label),ensure_ascii=False),encoding='utf-8')
    engine=Engine(recovery=True)
    assert engine.datasets[0].label=='新版数据'
