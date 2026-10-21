from __future__ import annotations
import os
import asyncio, json, sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT=Path(__file__).resolve().parents[1]
XPS=os.environ.get('PLOTTER_TEST_XPS', '')
XRD=os.environ.get('PLOTTER_TEST_XRD', '')

def content(result):
    assert not result.isError, str(result)
    return json.loads(next(c.text for c in result.content if c.type=='text'))

async def main():
    executable=sys.argv[1] if len(sys.argv)>1 else sys.executable
    args=[] if Path(executable).suffix.lower()=='.exe' and Path(executable).name.lower()!='python.exe' else [str(ROOT/'mcp_entry.py')]
    args.append('--headless')
    server=StdioServerParameters(command=executable,args=args,cwd=str(ROOT))
    report={}
    async with stdio_client(server) as (read,write):
        async with ClientSession(read,write) as client:
            report['initialize']=(await client.initialize()).model_dump(mode='json')
            assert report['initialize']['serverInfo']['name']=='绘图器'
            assert report['initialize']['serverInfo']['version']=='1.0'
            report['tools']=[t.name for t in (await client.list_tools()).tools]
            assert 'plot_in_origin' in report['tools'] and 'capture_app_preview' in report['tools']
            report['import']=content(await client.call_tool('import_files',dict(paths=[XPS,XRD])))
            assert len(report['import']['imported'])==6 and not report['import']['issues']
            content(await client.call_tool('import_files',dict(paths=[XPS])))
            state=content(await client.call_tool('get_workspace',{})); assert len(state['datasets'])==6 and state['version']=='1.0'
            first=state['datasets'][0]['id']
            content(await client.call_tool('update_dataset',dict(dataset_id=first,label='TC 测试',color='#34C759')))
            report['validate']=content(await client.call_tool('validate_plot',{}))
            assert len(report['validate']['graphs'])==6
            bad=await client.call_tool('set_plot_options',dict(options={'x_min':10,'x_max':'1e999'}))
            assert bad.isError; report['invalid_range_rejected']=True
            state=content(await client.call_tool('get_workspace',{})); assert state['options']['x_min'] is None
            report['save']=content(await client.call_tool('save_workspace',dict(path=str(ROOT/'validation'/'mcp_workspace.json'))))
            content(await client.call_tool('load_workspace',dict(path=report['save']['path'])))
            state=content(await client.call_tool('get_workspace',{})); assert state['datasets'][0]['label']=='TC 测试'
    (ROOT/'validation'/'mcp_protocol.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'tools':len(report['tools']),'datasets':6,'duplicate_import':True,'invalid_range_rejected':True,'workspace_roundtrip':True}))

if __name__=='__main__': asyncio.run(main())
