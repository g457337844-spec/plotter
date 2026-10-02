from __future__ import annotations
import math, re
from dataclasses import dataclass, field, asdict

PALETTE = ('#007AFF', '#FF375F', '#30A46C', '#AF52DE', '#FF9500', '#00A7B5', '#5856D6', '#A2845E')

class DataError(ValueError):
    def __init__(self, message: str, code='invalid_data', details=None):
        super().__init__(message)
        self.code, self.details = code, details or {}

def finite(value, name='数值') -> float:
    if isinstance(value, bool):
        raise DataError(f'{name}不能是布尔值')
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise DataError(f'{name}必须是数字') from None
    if not math.isfinite(result):
        raise DataError(f'{name}必须是有限数值，不能使用 NaN 或无穷大')
    return result

def color(value: str) -> str:
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', str(value)):
        raise DataError('颜色格式应为 #RRGGBB')
    return value.upper()

@dataclass
class Curve:
    role: str
    label: str
    values: list[float | None]
    source_column: int = 0
    unit: str = ''

@dataclass
class Dataset:
    id: str
    kind: str
    source: str
    label: str
    x: list[float]
    curves: list[Curve]
    sheet: str = ''
    region: str = ''
    x_unit: str = ''
    color: str = PALETTE[0]
    enabled: bool = True
    warnings: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def measured(self) -> Curve:
        return next(c for c in self.curves if c.role == 'measured')

    @property
    def x_range(self):
        return min(self.x), max(self.x)

    def summary(self) -> dict:
        return dict(id=self.id, kind=self.kind, source=self.source, label=self.label,
                    sheet=self.sheet, region=self.region, points=len(self.x),
                    x_range=self.x_range, x_unit=self.x_unit, color=self.color,
                    enabled=self.enabled, warnings=self.warnings, metadata={k:v for k,v in self.metadata.items() if k not in {'row_numbers','hkl'}},
                    curves=[dict(role=c.role,label=c.label,source_column=c.source_column,
                                 unit=c.unit,missing=sum(v is None for v in c.values)) for c in self.curves])

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        value = dict(value)
        value['curves'] = [Curve(**v) for v in value['curves']]
        ds = cls(**value)
        validate_dataset(ds)
        return ds

def validate_dataset(ds: Dataset):
    if ds.kind not in {'xps','xrd','reference'} or len(ds.x) < 2 or not ds.curves:
        raise DataError(f'{ds.label} 的数据结构不完整')
    ds.color = color(ds.color)
    if len(ds.label.strip()) == 0 or len(ds.label) > 160:
        raise DataError('样品名称应为 1–160 个字符')
    ds.x=[finite(x,'横坐标') for x in ds.x]
    if max(ds.x) == min(ds.x): raise DataError('横坐标不能全部相同')
    for curve in ds.curves:
        if len(curve.values) != len(ds.x): raise DataError('数据列长度不一致')
        usable = 0
        for i,value in enumerate(curve.values):
            if value is not None:
                curve.values[i]=finite(value, curve.label); usable += 1
        if usable < 2: raise DataError(f'{curve.label} 的有效数据不足两点')
    if ds.kind != 'reference': ds.measured

@dataclass
class Options:
    mode: str = 'separate'
    template: str = 'Origin'
    connection: str = 'existing'
    x_min: float | None = None
    x_max: float | None = None
    reverse_xps: bool = False
    normalize_xrd: bool = False
    line_width: float = 1.5
    peak_fill: bool = True
    peak_labels: bool = False
    legend: bool = False
    y_title: str = ''
    x_title: str = ''
    show_y_values: bool = True

    @classmethod
    def from_dict(cls, value: dict | None):
        value = value or {}
        unknown = set(value) - set(cls.__dataclass_fields__)
        if unknown: raise DataError(f'未知设置：{", ".join(sorted(unknown))}')
        obj = cls(**value)
        if obj.mode not in {'separate','stack','overlay'}: raise DataError('绘图方式无效')
        if obj.connection not in {'existing','new'}: raise DataError('Origin 连接方式无效')
        obj.template = str(obj.template).strip()
        if not obj.template or any(c in obj.template for c in '\r\n";'):
            raise DataError('请填写有效的 Origin 模板名称')
        if (obj.x_min is None) != (obj.x_max is None): raise DataError('横坐标起点和终点需要同时填写')
        if obj.x_min is not None:
            obj.x_min, obj.x_max = finite(obj.x_min,'横坐标起点'), finite(obj.x_max,'横坐标终点')
            if obj.x_min >= obj.x_max: raise DataError('横坐标起点必须小于终点；反向坐标请使用单独的开关')
        obj.line_width = finite(obj.line_width,'线宽')
        if not .1 <= obj.line_width <= 8: raise DataError('线宽应在 0.1–8 pt 之间')
        for key in ('reverse_xps','normalize_xrd','peak_fill','peak_labels','legend','show_y_values'):
            if type(getattr(obj,key)) is not bool: raise DataError(f'{key} 必须是布尔值')
        for key in ('y_title','x_title'):
            value = getattr(obj,key)
            if not isinstance(value,str) or len(value)>180: raise DataError('轴标题最多 180 个字符')
        return obj

    def to_dict(self): return asdict(self)
