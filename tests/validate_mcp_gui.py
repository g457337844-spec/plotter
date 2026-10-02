"""Exercise the packaged UI and real Origin through the public MCP interface.

Leaves the tested application and its newly created Origin graphs open for review.
Never attaches to or closes pre-existing Origin sessions.
"""
import asyncio,json,sys,subprocess,time
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from studio.service import app_data,atomic_json
from studio.bridge import remote_call
from studio.origin import origin_processes

XPS=r'E:\Desktop\小图\第二体系\表征\XPS\TC.xlsx'
XRD=r'E:\Desktop\表征\第二体系\XRD\T TC C CAG\高树良-XRD-5°-四个样品\1.txt'

def content(result):
    assert not result.isError,str(result)
    return json.loads(next(c.text for c in result.content if c.type=='text'))

async def main():
    directory=Path(sys.argv[1]).resolve(); out=Path(sys.argv[2]).resolve()
    out.mkdir(parents=True,exist_ok=True)
    before=origin_processes()
    process=subprocess.Popen([str(directory/'绘图器.exe'),'--open',XPS,XRD],cwd=directory,creationflags=subprocess.CREATE_NO_WINDOW)
    bridge=None
    for _ in range(50):
        assert process.poll() is None,'desktop application exited'
        try:
            info=json.loads((app_data()/'bridge.json').read_text(encoding='utf-8'))
            if info['pid']==process.pid and len(remote_call(info,'state',{})['datasets'])>=6: bridge=info; break
        except Exception: pass
        await asyncio.sleep(.4)
    assert bridge is not None,'desktop bridge did not start'
    report={'gui_pid':process.pid,'before_origin_pids':list(before),'started_at':time.strftime('%Y-%m-%d %H:%M:%S')}
    repeated=subprocess.Popen([str(directory/'绘图器.exe'),'--open',XPS,XRD],cwd=directory,creationflags=subprocess.CREATE_NO_WINDOW)
    assert await asyncio.to_thread(repeated.wait,15)==0,'second launch did not forward to the desktop window'
    assert process.poll() is None
    assert json.loads((app_data()/'bridge.json').read_text(encoding='utf-8'))['pid']==process.pid
    report['single_instance_repeated_import']=len(remote_call(bridge,'state',{})['datasets'])==6
    assert report['single_instance_repeated_import']
    server=StdioServerParameters(command=str(directory/'绘图器-MCP.exe'),args=[],cwd=str(directory))
    async with stdio_client(server) as (read,write):
        async with ClientSession(read,write) as client:
            report['protocol']=(await client.initialize()).model_dump(mode='json')
            report['tools']=[t.name for t in (await client.list_tools()).tools]
            state=content(await client.call_tool('get_workspace',{}))
            targets=[d for d in state['datasets'] if d['source'] in {XPS,XRD}]
            assert len(targets)==6
            o1s=next(d for d in targets if d['region']=='O1s')
            content(await client.call_tool('update_dataset',dict(dataset_id=o1s['id'],label='TC 接口联动检查')))
            assert next(d for d in remote_call(bridge,'state',{})['datasets'] if d['id']==o1s['id'])['label']=='TC 接口联动检查'
            content(await client.call_tool('update_dataset',dict(dataset_id=o1s['id'],label=o1s['label'])))
            report['gui_mcp_shared_state']=True
            content(await client.call_tool('set_plot_options',dict(options={'mode':'separate','connection':'new','x_min':None,'x_max':None,'legend':False,'peak_labels':False,'show_y_values':True})))
            ids=[d['id'] for d in targets]
            report['validation']=content(await client.call_tool('validate_plot',dict(dataset_ids=ids)))
            assert len(report['validation']['graphs'])==6
            report['plot']=content(await client.call_tool('plot_in_origin',dict(dataset_ids=ids,preview_directory=str(out/'Origin 成图'))))
            assert len(report['plot']['graphs'])==6
            assert report['plot']['origin']['owned'] and report['plot']['origin']['pid'] not in before
            assert max(b['roundtrip_max_error'] for b in report['plot']['workbooks'])==0
            report['audits']=[]
            for graph in report['plot']['graphs']:
                audit=content(await client.call_tool('audit_graph',dict(graph_name=graph['graph'])))['audit']
                for key in ('page.width','page.height','layer.left','layer.width'):
                    assert abs(audit[key]-graph['baseline'][key])<1e-6
                assert audit['yl']['show']==1 and abs(audit['yl']['normalized_y']-.5)<.002
                assert abs(audit['xb']['normalized_x']-.5)<.002
                report['audits'].append(audit)
            graph=next(g for g in report['plot']['graphs'] if o1s['id'] in g['data'])
            content(await client.call_tool('open_origin_graph',dict(graph_name=graph['graph'])))
            # Give the GUI's normal revision polling time to populate its preview menu.
            await asyncio.sleep(1)
            report['gui_capture']=content(await client.call_tool('capture_app_preview',dict(path=str(out/'界面预览.png'),graph_name=graph['graph'])))
            report['workspace']=content(await client.call_tool('save_workspace',dict(path=str(out/'示例工作区.json'))))
            report['origin_status']=content(await client.call_tool('origin_status',{}))
    report['after_origin_pids']=list(origin_processes())
    assert set(before)<=set(report['after_origin_pids']),'a pre-existing Origin process disappeared'
    report['finished_at']=time.strftime('%Y-%m-%d %H:%M:%S')
    atomic_json(out/'桌面版MCP联动验证.json',report)
    print(json.dumps({'gui_pid':process.pid,'graphs':6,'MCP_tools':len(report['tools']),'roundtrip_max_error':0,'existing_origin_preserved':True},ensure_ascii=True))

if __name__=='__main__': asyncio.run(main())
