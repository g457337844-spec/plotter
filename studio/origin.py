from __future__ import annotations
import gc, math, uuid, os
from pathlib import Path
from .models import DataError, Options, Dataset, PALETTE
from .planning import GraphPlan, display_values, axis_titles

def origin_processes():
    import win32api, win32process, win32con
    result={}
    for pid in win32process.EnumProcesses():
        if not pid: continue
        handle=None
        try:
            handle=win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION|win32con.PROCESS_VM_READ,False,pid)
            executable=win32process.GetModuleFileNameEx(handle,0)
            if Path(executable).name.casefold() in {'origin64.exe','origin.exe'}: result[pid]=executable
        except Exception: pass
        finally:
            if handle: win32api.CloseHandle(handle)
    return result

def quote(value):
    return str(value).replace('"',"'").replace('\r',' ').replace('\n',' ')

def formula_markup(value):
    value=quote(value)
    value=re_sub(r'_\{([^{}]+)\}',r'\\-(\1)',value)
    return re_sub(r'\^\{([^{}]+)\}',r'\\+(\1)',value)

def re_sub(pattern,replacement,value):
    import re
    return re.sub(pattern,replacement,value)

class OriginSession:
    """COM objects live on one service thread. Existing sessions are never exited."""
    def __init__(self):
        self.app=None; self.pid=None; self.owned=False; self.identity=None; self.mode=None

    def connect(self, mode='existing', visible=True):
        import win32com.client
        if self.app is not None:
            if mode!=self.mode: self.release()
            else:
                self.guard()
                return self.status()
        before=origin_processes()
        if mode=='existing':
            if len(before)!=1:
                raise DataError('请只保留一个 Origin 窗口后连接；也可以选择“新建独立窗口”。' if before else '请先打开 Origin，或选择“新建独立窗口”。','origin_target')
            app=win32com.client.Dispatch('Origin.ApplicationSI')
            if set(origin_processes())!=set(before):
                app=None; gc.collect(); raise DataError('Origin 窗口发生变化，已停止连接，请重新选择目标','origin_target')
            pid=next(iter(before)); owned=False
        else:
            app=win32com.client.DispatchEx('Origin.Application')
            # COM registration can behave differently between Origin installations.
            # A new PID must be observed before any project mutation is allowed.
            added=set(origin_processes())-set(before)
            if len(added)!=1:
                app=None; gc.collect()
                raise DataError('Origin 没有创建可确认的独立进程，已停止。请打开 Origin 并使用“当前窗口”。','origin_target')
            pid=added.pop(); owned=True
            if int(app.Pages.Count)!=0 or str(app.LTStr('%G')).casefold()!='untitled':
                app=None; gc.collect()
                raise DataError('独立连接返回了含工程内容的会话，已停止；没有重置或关闭该工程。','origin_target')
        self.app,self.pid,self.owned,self.mode=app,pid,owned,mode
        if owned:
            # Only a positively identified new process may get a fresh project.
            if not app.NewProject():
                self.release(); raise DataError('无法创建独立测试工程')
        if visible: app.Visible=1
        app.CanClose=True
        self.identity=self.project_identity()
        return self.status()

    def project_identity(self):
        return (str(self.app.LTStr('%G')),str(self.app.LTStr('%X')))

    def guard(self):
        if self.app is None: raise DataError('尚未连接 Origin')
        if self.pid not in origin_processes():
            self.release(); raise DataError('Origin 窗口已经关闭，请重新连接','origin_target')
        if self.project_identity()!=self.identity:
            self.release(); raise DataError('Origin 当前工程已切换，请重新连接后绘图','origin_target')
        if self.mode=='existing' and len(origin_processes())!=1:
            raise DataError('检测到多个 Origin 窗口，请只保留目标窗口后继续','origin_target')

    def status(self):
        if self.app is None: return dict(connected=False,instances=list(origin_processes()))
        return dict(connected=True,pid=self.pid,owned=self.owned,mode=self.mode,
                    version=float(self.app.Evaluate('@V')),project=str(self.app.LTStr('%G')),page_count=int(self.app.Pages.Count))

    def release(self):
        self.app=None; self.pid=None; self.identity=None; self.owned=False; self.mode=None; gc.collect()

    def discard_private_test(self):
        if not self.owned or self.app is None: raise DataError('只能清理本次创建的独立测试进程')
        self.guard()
        self.app.IsModified=False; self.app.Exit(); self.release()

