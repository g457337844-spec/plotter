from __future__ import annotations
import csv, hashlib, io, math, re
from pathlib import Path
from .models import Curve, Dataset, DataError, PALETTE, finite, validate_dataset

NUMBER = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'

def dataset_id(path, sheet, kind):
    return hashlib.sha256(f'{str(path).casefold()}|{sheet}|{kind}'.encode('utf-8')).hexdigest()[:20]

def text(value): return '' if value is None else str(value).strip().lstrip('\ufeff')

def numeric(value):
    if value is None or isinstance(value,bool): return False
    if isinstance(value,(int,float)): return math.isfinite(value)
    return bool(re.fullmatch(NUMBER,str(value).strip())) and math.isfinite(float(value))

def header_role(value):
    h = text(value).casefold()
    if any(s in h for s in ('binding energy','bindingenergy','结合能','binding_energy')) or h in {'be','b.e.','energy (ev)'}: return 'x'
    if any(s in h for s in ('backgnd','background','baseline','背景','本底')): return 'background'
    if any(s in h for s in ('拟合包封','envelope','total fit','fit sum','fitted sum')): return 'envelope'
    if any(s in h for s in ('拟合峰','fit peak','fitpeak','component','峰值')): return 'peak'
    if any(s in h for s in ('intensity','counts','measured','raw data','experimental','强度','实测')): return 'measured'
    if h in {'x','ev'}: return 'x'
    return 'unknown'

def region_of(name):
    match = re.search(r'(?i)([A-Z][a-z]?\s*\d[spdf](?:\s*\d/\d)?|[A-Z][a-z]?\s*LMM|[A-Z][a-z]?\s*LM\d)',name)
    if match: return re.sub(r'\s+','',match.group(1))
    if re.search(r'(?i)survey|wide|全谱',name): return 'Survey'
    if re.search(r'(?i)valence|价带|\bvb\b',name): return 'VB'
    return re.sub(r'(?i)\s*scan\s*[a-z]?\s*$', '', name).strip() or 'Spectrum'

def parse_xps_rows(rows, *, path: Path, sheet: str, mapping=None) -> Dataset | None:
    # Headers and units are detected separately; the first data row is never a unit row.
    rows = [list(r) for r in rows]
    mapping = mapping or {}
    header_i, x_col = None, None
    for i,row in enumerate(rows[:100]):
        candidates = [j for j,v in enumerate(row) if header_role(v)=='x']
        if candidates:
            header_i, x_col = i, candidates[0]; break
    if header_i is None: return None
    if mapping.get('x_column') is not None: x_col = int(mapping['x_column'])-1
    head = rows[header_i]
    data_i = next((i for i in range(header_i+1,min(len(rows),header_i+20))
                   if x_col < len(rows[i]) and (isinstance(rows[i][x_col],(int,float))
                   or re.fullmatch(NUMBER,text(rows[i][x_col])))),None)
    if data_i is None: raise DataError(f'{sheet} 找到能量表头，但没有能量数据')
    ncols = max(len(row) for row in rows)
    units = ['']*ncols
    for row in rows[header_i+1:data_i]:
        for j,v in enumerate(row):
            if text(v) and not numeric(v): units[j]=text(v)
    cols = [j for j in range(ncols) if j!=x_col and any(j<len(r) and numeric(r[j]) for r in rows[data_i:])]
    roles = {j:header_role(head[j] if j<len(head) else None) for j in cols}
    measured = [j for j in cols if roles[j]=='measured']
    if mapping.get('y_column') is not None:
        measured = [int(mapping['y_column'])-1]
        if measured[0] not in cols: raise DataError(f'{sheet} 指定的实测列没有数字')
    if not measured:
        unknown = [j for j in cols if roles[j]=='unknown']
        with_units = [j for j in unknown if re.search(r'(?i)counts|intensity|a\.\s*u\.|cps|强度',units[j])]
        measured = with_units if with_units else unknown
    if len(measured)!=1:
        raise DataError(f'{sheet} 的实测强度列不明确，请指定实测列；不会按列顺序猜测。',
                        'ambiguous_column', dict(sheet=sheet,candidates=[dict(column=j+1,header=text(head[j]) if j<len(head) else '',unit=units[j]) for j in measured]))
    y_col=measured[0]; roles[y_col]='measured'
    selected=[y_col]+[j for j in cols if j!=y_col and roles[j] in {'peak','envelope','background'}]
    x, values, row_numbers = [], {j:[] for j in selected}, []
    warnings=[]; blank_rows=[]
    for i,row in enumerate(rows[data_i:],data_i):
        xv=row[x_col] if x_col<len(row) else None
        if not text(xv):
            if any(j<len(row) and text(row[j]) for j in selected):
                raise DataError(f'{sheet} 第 {i+1} 行缺少能量，但仍有强度数据')
            if i < len(rows)-1: blank_rows.append(i+1)
            continue
        if not numeric(xv):
            raise DataError(f'{sheet} 第 {i+1} 行的能量不是有限数字：{text(xv)}')
        x.append(finite(xv)); row_numbers.append(i+1)
        for j in selected:
            v=row[j] if j<len(row) else None
            if not text(v): values[j].append(None)
            elif numeric(v): values[j].append(finite(v))
            else: raise DataError(f'{sheet} 第 {i+1} 行、第 {j+1} 列不是有限数字：{text(v)}')
    curves=[]
    measured_header=text(head[y_col] if y_col<len(head) else '').casefold()
    inferred_unit='Counts / s' if re.search(r'(?i)cps|counts\s*/\s*s',measured_header) else 'Counts' if 'counts' in measured_header else 'a.u.'
    measured_unit=units[y_col] or inferred_unit
    for j in selected:
        label=text(head[j] if j<len(head) else '') or ('Measured' if j==y_col else f'Column {j+1}')
        missing=sum(v is None for v in values[j])
        if missing:
            warnings.append(f'{label} 有 {missing} 个缺失点，已保留该曲线并在缺失点断开')
        curves.append(Curve(roles[j],label,values[j],j+1,units[j] or measured_unit))
    if not units[y_col]: warnings.append(f'表格未提供强度单位，按表头显示为 {measured_unit}；可在高级设置中修改轴标题')
    if blank_rows: warnings.append(f'已跳过 {len(blank_rows)} 个空数据行，未截断后续数据')
    ignored=[j+1 for j in cols if j not in selected]
    if ignored: warnings.append(f'未用于绘图的辅助数字列：{", ".join(map(str,ignored))}')
    duplicates=len(x)-len(set(x))
    if duplicates: warnings.append(f'有 {duplicates} 个重复能量值，已保留原始顺序')
    ds=Dataset(dataset_id(path,sheet,'xps'),'xps',str(path),path.stem,x,curves,sheet,region_of(sheet),units[x_col] or 'eV',
               warnings=warnings,metadata=dict(header_row=header_i+1,data_row=data_i+1,row_numbers=row_numbers,measured_column=y_col+1))
    validate_dataset(ds)
    return ds

