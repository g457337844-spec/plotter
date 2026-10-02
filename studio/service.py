from __future__ import annotations
import json, os, queue, threading, time, traceback
from concurrent.futures import Future
from pathlib import Path
from . import __version__
from .models import Dataset, Options, DataError, PALETTE, color
from .parsers import import_path, parse_xps_rows
from .planning import validate_selection
from .origin import OriginSession, render, execute, snapshot

def app_data():
    root=Path(os.environ.get('LOCALAPPDATA',str(Path.cwd()))) / 'Plotter'
    root.mkdir(parents=True,exist_ok=True); return root

def atomic_json(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    temporary.replace(path)

class Engine:
    def __init__(self, recovery=True, preview_root=None):
        self.datasets=[]; self.options=Options(); self.history=[]; self.notices=[]
        self.version=0; self.session=OriginSession(); self.progress=''; self.ui=None
        self.recovery=recovery; self.preview_root=Path(preview_root or app_data()/'previews')
        self.workspace_path=app_data()/'recovery.json'
        legacy=app_data().parent/'OriginStudio'/'recovery.json'
        if recovery and not self.workspace_path.exists() and legacy.is_file():
            try:
                self.restore(json.loads(legacy.read_text(encoding='utf-8')))
                atomic_json(self.workspace_path,self.workspace())
            except Exception as exc: self.notices.append(f'原工作区无法迁移：{exc}')
        if recovery and self.workspace_path.is_file():
            try: self.restore(json.loads(self.workspace_path.read_text(encoding='utf-8')))
            except Exception as exc: self.notices.append(f'上次的工作区无法恢复：{exc}')

    def workspace(self):
        return dict(format='origin-studio-workspace',format_version=1,
                    datasets=[d.to_dict() for d in self.datasets],options=self.options.to_dict())

    def restore(self,value):
        if value.get('format')!='origin-studio-workspace' or value.get('format_version')!=1:
            raise DataError('这不是受支持的绘图器工作区')
        datasets=[Dataset.from_dict(d) for d in value['datasets']]
        if len({d.id for d in datasets})!=len(datasets): raise DataError('工作区中有重复数据标识')
        options=Options.from_dict(value.get('options'))
        self.datasets,self.options=datasets,options

    def changed(self):
        self.version+=1
        if self.recovery: atomic_json(self.workspace_path,self.workspace())

    def state(self,full=False):
        return dict(version=__version__,revision=self.version,options=self.options.to_dict(),
                    datasets=[d.to_dict() if full else d.summary() for d in self.datasets],
                    history=self.history,notices=self.notices,progress=self.progress,
                    origin=dict(connected=self.session.app is not None,pid=self.session.pid,
                                project=self.session.identity[0] if self.session.identity else '',
                                mode=self.session.mode))

    def handle(self,command,args=None):
        args=args or {}
        if command=='state': return self.state(bool(args.get('full',False)))
        if command=='import':
            paths=args.get('paths',[])
            if not paths: raise DataError('请提供至少一个文件路径')
            results=[]; issues=[]; notices=[]
            for path in paths:
                try:
                    items,info,errors=import_path(path,args.get('mapping'))
                    for ds in items:
                        old=next((d for d in self.datasets if d.id==ds.id),None)
                        if old:
                            ds.color,ds.label,ds.enabled=old.color,old.label,old.enabled
                            self.datasets[self.datasets.index(old)]=ds
                        else:
                            same=next((d for d in self.datasets if d.source==ds.source),None)
                            ds.color=same.color if same else PALETTE[len({d.source for d in self.datasets})%len(PALETTE)]
                            self.datasets.append(ds)
                        results.append(ds.summary())
                    notices.extend(info); issues.extend(errors)
                except DataError as exc:
                    issues.append(dict(path=str(path),message=str(exc),code=exc.code,details=exc.details))
            self.notices=notices+[e['message'] for e in issues]; self.changed()
            return dict(imported=results,notices=notices,issues=issues)
        if command=='excel_live':
            import win32com.client
            try: app=win32com.client.GetActiveObject('Excel.Application'); wb=app.ActiveWorkbook
            except Exception: raise DataError('未找到已打开的 Excel 工作簿，请先在 Excel 打开数据文件') from None
            if wb is None: raise DataError('Excel 没有活动工作簿')
            source=Path(str(wb.FullName))
            datasets=[]; issues=[]
            for ws in wb.Worksheets:
                matrix=ws.UsedRange.Value
                if not isinstance(matrix,tuple): continue
                try: ds=parse_xps_rows(matrix,path=source,sheet=str(ws.Name))
                except DataError as exc:
                    issues.append(dict(path=str(source),message=str(exc),code=exc.code,details=exc.details)); continue
                if ds:
                    ds.metadata['live_excel_snapshot']=True
                    old=next((d for d in self.datasets if d.id==ds.id),None)
                    if old:
                        ds.color,ds.label,ds.enabled=old.color,old.label,old.enabled
                        self.datasets.remove(old)
                    else:
                        same=next((d for d in self.datasets if d.source==ds.source),None)
                        ds.color=same.color if same else PALETTE[len({d.source for d in self.datasets})%len(PALETTE)]
                    self.datasets.append(ds); datasets.append(ds.summary())
            if not datasets and not issues: raise DataError('活动工作簿中没有 XPS 数据')
            self.changed(); return dict(imported=datasets,issues=issues,notices=['导入的是当前 Excel 数据快照；绘图不会修改工作簿'])
        if command=='update':
            ds=next((d for d in self.datasets if d.id==args.get('id')),None)
            if ds is None: raise DataError('没有找到这份数据')
            patch=args.get('changes',{})
            if set(patch)-{'label','color','enabled'}: raise DataError('只能修改样品名称、颜色和勾选状态')
            label=patch.get('label',ds.label)
            if not isinstance(label,str) or not label.strip() or len(label)>160: raise DataError('名称应为 1–160 个字符')
            newcolor=color(patch.get('color',ds.color)); enabled=patch.get('enabled',ds.enabled)
            if type(enabled) is not bool: raise DataError('勾选状态必须是布尔值')
            ds.label,ds.color,ds.enabled=label.strip(),newcolor,enabled
            self.changed(); return ds.summary()
        if command=='remove':
            ids=set(args.get('ids',[])); self.datasets=[d for d in self.datasets if d.id not in ids]
            self.changed(); return self.state()
        if command=='reorder':
            ids=args.get('ids',[])
            if len(ids)!=len(self.datasets) or len(set(ids))!=len(ids) or set(ids)!={d.id for d in self.datasets}:
                raise DataError('排序需要恰好包含工作区中的全部数据')
            by_id={d.id:d for d in self.datasets}; self.datasets=[by_id[i] for i in ids]
            self.changed(); return self.state()
        if command=='clear':
            self.datasets=[]; self.notices=[]; self.changed(); return self.state()
        if command=='options':
            merged=self.options.to_dict(); merged.update(args)
            self.options=Options.from_dict(merged); self.changed(); return self.options.to_dict()
        if command=='validate':
            options=Options.from_dict({**self.options.to_dict(),**args.get('options',{})})
            selected=self.selection(args.get('ids'))
            plans=validate_selection(selected,options)
            notes=[]
            if options.mode=='overlay' and any(d.kind=='xps' and any(c.role=='peak' for c in d.curves) for d in selected):
                notes.append('XPS 叠加对比只画实测曲线；分峰数据保留在工作区和原始文件中')
            if options.mode=='stack': notes.append('分层绘图保持默认页宽和绘图区总范围，按数据层数分配高度')
            return dict(valid=True,graphs=[p.summary() for p in plans],notes=notes)
        if command=='plot':
            options=Options.from_dict({**self.options.to_dict(),**args.get('options',{})})
            selected=self.selection(args.get('ids')); plans=validate_selection(selected,options)
            self.progress='正在连接 Origin'
            try:
                result=render(self.session,plans,options,selected,args.get('preview_dir',str(self.preview_root)),self.set_progress)
                result['created_at']=time.strftime('%Y-%m-%d %H:%M:%S')
                self.history.append(result); self.version+=1
                return result
            finally: self.progress=''
        if command=='origin_status':
            if args.get('connect'):
                result=self.session.connect(args.get('mode',self.options.connection)); self.version+=1
                return result
            return self.session.status()
        if command=='origin_disconnect':
            self.session.release(); self.version+=1; return dict(connected=False)
        if command=='audit':
            self.session.guard()
            graph=args.get('graph')
            known={g['graph'] for h in self.history for g in h['graphs']}
            if graph not in known: raise DataError('只能核验本工作区创建的图页')
            execute(self.session.app,f'win -a {graph}; layer -s 1;')
            return dict(graph=graph,audit=snapshot(self.session.app))
        if command=='activate_graph':
            self.session.guard(); graph=args.get('graph')
            if graph not in {g['graph'] for h in self.history for g in h['graphs']}: raise DataError('图页不存在于当前记录')
            execute(self.session.app,f'win -a {graph};'); self.session.app.Visible=1
            return dict(graph=graph,activated=True)
        if command=='save':
            path=Path(args['path']).resolve()
            if path.suffix.casefold()!='.json': raise DataError('工作区文件扩展名应为 .json')
            atomic_json(path,self.workspace()); return dict(path=str(path))
        if command=='load':
            path=Path(args['path']).resolve()
            if path.stat().st_size>30*1024*1024: raise DataError('工作区文件过大')
            self.restore(json.loads(path.read_text(encoding='utf-8'))); self.changed(); return self.state()
        if command=='ui_snapshot':
            if self.ui is None: raise DataError('桌面窗口未运行，请打开绘图器后截图')
            return self.ui('snapshot',args)
        if command=='ui_focus':
            if self.ui is None: raise DataError('桌面窗口未运行')
            return self.ui('focus',args)
        if command=='cleanup_test':
            self.session.discard_private_test(); return dict(cleaned=True)
        raise DataError(f'不支持的操作：{command}')

    def set_progress(self,value): self.progress=value

    def selection(self,ids):
        if ids is None: return [d for d in self.datasets if d.enabled]
        if len(ids)!=len(set(ids)): raise DataError('数据选择含有重复项')
        found=[d for d in self.datasets if d.id in ids]
        if len(found)!=len(ids): raise DataError('选择中包含不存在的数据')
        # An explicit selection overrides GUI checkbox state for this invocation.
        return [Dataset.from_dict({**d.to_dict(),'enabled':True}) for d in found]

class Broker:
    def __init__(self,recovery=True,preview_root=None):
        self.jobs=queue.Queue(); self.engine=None; self.ready=threading.Event(); self.closed=False
        self.thread=threading.Thread(target=self.run,args=(recovery,preview_root),daemon=True,name='OriginStudio-Service')
        self.thread.start(); self.ready.wait(10)

    def run(self,recovery,preview_root):
        import pythoncom
        pythoncom.CoInitialize()
        try:
            self.engine=Engine(recovery,preview_root); self.ready.set()
            while True:
                job=self.jobs.get()
                if job is None: break
                command,args,future=job
                if not future.set_running_or_notify_cancel(): continue
                try: future.set_result(self.engine.handle(command,args))
                except BaseException as exc:
                    try:
                        atomic_json(app_data()/'last_error.json',dict(command=command,error=str(exc),script=getattr(exc,'origin_script',None),traceback=traceback.format_exc()))
                    except Exception: pass
                    future.set_exception(exc)
            self.engine.session.release()
        finally: pythoncom.CoUninitialize()

    def submit(self,command,args=None):
        if self.closed: raise DataError('绘图服务已经关闭')
        if self.engine is None: raise DataError('绘图服务尚未启动')
        future=Future(); self.jobs.put((command,args or {},future)); return future

    def call(self,command,args=None,timeout=180): return self.submit(command,args).result(timeout)

    def close(self):
        if self.closed: return
        self.closed=True; self.jobs.put(None); self.thread.join(3)