GEOMETRY=('page.width','page.height','page.resx','page.resy','layer.unit','layer.left','layer.top','layer.width','layer.height')

def execute(app, script, context=None):
    if os.environ.get('ORIGIN_STUDIO_TRACE_SCRIPTS')=='1' and '\n' in script:
        for line in script.splitlines():
            if line.strip(): execute(app,line,context)
        return
    # COM's temporary context is restored after Execute. Activate the page
    # explicitly so subsequent Evaluate/LTStr reads inspect the selected layer.
    if context and not app.Execute(f'win -a {context};'):
        raise RuntimeError('无法激活本次创建的 Origin 图页')
    result=app.Execute(script)
    if not result:
        error=RuntimeError('Origin 未能执行绘图操作')
        error.origin_script=script
        raise error

def snapshot(app):
    result={key:float(app.Evaluate(key)) for key in GEOMETRY}
    x0,x1,y0,y1=[float(app.Evaluate('layer.'+s)) for s in ('x.from','x.to','y.from','y.to')]
    for obj in ('xb','yl'):
        result[obj]=dict(text=str(app.LTStr(f'{obj}.text$')),
                         size=float(app.Evaluate(f'{obj}.fsize')),
                         attach=float(app.Evaluate(f'{obj}.attach')),
                         show=float(app.Evaluate(f'{obj}.show')),
                         font=float(app.Evaluate(f'{obj}.font')),
                         normalized_x=(float(app.Evaluate(f'{obj}.x'))-x0)/(x1-x0),
                         normalized_y=(float(app.Evaluate(f'{obj}.y'))-y0)/(y1-y0))
    result['ticks']={a:float(app.Evaluate(f'layer.{a}.label.pt')) for a in ('x','y')}
    result['element_scale']=float(app.Evaluate('layer.factor'))
    result['fixed_scaling']=float(app.Evaluate('layer.fixed'))
    result['y_label_format']=int(app.Evaluate('layer.y.label.numFormat'))
    result['y_decimals']=int(app.Evaluate('layer.y.decPlaces'))
    result['legend']=str(app.LTStr('legend.text$'))
    result['x_range']=[x0,x1]; result['y_range']=[y0,y1]
    return result

def tick_width(app, graph, texts, size):
    """Measure with Origin's own font renderer; remove the temporary ruler."""
    widths=[]
    for value in texts:
        execute(app,f'label -n GSTickMeasure "{quote(value)}"; GSTickMeasure.font=layer.y.label.font; GSTickMeasure.fsize={size:g}; GSTickMeasure.show=0;',graph)
        widths.append(abs(float(app.Evaluate('GSTickMeasure.dx')))/(float(app.Evaluate('layer.x.to'))-float(app.Evaluate('layer.x.from'))))
    execute(app,'label -r GSTickMeasure;',graph)
    return max(widths,default=0)

def tick_texts(audit):
    start,end=audit['y_range']; decimals=max(0,min(audit['y_decimals'],8))
    values=[start,end,0,(start+end)/2]
    mode=audit['y_label_format']
    if mode==2: return [f'{v:.{decimals}e}' for v in values]
    if mode==4: return [f'{v:,.{decimals}f}' for v in values]
    return [f'{v:.{decimals}f}' for v in values]