def load_excel_rows(path: Path):
    if path.suffix.casefold() in {'.xlsx','.xlsm'}:
        import openpyxl
        wb=openpyxl.load_workbook(path,read_only=True,data_only=True)
        try:
            return [(ws.title,list(ws.iter_rows(values_only=True))) for ws in wb.worksheets]
        finally: wb.close()
    if path.suffix.casefold() not in {'.xls','.xlsb'}: raise DataError('不支持这个表格格式')
    # Legacy formats use a private, read-only Excel instance; macros are disabled.
    import win32com.client
    app=win32com.client.DispatchEx('Excel.Application'); wb=None
    try:
        app.Visible=False; app.DisplayAlerts=False; app.AutomationSecurity=3
        wb=app.Workbooks.Open(str(path),UpdateLinks=0,ReadOnly=True)
        return [(str(ws.Name),[list(r) for r in ws.UsedRange.Value]) for ws in wb.Worksheets]
    finally:
        if wb is not None: wb.Close(SaveChanges=False)
        app.Quit()

def read_text(path: Path):
    raw=path.read_bytes()
    encodings=('utf-16','utf-8-sig','gb18030') if raw[:2] in {b'\xff\xfe',b'\xfe\xff'} else ('utf-8-sig','gb18030')
    for encoding in encodings:
        try: return raw.decode(encoding)
        except UnicodeDecodeError: pass
    raise DataError(f'{path.name} 的文本编码无法识别，请保存为 UTF-8')

def numeric_tokens(line):
    value=line.strip()
    if not value or value.startswith(('*','#','//')): return None
    tokens=re.split(r'[\s,;]+',value)
    if len(tokens)<2 or not all(re.fullmatch(NUMBER,t) for t in tokens): return None
    pair=tuple(finite(t,'衍射数据') for t in tokens[:2])
    return pair