def make_workbook(app, ds: Dataset, options: Options, created: list):
    name=str(app.CreatePage(2,'SD'+uuid.uuid4().hex[:9],'Origin',2))
    if not name: raise RuntimeError('Origin 无法创建数据工作簿')
    created.append(name)
    curves=list(ds.curves)
    if ds.kind=='xrd' and options.normalize_xrd:
        from .models import Curve
        curves.append(Curve('display','Normalized intensity',display_values(ds,options),0,'%'))
    if ds.kind=='reference':
        # Keep sticks as editable native line data; missing rows separate the peaks.
        rows=[]
        for x,v in zip(ds.x,curves[0].values): rows.extend([[x,0.0],[x,v],[float('nan'),float('nan')]])
    else:
        rows=[[x]+[float('nan') if c.values[i] is None else c.values[i] for c in curves] for i,x in enumerate(ds.x)]
    if not app.PutWorksheet(name,rows,0,0): raise RuntimeError(f'写入 {ds.label} 失败')
    ws=app.FindWorksheet(name)
    if ws is None: raise RuntimeError('无法定位新建的工作簿')
    ws.LongName=f'{ds.label} · {ds.sheet or "XRD"}'
    col=ws.Columns.Item(0); col.Type=3
    col.LongName='Binding Energy' if ds.kind=='xps' else '2 Theta'; col.Units=ds.x_unit
    col.Comments=ds.source
    for i,c in enumerate(curves,1):
        col=ws.Columns.Item(i); col.Type=0; col.LongName=c.label; col.Units=c.unit
        col.Comments=f'{ds.source}; sheet={ds.sheet}; source column={c.source_column}; role={c.role}'
    received=app.GetWorksheet(name,0,0,len(rows)-1,len(rows[0])-1)
    if len(received)!=len(rows) or any(len(r)!=len(rows[0]) for r in received):
        raise RuntimeError('Origin 数据回读行列数量不一致')
    max_error=0.0
    for want,got in zip(rows,received):
        for a,b in zip(want,got):
            if math.isnan(a):
                if b is not None and math.isfinite(float(b)) and float(b)>-1e-250: raise RuntimeError('Origin 未能保留缺失点')
            else:
                if b is None: raise RuntimeError('Origin 回读数据缺失')
                err=abs(a-float(b)); max_error=max(max_error,err)
                if err>max(abs(a)*1e-10,1e-8): raise RuntimeError('Origin 回读数据与原始数据不一致')
    return dict(page=name,sheet=str(ws.Name),curves=curves,roundtrip_max_error=max_error)

def add_curve(app, graph, layer, book, column, hex_color, plot=200):
    execute(app,f'plotxy iy:=[{book["page"]}]{book["sheet"]}!(1,{column}) plot:={plot} color:=color("{hex_color}") legend:=0 ogl:=[{graph}]{layer}!;')
    target=app.FindGraphLayer(f'[{graph}]{layer}')
    return int(target.DataPlots.Count)

def plot_style(app,graph,layer,index,hex_color,width=1.5,hidden=False,symbol=False):
    cmds=[f'layer -s {layer};',f'layer.plot{index}.color=color("{hex_color}");',f'range __gsplot=!{index}; set __gsplot -lm 0;']
    if symbol:
        cmds.extend([f'layer.plot{index}.symbol.size=3;',f'layer.plot{index}.symbol.kind=2;'])
    else:
        cmds.extend([f'layer.plot{index}.line.width={width:g};',f'layer.plot{index}.line.type={0 if hidden else 1};'])
    execute(app,'\n'.join(cmds),graph)

def draw_dataset(app,graph,layer,ds,book,options,comparison=False):
    curves=book['curves']; report=[]
    if ds.kind=='reference':
        i=add_curve(app,graph,layer,book,2,ds.color,200)
        plot_style(app,graph,layer,i,ds.color,options.line_width)
        return [dict(role='sticks',index=i,color=ds.color)]
    if ds.kind=='xrd' or comparison:
        col=len(curves)+1 if ds.kind=='xrd' and options.normalize_xrd else next(i+2 for i,c in enumerate(curves) if c.role=='measured')
        i=add_curve(app,graph,layer,book,col,ds.color)
        plot_style(app,graph,layer,i,ds.color,options.line_width)
        return [dict(role='measured',index=i,color=ds.color)]
    peaks=[(i+2,c) for i,c in enumerate(curves) if c.role=='peak']
    peaks.sort(key=lambda pair:ds.x[max(range(len(ds.x)),key=lambda k:pair[1].values[k] if pair[1].values[k] is not None else -math.inf)],reverse=True)
    background=next((i+2 for i,c in enumerate(curves) if c.role=='background'),None)
    for k,(col,c) in enumerate(peaks):
        hex_color=PALETTE[k%len(PALETTE)]
        i=add_curve(app,graph,layer,book,col,hex_color)
        plot_style(app,graph,layer,i,hex_color,options.line_width)
        if options.peak_fill and background:
            boundary=add_curve(app,graph,layer,book,background,hex_color)
            plot_style(app,graph,layer,boundary,hex_color,0,hidden=True)
            execute(app,f'layer -s {layer}; range __gsfill=!{i}; set __gsfill -pf 1; set __gsfill -pfv 8; set __gsfill -pfn 1; set __gsfill -pfb color("{hex_color}"); set __gsfill -pfm 3; set __gsfill -pff color("#FFFFFF");',graph)
        report.append(dict(role='peak',index=i,color=hex_color,column=col,label=c.label))
    for role,hex_color in (('background','#8E8E93'),('envelope','#FF375F'),('measured',ds.color)):
        for col,c in enumerate(curves,2):
            if c.role!=role: continue
            symbol=role=='measured' and bool(peaks)
            i=add_curve(app,graph,layer,book,col,hex_color,201 if symbol else 200)
            plot_style(app,graph,layer,i,hex_color,options.line_width,symbol=symbol)
            report.append(dict(role=role,index=i,color=hex_color,column=col,label=c.label))
    return report

def arrange(app, graph, panels, baseline):
    if len(panels)==1: return
    # Layer 1 keeps the default frame and owns the shared native axis titles.
    # Child plot layers only divide the original rectangle vertically.
    for _ in range(len(panels)): execute(app,f'layadd igp:={graph} type:=normal activate:=1;')
    weights=[.4 if p[0].kind=='reference' else 1 for p in panels]
    top=baseline['layer.top']; height=baseline['layer.height']; total=sum(weights)
    # A real gap keeps default-size tick labels from touching the next panel.
    # The first and last frame edges still match the native template exactly.
    gap=height*.045
    available=height-gap*(len(panels)-1)
    for i,w in enumerate(weights,2):
        h=available*w/total
        execute(app,f'layer -s {i}; layer.fixed=1; layer.factor={baseline["element_scale"]:g}; layer.unit={baseline["layer.unit"]:g}; layer.left={baseline["layer.left"]:g}; layer.width={baseline["layer.width"]:g}; layer.top={top:g}; layer.height={h:g};',graph)
        top+=h+gap

def render_graph(app,plan:GraphPlan,options:Options,books,created,preview_dir):
    name=str(app.CreatePage(3,'SG'+uuid.uuid4().hex[:9],options.template,2))
    if not name: raise RuntimeError(f'无法使用模板 {options.template} 创建图页')
    created.append(name); execute(app,f'win -a {name};')
    execute(app,f'page.longname$="{quote(plan.title)}";',name)
    baseline=snapshot(app)
    baseline_tick_width=tick_width(app,name,tick_texts(baseline),baseline['ticks']['y'])
    arrange(app,name,plan.panels,baseline)
    all_curves=[]; audits=[]; legends=[]
    multi=len(plan.panels)>1
    if multi:
        first=plan.panels[0][0]; firstbook=books[first.id]
        col=len(firstbook['curves'])+1 if first.kind=='xrd' and options.normalize_xrd else next(j+2 for j,c in enumerate(firstbook['curves']) if c.role=='measured')
        index=add_curve(app,name,1,firstbook,col,first.color)
        x_title,y_title=axis_titles(first,options); low,high=plan.x_range
        execute(app,f'layer -s 1; rescale; layer.showData=0; layer.x.from={low:.15g}; layer.x.to={high:.15g}; layer.x.reverse={int(options.reverse_xps and plan.kind=="xps")}; layer.x.rescale=1; layer.y.rescale=1; layer.y.showLabels=0; layer.y.ticks=0; xb.text$="{quote(x_title)}"; yl.text$="{quote(y_title)}"; label -r legend;',name)
        audits.append(snapshot(app))
    for panel_index,panel in enumerate(plan.panels,1):
        i=panel_index+1 if multi else panel_index
        comparison=len(panel)>1
        reports=[]
        for ds in panel: reports.extend(draw_dataset(app,name,i,ds,books[ds.id],options,comparison))
        execute(app,f'layer -s {i}; rescale;',name)
        low,high=plan.x_range
        x_title,y_title=axis_titles(panel[0],options)
        cmds=[f'layer -s {i};',f'layer.x.from={low:.15g};',f'layer.x.to={high:.15g};',
              f'layer.x.reverse={int(options.reverse_xps and plan.kind=="xps")};',
              'layer.x.rescale=1;', 'layer.y.rescale=1;',
              f'xb.text$="{quote(x_title)}";',f'yl.text$="{quote(y_title)}";',
              f'layer.y.showLabels={int(options.show_y_values)};']
        # Native titles keep their template anchor, font and automatic positioning.
        if multi: cmds.extend(['xb.show=0;','layer.x.showLabels=0;'])
        else: cmds.append('xb.show=1;')
        cmds.append('yl.show=0;' if multi or panel[0].kind=='reference' else 'yl.show=1;')
        if panel[0].kind=='reference':
            top=max(v for v in panel[0].curves[0].values if v is not None)
            cmds.extend(['layer.y.from=0;',f'layer.y.to={max(top*1.1,1):.15g};','layer.y.showLabels=0;'])
        if options.legend or comparison or len(plan.panels)>1:
            if comparison:
                legend='\\n'.join(f'\\l({reports[k]["index"]}) {formula_markup(d.label)}' for k,d in enumerate(panel))
            elif len(plan.panels)>1 or panel[0].kind=='reference':
                measured=next((p['index'] for p in reports if p['role'] in {'measured','sticks'}),reports[-1]['index'])
                legend=f'\\l({measured}) {formula_markup(panel[0].label)}'
            else:
                names={'background':'Background','envelope':'Fit envelope','measured':'Measured'}; peaknum=0; entries=[]
                for plot in reports:
                    if plot['role']=='peak': peaknum+=1; title=f'Peak {peaknum}'
                    else: title=names.get(plot['role'],plot['role'])
                    entries.append(f'\\l({plot["index"]}) {title}')
                legend='\\n'.join(entries)
            legends.append((i,legend,len(plan.panels)>1 or comparison))
        else: cmds.append('label -r legend;')
        execute(app,'\n'.join(cmds),name)
        if options.peak_labels and len(panel)==1 and panel[0].kind=='xps':
            ds=panel[0]; y0=float(app.Evaluate('layer.y.from')); y1=float(app.Evaluate('layer.y.to'))
            for k,c in enumerate([c for c in ds.curves if c.role=='peak']):
                valid=[j for j,(x,y) in enumerate(zip(ds.x,c.values)) if low<=x<=high and y is not None]
                if not valid: continue
                j=max(valid,key=lambda j:c.values[j]); x=ds.x[j]; y=c.values[j]
                obj=f'GSPeak{k+1}'
                execute(app,f'label -n {obj} "{x:.1f} eV"; {obj}.attach=2; {obj}.x={x:.15g}; {obj}.y={min(y+(y1-y0)*.05,y1-(y1-y0)*.04):.15g}; {obj}.fsize={baseline["xb"]["size"]*.6:g};',name)
        audits.append(snapshot(app)); all_curves.append(reports)
    for i,legend,inside in legends:
        cmds=[f'layer -s {i};','label -r legend;',f'label -sa -n legend "{legend}";','legend.show=1;']
        if inside:
            low,high=plan.x_range
            edge=low if options.reverse_xps and plan.kind=='xps' else high
            sign=-1 if options.reverse_xps and plan.kind=='xps' else 1
            cmds.extend(['legend.attach=2;',f'legend.fsize={baseline["xb"]["size"]*.75:g};',f'legend.x={edge:.15g}-{sign}*(abs(legend.dx)/2+{(high-low)*.025:.15g});','legend.y=layer.y.to-abs(legend.dy)/2-(layer.y.to-layer.y.from)*0.045;'])
        execute(app,'\n'.join(cmds),name)
    if multi:
        execute(app,f'laylink igp:={name} igl:=1 destlayers:="2:{len(plan.panels)+1}" XAxis:=1 YAxis:=0 unit:=page;',name)
        widths=[]
        for i in range(2,len(plan.panels)+2):
            execute(app,f'layer -s {i};',name)
            if plan.panels[i-2][0].kind!='reference': widths.append(tick_width(app,name,tick_texts(snapshot(app)),baseline['ticks']['y']))
    else:
        widths=[tick_width(app,name,tick_texts(snapshot(app)),baseline['ticks']['y'])]
    offset=baseline['yl']['normalized_x']
    if options.show_y_values: offset-=max(0,max(widths,default=0)-baseline_tick_width)
    # Rescaling several curves can leave titles at an earlier scale coordinate.
    # Preserve the template's relative center without changing its fonts/anchors.
    execute(app,f'layer -s 1; xb.x=layer.x.from+(layer.x.to-layer.x.from)*{baseline["xb"]["normalized_x"]:.15g}; xb.y=layer.y.from+(layer.y.to-layer.y.from)*{baseline["xb"]["normalized_y"]:.15g}; yl.x=layer.x.from+(layer.x.to-layer.x.from)*{offset:.15g}; yl.y=layer.y.from+(layer.y.to-layer.y.from)*{baseline["yl"]["normalized_y"]:.15g};',name)
    audits=[]
    for i in range(1,len(plan.panels)+1+int(multi)):
        execute(app,f'layer -s {i};',name); audits.append(snapshot(app))
    # Geometry changes are treated as errors, never silently fixed by enlarging the page.
    for audit in audits:
        for key in ('page.width','page.height','page.resx','page.resy','layer.left','layer.width'):
            if not math.isclose(audit[key],baseline[key],abs_tol=1e-6): raise RuntimeError(f'Origin 改变了默认尺寸：{key}')
    if multi:
        # Origin rounds layer rectangles to native page pixels.
        tolerance=(100/baseline['page.height']+1e-6) if baseline['layer.unit']==1 else .003
        if abs(audits[1]['layer.top']-baseline['layer.top'])>tolerance or abs(audits[-1]['layer.top']+audits[-1]['layer.height']-baseline['layer.top']-baseline['layer.height'])>tolerance:
            raise RuntimeError('多层图超出了默认绘图区范围')
    if len(plan.panels)==1:
        for key in ('layer.top','layer.height'):
            if not math.isclose(audits[0][key],baseline[key],abs_tol=1e-6): raise RuntimeError('Origin 改变了默认绘图区位置')
    for obj in ('xb','yl'):
        for key in ('size','attach','font'):
            if not math.isclose(audits[0][obj][key],baseline[obj][key],abs_tol=.003):
                raise RuntimeError(f'原生轴标题的默认字体或关联发生变化：{obj}.{key}')
    preview=None
    if preview_dir:
        preview_dir=Path(preview_dir).resolve(); preview_dir.mkdir(parents=True,exist_ok=True)
        execute(app,f'win -a {name}; layer -s 1;')
        execute(app,f'expGraph type:=png path:="{quote(preview_dir)}" filename:="{name}" overwrite:=1 tr1.width:=1600 tr1.unit:=2;',name)
        preview=str(preview_dir/f'{name}.png')
        if not Path(preview).is_file(): raise RuntimeError('Origin 没有生成预览图')
    return dict(graph=name,title=plan.title,kind=plan.kind,preview=preview,
                baseline=baseline,audit=audits,curves=all_curves,
                size_inches=[baseline['page.width']/baseline['page.resx'],baseline['page.height']/baseline['page.resy']],
                data=[d.id for p in plan.panels for d in p],data_layers=len(plan.panels),shared_native_axis_layer=multi,
                native_axis_titles=True,default_geometry_preserved=True)

def render(session:OriginSession,plans,options,datasets,preview_dir=None,progress=None):
    session.connect(options.connection)
    session.guard(); app=session.app
    created=[]; books={}; results=[]
    try:
        used={d.id:d for plan in plans for panel in plan.panels for d in panel}
        for i,ds in enumerate(used.values()):
            if progress: progress(f'正在导入 {ds.label} · {ds.region or "XRD"}')
            books[ds.id]=make_workbook(app,ds,options,created)
        for i,plan in enumerate(plans):
            if progress: progress(f'正在绘制 {i+1}/{len(plans)} · {plan.title}')
            session.guard()
            results.append(render_graph(app,plan,options,books,created,preview_dir))
        app.Visible=1
        return dict(graphs=results,workbooks=[dict(dataset=k,page=v['page'],roundtrip_max_error=v['roundtrip_max_error']) for k,v in books.items()],origin=session.status())
    except Exception:
        for name in reversed(created):
            try: app.DestroyPage(name)
            except Exception: pass
        raise