def parse_xrd(path: Path, content: str):
    points=[]; bad=[]; in_data=False; row_numbers=[]
    for i,line in enumerate(content.splitlines(),1):
        stripped=line.strip()
        if not stripped or stripped.startswith(('*','#','//')): continue
        pair=numeric_tokens(line)
        if pair:
            points.append(pair); row_numbers.append(i); in_data=True
        elif in_data or re.match(r'^\s*'+NUMBER+r'[\s,;]',line):
            bad.append(i)
    if bad: raise DataError(f'{path.name} 的第 {", ".join(map(str,bad[:8]))} 行含有不完整或非法数值，已停止导入')
    if len(points)<10: raise DataError(f'{path.name} 至少需要 10 行两列 XRD 数据')
    order=sorted(range(len(points)),key=lambda i:points[i][0])
    warnings=[]
    if order!=list(range(len(points))): warnings.append('角度不是递增顺序，已按角度排序；原始文件未改变')
    if len(set(p[0] for p in points))<len(points): warnings.append('存在重复角度值，已保留全部点')
    points=[points[i] for i in order]
    ds=Dataset(dataset_id(path,'','xrd'),'xrd',str(path),path.stem,[p[0] for p in points],
               [Curve('measured','Intensity',[p[1] for p in points],2,'a.u.')],x_unit='deg',warnings=warnings,
               metadata=dict(row_numbers=[row_numbers[i] for i in order]))
    validate_dataset(ds); return ds

def parse_reference(path, content):
    lines=content.splitlines()
    m=re.search(r'(?im)PDF\s*#\s*(\d+\s*-\s*\d+)',content)
    if not m: raise DataError('未找到 PDF 参考卡号')
    number=re.sub(r'\s+','',m.group(1))
    header=next((i for i,l in enumerate(lines) if re.search(r'(?i)2[-\s]*theta',l) and re.search(r'(?i)h\s*k\s*l',l)),None)
    if header is None: raise DataError(f'{path.name} 未找到参考峰表头')
    pre=[l.strip() for l in lines[:header] if l.strip() and not re.search(r'(?i)PDF\s*#',l)]
    formula=pre[1] if len(pre)>1 else pre[0] if pre else path.stem
    points=[]; hkls=[]
    pat=re.compile(r'^\s*('+NUMBER+r')\s+('+NUMBER+r')\s+('+NUMBER+r')\s+\(\s*([^)]*)\)')
    for i,l in enumerate(lines[header+1:],header+2):
        m=pat.match(l)
        if m:
            x,y=finite(m[1]),finite(m[3]); points.append((x,y)); hkls.append(' '.join(m[4].split()))
        elif re.match(r'^\s*'+NUMBER+r'\s+',l): raise DataError(f'{path.name} 第 {i} 行参考峰格式无效')
    if len(points)<2: raise DataError(f'{path.name} 的参考峰不足两点')
    if any(y<0 for x,y in points): raise DataError('参考峰强度不能为负数')
    ds=Dataset(dataset_id(path,'','reference'),'reference',str(path),f'{formula} (PDF#{number})',
               [p[0] for p in points],[Curve('sticks',formula,[p[1] for p in points],2,'Relative intensity')],
               x_unit='deg',metadata=dict(card_number=number,hkl=hkls,formula=formula))
    validate_dataset(ds); return ds

def import_path(path_value, mapping=None):
    path=Path(path_value).expanduser().resolve()
    if not path.is_file(): raise DataError(f'文件不存在：{path}')
    if path.stat().st_size>100*1024*1024: raise DataError('文件超过 100 MB，请拆分后导入')
    if path.suffix.casefold() in {'.xlsx','.xlsm','.xls','.xlsb'}:
        datasets=[]; notices=[]; issues=[]
        for name,rows in load_excel_rows(path):
            try:
                ds=parse_xps_rows(rows,path=path,sheet=name,mapping=(mapping or {}).get(name))
                if ds: datasets.append(ds)
                else: notices.append(f'{name}：没有 XPS 能量表头，未导入')
            except DataError as exc:
                issues.append(dict(message=str(exc),code=exc.code,details=exc.details,sheet=name,path=str(path)))
        if not datasets and not issues: raise DataError(f'{path.name} 中没有可识别的 XPS 数据')
        return datasets,notices,issues
    if path.suffix.casefold() in {'.txt','.csv','.dat','.xy','.ras'}:
        content=read_text(path)
        ds=parse_reference(path,content) if re.search(r'(?i)PDF\s*#\s*\d+\s*-\s*\d+',content[:5000]) else parse_xrd(path,content)
        return [ds],[],[]
    raise DataError('支持 XPS 表格（xlsx / xls）和 XRD 文本（txt / csv / dat / ras）')
