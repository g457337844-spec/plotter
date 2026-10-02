from __future__ import annotations
import json, math, os, sys
from concurrent.futures import Future
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, QSize, Signal, QObject
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPainterPath, QPen, QLinearGradient, QRadialGradient, QPixmap, QAction, QKeySequence
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QFrame,QVBoxLayout,QHBoxLayout,
    QLabel,QPushButton,QToolButton,QComboBox,QCheckBox,QLineEdit,QDoubleSpinBox,QScrollArea,
    QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QFileDialog,QColorDialog,
    QDialog,QDialogButtonBox,QTextEdit,QFormLayout,QMessageBox,QSplitter,QProgressBar,QMenu,QGraphicsDropShadowEffect)
from . import __version__
from .models import Dataset,Options,DataError,PALETTE
from .planning import display_values,axis_titles
from .service import Broker,app_data
from .bridge import Bridge

def asset_path(name): return Path(getattr(sys,'_MEIPASS',str(Path(__file__).resolve().parents[1]))) / 'assets' / name

STYLE='''
QWidget { color:#1d2538; font-family:"Microsoft YaHei UI"; font-size:13px; }
QMainWindow, QWidget#shell { background:transparent; }
QFrame#sidebar { background:rgba(255,255,255,155); border:1px solid rgba(255,255,255,230); border-radius:24px; }
QFrame#card { background:#ffffff; border:1px solid #e7ebf4; border-radius:20px; }
QFrame#inset { background:#f5f7fc; border:0; border-radius:13px; }
QLabel { background:transparent; border:0; }
QLabel#title { font-size:27px; font-weight:600; color:#182137; }
QLabel#subtitle, QLabel#muted { color:#788398; font-size:12px; }
QLabel#section { font-size:15px; font-weight:600; }
QLabel#overline { color:#9aa4b5; font-size:11px; font-weight:600; }
QPushButton, QToolButton { background:#f3f5fa; border:1px solid transparent; border-radius:16px; padding:8px 14px; min-height:18px; font-weight:500; }
QPushButton:hover,QToolButton:hover { background:#e9eef8; }
QPushButton:pressed,QToolButton:pressed { background:#dce6f7; }
QPushButton:disabled,QToolButton:disabled { color:#acb3c1; background:#f2f4f8; }
QPushButton#primary,QToolButton#primary { color:white; background:#007aff; border:1px solid #007aff; }
QPushButton#primary:hover,QToolButton#primary:hover { background:#006ce4; }
QPushButton#primary:disabled { background:#b8d7fc; border-color:#b8d7fc; }
QPushButton#nav { text-align:left; padding:12px 16px; border-radius:16px; background:transparent; color:#66728a; font-weight:500; }
QPushButton#nav:checked { background:rgba(0,122,255,20); color:#007aff; }
QPushButton#nav:hover { background:rgba(0,122,255,12); }
QPushButton#link { background:transparent; color:#007aff; padding:4px 2px; font-size:12px; }
QLineEdit,QComboBox,QDoubleSpinBox { background:#f5f7fc; border:1px solid #e9edf5; border-radius:11px; padding:8px 10px; min-height:19px; selection-background-color:#c3ddff; }
QLineEdit:focus,QComboBox:focus,QDoubleSpinBox:focus { border:1px solid #75b3ff; background:#fff; }
QLineEdit:disabled { color:#a9b1bf; background:#f7f8fb; }
QComboBox::drop-down { border:0; width:25px; }
QComboBox QAbstractItemView { background:white; selection-background-color:#e7f1ff; selection-color:#007aff; border:1px solid #e3e8f2; padding:5px; }
QCheckBox { spacing:9px; background:transparent; padding:4px 0; }
QCheckBox::indicator { width:16px; height:16px; background:#fff; border:1px solid #cbd3e0; border-radius:5px; }
QCheckBox::indicator:checked { background:#007aff; border:1px solid #007aff; image:none; }
QTableWidget { background:white; border:0; gridline-color:transparent; selection-background-color:#edf4ff; selection-color:#1d2538; outline:0; }
QTableWidget::item { padding:7px 5px; border-bottom:1px solid #f0f3f8; }
QTableWidget::item:selected { background:#edf4ff; }
QHeaderView::section { background:white; border:0; border-bottom:1px solid #e9edf5; color:#95a0b3; padding:9px 5px; font-size:11px; }
QScrollArea { border:0; background:transparent; }
QScrollArea>QWidget>QWidget { background:transparent; }
QScrollBar:vertical { width:6px; background:transparent; margin:4px 0; }
QScrollBar::handle:vertical { background:#d5dce8; min-height:25px; border-radius:3px; }
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical { background:transparent; }
QProgressBar { border:0; border-radius:3px; background:#e8f0fc; max-height:5px; }
QProgressBar::chunk { background:#007aff; border-radius:3px; }
QSplitter::handle { background:transparent; width:12px; }
QDialog { background:#f7f9fd; }
QTextEdit { background:white; border:1px solid #e3e8f1; border-radius:12px; padding:10px; }
QToolTip { background:#1c2739; color:#fff; border:0; padding:6px; }
'''

def label(value,obj=None):
    w=QLabel(value)
    if obj: w.setObjectName(obj)
    return w

def button(value,callback=None,primary=False):
    w=QPushButton(value)
    if primary: w.setObjectName('primary')
    if callback: w.clicked.connect(callback)
    return w

def card():
    w=QFrame(); w.setObjectName('card')
    layout=QVBoxLayout(w); layout.setContentsMargins(20,18,20,18); layout.setSpacing(12)
    return w,layout

class Shell(QWidget):
    def paintEvent(self,event):
        painter=QPainter(self); painter.setRenderHint(QPainter.Antialiasing)
        grad=QLinearGradient(0,0,self.width(),self.height()); grad.setColorAt(0,QColor('#eaf3ff')); grad.setColorAt(1,QColor('#f5f2fd'))
        painter.fillRect(self.rect(),grad)
        glow=QRadialGradient(self.width()*.65,0,self.width()*.7); glow.setColorAt(0,QColor(255,255,255,245)); glow.setColorAt(1,QColor(255,255,255,0))
        painter.fillRect(self.rect(),glow)

class SpectrumCanvas(QWidget):
    def __init__(self):
        super().__init__(); self.setMinimumHeight(230); self.datasets=[]; self.options=Options(); self.image=None
        self.setMouseTracking(True); self.setToolTip('这是数据预览。Origin 成图使用本机模板和原生轴标题。')

    def set_data(self,datasets,options):
        self.datasets=datasets; self.options=options; self.image=None; self.update()

    def set_image(self,path):
        self.image=QPixmap(path) if path else None; self.update()

    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.fillRect(self.rect(),Qt.white)
        if self.image and not self.image.isNull():
            pix=self.image.scaled(self.size()-QSize(16,8),Qt.KeepAspectRatio,Qt.SmoothTransformation)
            p.drawPixmap((self.width()-pix.width())//2,(self.height()-pix.height())//2,pix); return
        active=[d for d in self.datasets if d.enabled]
        if not active:
            p.setPen(QColor('#a7b1c2')); p.setFont(QFont('Microsoft YaHei UI',14))
            p.drawText(self.rect(),Qt.AlignCenter,'导入数据，预览你的第一张图谱'); return
        first=active[0]
        active=[d for d in active if d.kind==first.kind and (d.kind!='xps' or d.region.casefold()==first.region.casefold())]
        if self.options.mode=='separate': active=active[:1]
        panels=[[d] for d in active[:5]] if self.options.mode=='stack' else [active]
        rect=QRectF(82,22,max(self.width()-110,50),max(self.height()-84,50))
        h=rect.height()/len(panels)
        for i,panel in enumerate(panels):
            area=QRectF(rect.left(),rect.top()+i*h,rect.width(),h)
            self.draw_panel(p,area,panel,i==len(panels)-1)

    def draw_panel(self,p,rect,panel,bottom):
        opts=self.options
        low=opts.x_min if opts.x_min is not None else min(d.x_range[0] for d in panel)
        high=opts.x_max if opts.x_max is not None else max(d.x_range[1] for d in panel)
        if high<=low: return
        ds=panel[0]; compare=len(panel)>1
        series=[]
        for d in panel:
            if d.kind=='xrd': series.append((d,display_values(d,opts),d.color,'measured'))
            elif d.kind=='reference': series.append((d,d.curves[0].values,d.color,'sticks'))
            elif compare: series.append((d,d.measured.values,d.color,'measured'))
            else:
                peaks=[c for c in d.curves if c.role=='peak']
                peaks.sort(key=lambda c:d.x[max(range(len(d.x)),key=lambda j:c.values[j] if c.values[j] is not None else -math.inf)],reverse=True)
                for k,c in enumerate(peaks): series.append((d,c.values,PALETTE[k%len(PALETTE)],'peak'))
                for role,clr in [('background','#9aa4b5'),('envelope','#FF375F'),('measured',d.color)]:
                    for c in d.curves:
                        if c.role==role: series.append((d,c.values,clr,role))
        values=[v for d,ys,clr,role in series for x,v in zip(d.x,ys) if v is not None and low<=x<=high]
        if not values: return
        ylow,yhigh=min(values),max(values); span=max(yhigh-ylow,abs(yhigh)*.01,1)
        ylow-=span*.05; yhigh+=span*.12
        reverse=opts.reverse_xps and ds.kind=='xps'
        def pos(x,y): return QPointF(rect.left()+rect.width()*((high-x if reverse else x-low)/(high-low)),rect.bottom()-(y-ylow)/(yhigh-ylow)*rect.height())
        p.setPen(QPen(QColor('#cbd3e0'),1)); p.drawLine(rect.bottomLeft(),rect.bottomRight()); p.drawLine(rect.topLeft(),rect.bottomLeft())
        p.setFont(QFont('Segoe UI',9)); p.setPen(QColor('#7f8ba0'))
        for k in range(4):
            y=ylow+(yhigh-ylow)*k/3; pt=pos(low,y)
            p.drawText(QRectF(2,pt.y()-8,70,17),Qt.AlignRight|Qt.AlignVCenter,f'{y:.0f}' if abs(y)>=10 else f'{y:.1f}')
        if bottom:
            for k in range(6):
                x=low+(high-low)*k/5; pt=pos(x,ylow)
                p.drawText(QRectF(pt.x()-30,rect.bottom()+8,60,18),Qt.AlignCenter,f'{x:g}')
            x_title,y_title=axis_titles(ds,opts)
            p.setPen(QColor('#59657a')); p.setFont(QFont('Segoe UI',10))
            p.drawText(QRectF(rect.left(),rect.bottom()+31,rect.width(),22),Qt.AlignCenter,x_title)
        p.save(); p.translate(18,rect.center().y()); p.rotate(-90); p.setFont(QFont('Segoe UI',9)); p.setPen(QColor('#7f8ba0'))
        p.drawText(QRectF(-rect.height()/2,-10,rect.height(),20),Qt.AlignCenter,axis_titles(ds,opts)[1]); p.restore()
        p.save(); p.setClipRect(rect.adjusted(0,0,1,1))
        for d,ys,clr,role in series:
            path=QPainterPath(); running=False
            step=max(1,len(d.x)//1600)
            for j in range(0,len(d.x),step):
                x,v=d.x[j],ys[j]
                if v is None or not low<=x<=high: running=False; continue
                pt=pos(x,v)
                if role=='sticks': path.moveTo(pos(x,0)); path.lineTo(pt); continue
                if running: path.lineTo(pt)
                else: path.moveTo(pt); running=True
            if role=='peak' and opts.peak_fill:
                bg=next((c.values for c in d.curves if c.role=='background'),None)
                indices=[j for j in range(0,len(d.x),step) if low<=d.x[j]<=high and ys[j] is not None and bg and bg[j] is not None]
                if len(indices)>1:
                    fill=QPainterPath(); fill.moveTo(pos(d.x[indices[0]],ys[indices[0]]))
                    for j in indices[1:]: fill.lineTo(pos(d.x[j],ys[j]))
                    for j in reversed(indices): fill.lineTo(pos(d.x[j],bg[j]))
                    fill.closeSubpath(); grad=QLinearGradient(0,rect.top(),0,rect.bottom()); c=QColor(clr); c.setAlpha(125); grad.setColorAt(0,c); c.setAlpha(12); grad.setColorAt(1,c)
                    p.fillPath(fill,grad)
            p.setPen(QPen(QColor(clr),1.35)); p.drawPath(path)
        p.restore()
        p.setFont(QFont('Segoe UI',10)); p.setPen(QColor(ds.color))
        p.drawText(rect.adjusted(8,8,-8,-8),Qt.AlignRight|Qt.AlignTop,' / '.join(d.label for d in panel)+(f' · {ds.region}' if ds.region else ''))

class UiRequests(QObject):
    requested=Signal(str,object,object)

class MainWindow(QMainWindow):
    def __init__(self,broker:Broker,bridge:Bridge | None=None):
        super().__init__(); self.broker=broker; self.bridge=bridge; self.jobs=[]; self.state={}; self.datasets=[]
        self.filter='all'; self.refreshing=False; self.known_revision=-1; self.tick_count=0; self.busy=False; self.known_history=0
        self.setWindowTitle(f'绘图器 {__version__}'); self.setWindowIcon(QIcon(str(asset_path('mark.svg'))))
        area=QApplication.primaryScreen().availableGeometry()
        self.resize(min(1360,max(area.width()-70,1040)),min(900,max(area.height()-60,700)))
        self.setMinimumSize(1040,700); self.setAcceptDrops(True)
        self.requests=UiRequests(); self.requests.requested.connect(self.ui_request)
        broker.engine.ui=self.external_ui
        self.build(); self.setStyleSheet(STYLE+f'QCheckBox::indicator:checked {{ image:url("{asset_path("check.svg").as_posix()}"); }}')
        self.refresh(broker.call('state',{'full':True}))
        self.timer=QTimer(self); self.timer.timeout.connect(self.poll); self.timer.start(100)
        delete=QAction(self); delete.setShortcut(QKeySequence.Delete); delete.triggered.connect(self.remove_selected); self.addAction(delete)
        choose=QAction(self); choose.setShortcut(QKeySequence.Open); choose.triggered.connect(self.choose_files); self.addAction(choose)
        save=QAction(self); save.setShortcut(QKeySequence.Save); save.triggered.connect(self.save_workspace); self.addAction(save)
        for direction,key in ((-1,'Alt+Up'),(1,'Alt+Down')):
            move=QAction(self); move.setShortcut(QKeySequence(key)); move.triggered.connect(lambda checked,d=direction:self.move_selected(d)); self.addAction(move)

    def build(self):
        shell=Shell(); shell.setObjectName('shell'); self.setCentralWidget(shell)
        root=QHBoxLayout(shell); root.setContentsMargins(20,20,24,20); root.setSpacing(24)
        side=QFrame(); side.setObjectName('sidebar'); side.setFixedWidth(196)
        sl=QVBoxLayout(side); sl.setContentsMargins(18,24,18,18); sl.setSpacing(8)
        logo=QLabel(); logo.setPixmap(QIcon(str(asset_path('mark.svg'))).pixmap(44,44)); sl.addWidget(logo)
        sl.addSpacing(8); title=label('绘图器','section'); title.setStyleSheet('font-size:20px; font-weight:600;'); sl.addWidget(title)
        sl.addWidget(label('SCIENTIFIC PLOTTING','overline')); sl.addSpacing(32)
        self.nav={}
        for key,caption in [('all','全部图谱'),('xps','XPS  光电子能谱'),('xrd','XRD  衍射图谱'),('reference','PDF  参考卡片')]:
            b=button(caption); b.setObjectName('nav'); b.setCheckable(True); b.setChecked(key=='all'); b.clicked.connect(lambda checked,k=key:self.set_filter(k)); sl.addWidget(b); self.nav[key]=b
        sl.addStretch(); self.side_count=label('0 份数据','muted'); sl.addWidget(self.side_count); sl.addSpacing(14)
        bridgebtn=button('●  自动化接口',self.show_mcp); bridgebtn.setStyleSheet('color:#34a56f; background:rgba(255,255,255,210); font-size:12px;'); sl.addWidget(bridgebtn)
        sl.addWidget(label(f'v{__version__}  ·  XPS + XRD','muted')); root.addWidget(side)
        main=QVBoxLayout(); main.setContentsMargins(0,6,0,0); main.setSpacing(18); root.addLayout(main,1)
        header=QHBoxLayout(); htext=QVBoxLayout(); htext.setSpacing(5); htext.addWidget(label('我的图谱','title'))
        htext.addWidget(label('整理数据，预览图谱，在 Origin 中完成绘图。','subtitle')); header.addLayout(htext); header.addStretch()
        header.addWidget(button('打开工作区',self.open_workspace)); header.addWidget(button('保存',self.save_workspace))
        self.importbtn=QToolButton(); self.importbtn.setText('＋ 导入数据'); self.importbtn.setObjectName('primary'); self.importbtn.setPopupMode(QToolButton.MenuButtonPopup)
        self.importbtn.clicked.connect(self.choose_files); menu=QMenu(self.importbtn)
        menu.addAction('选择本地数据文件',self.choose_files); menu.addAction('读取当前 Excel 工作簿',lambda:self.submit('excel_live',{},self.import_done))
        self.importbtn.setMenu(menu); header.addWidget(self.importbtn); main.addLayout(header)
        steps=QHBoxLayout(); steps.setSpacing(12)
        for value in ('1  导入与选择','2  预览与设置','3  Origin 绘图'):
            w=label(value); w.setStyleSheet('color:#8c99ad; font-size:12px; padding:4px 0;'); steps.addWidget(w)
        steps.addStretch(); self.badge=label('保留默认尺寸 · 原生轴标题'); self.badge.setStyleSheet('color:#007aff; font-size:11px;'); steps.addWidget(self.badge); main.addLayout(steps)
        self.banner=label(''); self.banner.setWordWrap(True); self.banner.hide(); main.addWidget(self.banner)
        split=QSplitter(Qt.Horizontal); split.setChildrenCollapsible(False); main.addWidget(split,1)
        left=QWidget(); ll=QVBoxLayout(left); ll.setContentsMargins(0,0,0,0); ll.setSpacing(16)
        data,dl=card(); self.data_card=data; data.setMinimumHeight(260); data.setMaximumHeight(340)
        dr=QHBoxLayout(); self.data_title=label('数据','section'); dr.addWidget(self.data_title); dr.addStretch()
        select=button('全选',self.select_all); select.setObjectName('link'); dr.addWidget(select)
        for direction,caption,tip in ((-1,'↑','上移选中的样品（Alt+↑）'),(1,'↓','下移选中的样品（Alt+↓）')):
            move=button(caption,lambda checked=False,d=direction:self.move_selected(d)); move.setObjectName('link'); move.setToolTip(tip); dr.addWidget(move)
        remove=button('移除',self.remove_selected); remove.setObjectName('link'); dr.addWidget(remove)
        inspect=button('数据详情',self.show_details); inspect.setObjectName('link'); dr.addWidget(inspect); dl.addLayout(dr)
        self.table=QTableWidget(0,7); self.table.setHorizontalHeaderLabels(['选择','颜色','样品名称','谱区 / 类型','点数','范围','状态'])
        self.table.verticalHeader().hide(); self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setShowGrid(False); self.table.setEditTriggers(QAbstractItemView.DoubleClicked|QAbstractItemView.EditKeyPressed)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.Stretch)
        self.table.itemChanged.connect(self.item_changed); self.table.itemSelectionChanged.connect(self.update_preview)
        dl.addWidget(self.table,1); self.empty=label('将 xlsx 或 txt 文件拖到这里，也可以点击“导入数据”。','muted'); self.empty.setWordWrap(True); dl.addWidget(self.empty)
        ll.addWidget(data)
        preview,pl=card(); pr=QHBoxLayout(); pr.addWidget(label('图谱预览','section')); pr.addStretch()
        self.preview_choice=QComboBox(); self.preview_choice.setMinimumWidth(180); self.preview_choice.addItem('数据预览',None); self.preview_choice.currentIndexChanged.connect(self.change_preview); pr.addWidget(self.preview_choice); pl.addLayout(pr)
        self.canvas=SpectrumCanvas(); pl.addWidget(self.canvas,1); self.preview_note=label('数据预览 · 最终排版由 Origin 模板决定','muted'); pl.addWidget(self.preview_note)
        ll.addWidget(preview,1); split.addWidget(left)
        settings,settings_layout=card(); settings.setMinimumWidth(288); settings.setMaximumWidth(340)
        settings_layout.addWidget(label('绘图设置','section'))
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content=QWidget(); form=QVBoxLayout(content); form.setContentsMargins(0,0,8,0); form.setSpacing(13); scroll.setWidget(content)
        self.mode=QComboBox(); self.mode.addItem('分别绘图 · 每份一页','separate'); self.mode.addItem('分层对比 · 同一页','stack'); self.mode.addItem('曲线叠加 · 同一坐标','overlay')
        form.addWidget(label('绘图方式','muted')); form.addWidget(self.mode)
        self.mode_note=label('XPS 对比会按能级分组。PDF 卡片可选。','muted'); self.mode_note.setWordWrap(True); form.addWidget(self.mode_note)
        self.connection=QComboBox(); self.connection.addItem('当前 Origin 窗口','existing'); self.connection.addItem('新建独立 Origin 窗口','new')
        form.addWidget(label('Origin 目标','muted')); form.addWidget(self.connection)
        target=QHBoxLayout(); self.target_info=label('尚未连接','muted'); target.addWidget(self.target_info,1)
        b=button('连接',self.connect_origin); b.setObjectName('link'); target.addWidget(b); form.addLayout(target)
        self.auto_range=QCheckBox('自动横坐标范围'); self.auto_range.setChecked(True); form.addWidget(self.auto_range)
        rangebox=QHBoxLayout(); self.xmin=QLineEdit(); self.xmax=QLineEdit(); self.xmin.setPlaceholderText('起点'); self.xmax.setPlaceholderText('终点'); self.xmin.setEnabled(False); self.xmax.setEnabled(False)
        rangebox.addWidget(self.xmin); rangebox.addWidget(label('—','muted')); rangebox.addWidget(self.xmax); form.addLayout(rangebox)
        self.reverse=QCheckBox('XPS 结合能从大到小'); self.reverse.setToolTip('只影响 XPS；范围仍按小值到大值填写。'); form.addWidget(self.reverse)
        self.fill=QCheckBox('XPS 分峰渐变填充'); self.fill.setChecked(True); self.fill.setToolTip('有背景列时填充到背景线，不把强度改为零基线。'); form.addWidget(self.fill)
        self.peak_labels=QCheckBox('显示 XPS 峰位数值'); form.addWidget(self.peak_labels)
        self.normalize=QCheckBox('XRD 强度归一化'); self.normalize.setToolTip('保留原始强度列，另外生成 0–100% 的显示列。'); form.addWidget(self.normalize)
        self.legend=QCheckBox('显示图例'); form.addWidget(self.legend)
        self.show_y=QCheckBox('显示纵坐标刻度数值'); self.show_y.setChecked(True); form.addWidget(self.show_y)
        row=QHBoxLayout(); row.addWidget(label('曲线线宽','muted')); row.addStretch(); self.line_width=QDoubleSpinBox(); self.line_width.setRange(.1,8); self.line_width.setSingleStep(.1); self.line_width.setValue(1.5); self.line_width.setSuffix(' pt'); row.addWidget(self.line_width); form.addLayout(row)
        self.advanced=button('更多设置  ⌄'); self.advanced.setObjectName('link'); form.addWidget(self.advanced)
        self.advanced_box=QWidget(); adv=QVBoxLayout(self.advanced_box); adv.setContentsMargins(0,0,0,0); adv.setSpacing(9)
        self.template=QLineEdit('Origin'); self.template.setToolTip('留用 Origin 即本机默认图模板。也可填已安装的 Origin 模板名。')
        adv.addWidget(label('Origin 模板','muted')); adv.addWidget(self.template)
        self.xtitle=QLineEdit(); self.xtitle.setPlaceholderText('自动：Binding Energy / 2θ'); adv.addWidget(label('横坐标标题','muted')); adv.addWidget(self.xtitle)
        self.ytitle=QLineEdit(); self.ytitle.setPlaceholderText('自动：实测强度单位'); adv.addWidget(label('纵坐标标题','muted')); adv.addWidget(self.ytitle)
        reset=button('恢复默认设置',self.reset_options); adv.addWidget(reset); form.addWidget(self.advanced_box); self.advanced_box.hide()
        self.advanced.clicked.connect(lambda:self.advanced_box.setVisible(not self.advanced_box.isVisible()))
        form.addStretch(); settings_layout.addWidget(scroll,1)
        self.validation=label('勾选数据后即可绘图','muted'); self.validation.setWordWrap(True); settings_layout.addWidget(self.validation)
        self.drawbtn=button('在 Origin 中绘图  →',self.draw,True); self.drawbtn.setMinimumHeight(28); settings_layout.addWidget(self.drawbtn)
        self.progress=QProgressBar(); self.progress.setRange(0,0); self.progress.setTextVisible(False); self.progress.hide(); settings_layout.addWidget(self.progress)
        split.addWidget(settings); split.setSizes([750,300])
        footer=QHBoxLayout(); self.status=label('就绪','muted'); footer.addWidget(self.status); footer.addStretch(); footer.addWidget(label('支持 xlsx / xls / txt / csv / ras','muted')); main.addLayout(footer)
        for w in (self.mode,self.connection): w.currentIndexChanged.connect(self.options_changed)
        for w in (self.reverse,self.fill,self.peak_labels,self.normalize,self.legend,self.show_y): w.toggled.connect(self.options_changed)
        self.auto_range.toggled.connect(self.range_toggled); self.line_width.valueChanged.connect(self.options_changed)
        for w in (self.xmin,self.xmax,self.template,self.xtitle,self.ytitle): w.editingFinished.connect(self.options_changed)

    def submit(self,command,args=None,callback=None,busy=False):
        if busy:
            self.busy=True; self.drawbtn.setEnabled(False); self.importbtn.setEnabled(False); self.progress.show()
        future=self.broker.submit(command,args); self.jobs.append((future,callback,busy))
        return future

    def poll(self):
        pending=[]; jobs,self.jobs=self.jobs,[]
        for future,callback,busy in jobs:
            if not future.done(): pending.append((future,callback,busy)); continue
            try:
                result=future.result()
                if callback: callback(result)
            except Exception as exc:
                self.message(str(exc),error=True)
                try:
                    with (app_data()/'errors.log').open('a',encoding='utf-8') as log: log.write(f'{type(exc).__name__}: {exc}\n')
                except Exception: pass
            finally:
                if busy:
                    self.busy=False; self.drawbtn.setEnabled(True); self.importbtn.setEnabled(True); self.progress.hide()
        self.jobs.extend(pending)
        self.tick_count+=1
        engine=self.broker.engine
        if engine.progress:
            self.status.setText(engine.progress)
            if not self.busy: self.progress.show()
        elif not self.busy: self.progress.hide()
        count=sum(d.enabled and d.kind!='reference' for d in self.datasets)
        self.drawbtn.setEnabled(bool(count) and not self.busy and not engine.progress)
        self.importbtn.setEnabled(not self.busy and not engine.progress)
        if self.tick_count%5==0 and engine.version!=self.known_revision and not any(f[1]==self.refresh for f in self.jobs):
            self.submit('state',{'full':True},self.refresh)
        if getattr(self,'close_requested',False) and not self.busy and not engine.progress: self.close()

    def refresh(self,value):
        self.refreshing=True
        selected=self.selected_ids(); self.state=value; self.known_revision=value['revision']
        self.datasets=[Dataset.from_dict(v) for v in value['datasets']]
        self.table.blockSignals(True); self.table.setRowCount(0)
        visible=[d for d in self.datasets if self.filter=='all' or d.kind==self.filter]
        for row,ds in enumerate(visible):
            self.table.insertRow(row)
            use=QTableWidgetItem(); use.setData(Qt.UserRole,ds.id); use.setFlags(Qt.ItemIsEnabled|Qt.ItemIsSelectable|Qt.ItemIsUserCheckable)
            use.setCheckState(Qt.Checked if ds.enabled else Qt.Unchecked); self.table.setItem(row,0,use)
            clr=QTableWidgetItem('●'); clr.setForeground(QColor(ds.color)); clr.setTextAlignment(Qt.AlignCenter); self.table.setItem(row,1,clr)
            self.table.setItem(row,2,QTableWidgetItem(ds.label))
            self.table.setItem(row,3,QTableWidgetItem(ds.region if ds.kind=='xps' else 'PDF 参考卡' if ds.kind=='reference' else 'XRD'))
            points=QTableWidgetItem(f'{len(ds.x):,}'); points.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter); self.table.setItem(row,4,points)
            self.table.setItem(row,5,QTableWidgetItem(f'{ds.x_range[0]:g}–{ds.x_range[1]:g}'))
            status=QTableWidgetItem('需留意' if ds.warnings else '已就绪'); status.setForeground(QColor('#e99531' if ds.warnings else '#36a371')); self.table.setItem(row,6,status)
            for col in (1,3,4,5,6): self.table.item(row,col).setFlags(Qt.ItemIsEnabled|Qt.ItemIsSelectable)
            for col in range(7): self.table.item(row,col).setToolTip(ds.source+(f'\n{ds.sheet}' if ds.sheet else '')+('\n'+'\n'.join(ds.warnings) if ds.warnings else ''))
            self.table.setRowHeight(row,36)
            if ds.id in selected: self.table.selectRow(row)
        self.table.blockSignals(False)
        if not hasattr(self,'color_connected'):
            self.table.cellDoubleClicked.connect(self.color_clicked); self.color_connected=True
        self.empty.setVisible(not visible); self.side_count.setText(f'{len(self.datasets)} 份数据 · {len({d.source for d in self.datasets})} 个文件')
        self.data_title.setText(f'数据  {len(visible)}')
        for key,b in self.nav.items(): b.setChecked(key==self.filter)
        opts=Options.from_dict(value['options'])
        self.mode.setCurrentIndex(self.mode.findData(opts.mode)); self.connection.setCurrentIndex(self.connection.findData(opts.connection))
        self.auto_range.setChecked(opts.x_min is None); self.xmin.setEnabled(opts.x_min is not None); self.xmax.setEnabled(opts.x_min is not None)
        self.xmin.setText('' if opts.x_min is None else f'{opts.x_min:g}'); self.xmax.setText('' if opts.x_max is None else f'{opts.x_max:g}')
        for w,v in ((self.reverse,opts.reverse_xps),(self.fill,opts.peak_fill),(self.peak_labels,opts.peak_labels),(self.normalize,opts.normalize_xrd),(self.legend,opts.legend),(self.show_y,opts.show_y_values)): w.setChecked(v)
        self.line_width.setValue(opts.line_width); self.template.setText(opts.template); self.xtitle.setText(opts.x_title); self.ytitle.setText(opts.y_title)
        current=self.preview_choice.currentData(); self.preview_choice.blockSignals(True); self.preview_choice.clear(); self.preview_choice.addItem('数据预览',None)
        for history in reversed(value.get('history',[])):
            for graph in history['graphs']: self.preview_choice.addItem(f'Origin · {graph["title"]}',graph)
        if isinstance(current,dict):
            for i in range(1,self.preview_choice.count()):
                if self.preview_choice.itemData(i)['graph']==current['graph']: self.preview_choice.setCurrentIndex(i); break
        self.preview_choice.blockSignals(False); self.refreshing=False; self.update_preview()
        origin=value.get('origin',{})
        self.target_info.setText(f'已连接 · {origin.get("project", "")}' if origin.get('connected') else '尚未连接')
        history=value.get('history',[])
        if len(history)>self.known_history:
            self.status.setText(f'绘图完成 · {len(history[-1]["graphs"])} 张图 · 数据回读校验通过')
        self.known_history=len(history)
        issues=[v for v in value.get('notices',[]) if '没有 XPS 能量表头' not in v]
        if issues: self.message('\n'.join(issues),error=True)

    def widget_options(self):
        value=dict(mode=self.mode.currentData(),connection=self.connection.currentData(),
                   x_min=None if self.auto_range.isChecked() else self.xmin.text().strip(),
                   x_max=None if self.auto_range.isChecked() else self.xmax.text().strip(),
                   reverse_xps=self.reverse.isChecked(),peak_fill=self.fill.isChecked(),peak_labels=self.peak_labels.isChecked(),
                   normalize_xrd=self.normalize.isChecked(),legend=self.legend.isChecked(),show_y_values=self.show_y.isChecked(),
                   line_width=self.line_width.value(),template=self.template.text().strip(),x_title=self.xtitle.text().strip(),y_title=self.ytitle.text().strip())
        return Options.from_dict(value)

    def options_changed(self,*args):
        if self.refreshing: return
        try:
            opts=self.widget_options(); self.submit('options',opts.to_dict()); self.update_preview()
        except DataError as exc: self.validation.setText(str(exc))

    def range_toggled(self,value):
        self.xmin.setEnabled(not value); self.xmax.setEnabled(not value)
        if not self.refreshing:
            if not value and self.datasets and not self.xmin.text():
                selected=self.current_dataset() or self.datasets[0]
                self.xmin.setText(f'{selected.x_range[0]:g}'); self.xmax.setText(f'{selected.x_range[1]:g}')
            self.options_changed()

    def reset_options(self):
        self.submit('options',Options().to_dict(),lambda r:self.message('已恢复默认设置'))

    def set_filter(self,key):
        self.filter=key; self.refresh(self.state)

    def selected_ids(self):
        return [self.table.item(i.row(),0).data(Qt.UserRole) for i in self.table.selectionModel().selectedRows()]

    def current_dataset(self):
        ids=self.selected_ids()
        return next((d for d in self.datasets if ids and d.id==ids[0]),None)

    def item_changed(self,item):
        if self.refreshing: return
        ds_id=self.table.item(item.row(),0).data(Qt.UserRole)
        if item.column()==0: changes={'enabled':item.checkState()==Qt.Checked}
        elif item.column()==2: changes={'label':item.text()}
        else: return
        self.submit('update',dict(id=ds_id,changes=changes))

    def color_clicked(self,row,col):
        if col!=1: return
        ds_id=self.table.item(row,0).data(Qt.UserRole); ds=next(d for d in self.datasets if d.id==ds_id)
        value=QColorDialog.getColor(QColor(ds.color),self,'样品曲线颜色')
        if value.isValid(): self.submit('update',dict(id=ds.id,changes={'color':value.name()}))

    def select_all(self):
        ids=[self.table.item(row,0).data(Qt.UserRole) for row in range(self.table.rowCount())]
        selected=[d for d in self.datasets if d.id in ids]; value=not all(d.enabled for d in selected)
        for d in selected: self.submit('update',dict(id=d.id,changes={'enabled':value}))

    def remove_selected(self):
        ids=self.selected_ids()
        if ids: self.submit('remove',dict(ids=ids),lambda r:self.message(f'已从工作区移除 {len(ids)} 份数据'))

    def move_selected(self,direction):
        selected=set(self.selected_ids())
        if not selected: return
        visible=[self.table.item(row,0).data(Qt.UserRole) for row in range(self.table.rowCount())]
        indices=range(1,len(visible)) if direction<0 else range(len(visible)-2,-1,-1)
        for i in indices:
            j=i+direction
            if visible[i] in selected and visible[j] not in selected: visible[i],visible[j]=visible[j],visible[i]
        iterator=iter(visible); shown=set(visible)
        ids=[next(iterator) if d.id in shown else d.id for d in self.datasets]
        self.submit('reorder',{'ids':ids},lambda r:self.message('已调整绘图顺序'))

    def update_preview(self):
        if self.refreshing: return
        count=sum(d.enabled and d.kind!='reference' for d in self.datasets)
        self.validation.setText(f'已选择 {count} 份图谱 · 使用 Origin 原生模板' if count else '请勾选需要绘制的图谱')
        self.drawbtn.setEnabled(bool(count) and not self.busy and not self.broker.engine.progress)
        if self.preview_choice.currentData(): self.change_preview(); return
        try: opts=self.widget_options()
        except DataError: return
        ids=self.selected_ids()
        visible=[d for d in self.datasets if (self.filter=='all' or d.kind==self.filter) and (not ids or d.id in ids)]
        self.canvas.set_data(visible,opts)
        self.preview_note.setText('数据预览 · 最终排版由 Origin 模板决定')

    def change_preview(self,*args):
        graph=self.preview_choice.currentData()
        if graph:
            self.canvas.set_image(graph.get('preview'))
            w,h=graph['size_inches']; self.preview_note.setText(f'Origin 成图 · 默认页尺寸 {w:g} × {h:g} in · 原生轴标题')
        else: self.update_preview()

    def choose_files(self):
        paths,_=QFileDialog.getOpenFileNames(self,'导入 XPS / XRD 数据','','图谱数据 (*.xlsx *.xlsm *.xls *.xlsb *.txt *.csv *.dat *.xy *.ras);;所有文件 (*)')
        if paths: self.submit('import',dict(paths=paths),self.import_done,busy=True)

    def import_done(self,value):
        amount=len(value['imported'])
        self.message(f'已导入 {amount} 份数据'+(f'；{len(value["issues"])} 项需要处理' if value['issues'] else ''),error=bool(value['issues']))
        self.status.setText(f'已导入 {amount} 份数据')
        if value['issues']:
            for issue in value['issues']:
                if issue['code']=='ambiguous_column': self.resolve_columns(issue)
                else: self.message(issue['message'],error=True)

    def resolve_columns(self,issue):
        details=issue['details']; sheet=details['sheet']; dialog=QDialog(self); dialog.setWindowTitle('选择实测强度列'); dialog.resize(420,190)
        layout=QVBoxLayout(dialog); prompt=label(f'{sheet} 的强度列不明确，请指定实测数据列。'); prompt.setWordWrap(True); layout.addWidget(prompt)
        choice=QComboBox()
        for c in details.get('candidates',[]): choice.addItem(f'第 {c["column"]} 列 · {c["header"] or "无表头"} · {c["unit"] or "无单位"}',c['column'])
        layout.addWidget(choice); controls=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel); controls.accepted.connect(dialog.accept); controls.rejected.connect(dialog.reject); layout.addWidget(controls)
        if dialog.exec()==QDialog.Accepted:
            path=issue.get('path')
            if not path:
                path=next((d.source for d in self.datasets if d.sheet!=sheet and Path(d.source).suffix.lower() in {'.xlsx','.xls'}),None)
            if path: self.submit('import',dict(paths=[path],mapping={sheet:{'y_column':choice.currentData()}}),self.import_done,busy=True)

    def show_details(self):
        ds=self.current_dataset()
        if ds is None:
            self.message('先在数据列表中选中一行'); return
        dialog=QDialog(self); dialog.setWindowTitle(f'数据详情 · {ds.label}'); dialog.resize(600,440); layout=QVBoxLayout(dialog)
        layout.addWidget(label(ds.sheet or ds.label,'section')); info=QTextEdit(); info.setReadOnly(True)
        lines=[f'来源：{ds.source}',f'点数：{len(ds.x):,}',f'范围：{ds.x_range[0]:g}–{ds.x_range[1]:g} {ds.x_unit}','', '识别的数据列：']
        roles={'measured':'实测强度','peak':'拟合分峰','envelope':'拟合包封','background':'背景','sticks':'参考峰'}
        for c in ds.curves: lines.append(f'第 {c.source_column} 列   {roles.get(c.role,c.role)}   {c.label}   [{c.unit}]')
        lines+=['','检查提示：']+(ds.warnings or ['数据检查通过'])
        info.setPlainText('\n'.join(lines)); layout.addWidget(info)
        close=QDialogButtonBox(QDialogButtonBox.Close); close.rejected.connect(dialog.reject); layout.addWidget(close); dialog.exec()

    def draw(self):
        try: opts=self.widget_options()
        except DataError as exc: self.message(str(exc),error=True); return
        self.banner.hide(); self.status.setText('正在检查数据并连接 Origin…')
        self.submit('plot',dict(options=opts.to_dict()),self.plot_done,busy=True)

    def plot_done(self,value):
        self.submit('state',{'full':True},self.refresh)
        graphs=value['graphs']; self.message(f'已在 Origin 创建 {len(graphs)} 张图谱。可在预览菜单查看成图。')
        self.status.setText(f'绘图完成 · {len(graphs)} 张图 · 数据回读校验通过')
        self.target_info.setText(f'已连接 · {value["origin"]["project"]}')
        if len(graphs)==1:
            for i in range(1,self.preview_choice.count()):
                if self.preview_choice.itemData(i)['graph']==graphs[0]['graph']: self.preview_choice.setCurrentIndex(i); break

    def connect_origin(self):
        self.submit('origin_status',dict(connect=True,mode=self.connection.currentData()),self.origin_connected,busy=True)

    def origin_connected(self,value):
        self.target_info.setText(f'已连接 · {value["project"]}'); self.message(f'已连接 Origin，目标工程：{value["project"]}')

    def message(self,text,error=False):
        self.banner.setText(text)
        self.banner.setStyleSheet(f'background:{"#fff0ed" if error else "#edf6ff"}; color:{"#c05b45" if error else "#44759f"}; border:1px solid {"#f7ded6" if error else "#dcecfb"}; border-radius:12px; padding:9px 14px; font-size:12px;')
        self.banner.show()

    def save_workspace(self):
        path,_=QFileDialog.getSaveFileName(self,'保存工作区','图谱工作区.json','工作区 (*.json)')
        if path: self.submit('save',dict(path=path),lambda r:self.message('工作区已保存'))

    def open_workspace(self):
        path,_=QFileDialog.getOpenFileName(self,'打开工作区','','工作区 (*.json)')
        if path: self.submit('load',dict(path=path),lambda r:self.message('工作区已打开'))

    def show_mcp(self):
        dialog=QDialog(self); dialog.setWindowTitle('自动化接口 · MCP'); dialog.resize(600,420); layout=QVBoxLayout(dialog)
        layout.addWidget(label('通过 MCP 自动测试与绘图','section'))
        desc=label('将下面的配置加入支持 MCP 的客户端。打开本软件后，接口会连接当前桌面工作区。可导入数据、调整选项、绘图、核验尺寸及截取本软件预览。'); desc.setWordWrap(True); layout.addWidget(desc)
        if getattr(sys,'frozen',False): command=str(Path(sys.executable).with_name('绘图器-MCP.exe')); args=[]
        else: command=sys.executable; args=[str(Path(__file__).resolve().parents[1]/'mcp_entry.py')]
        config=json.dumps({'mcpServers':{'plotter':{'command':command,'args':args}}},ensure_ascii=False,indent=2)
        text=QTextEdit(); text.setReadOnly(True); text.setPlainText(config); text.setFont(QFont('Consolas',10)); layout.addWidget(text,1)
        copy=button('复制配置',lambda:QApplication.clipboard().setText(config),True); layout.addWidget(copy)
        close=QDialogButtonBox(QDialogButtonBox.Close); close.rejected.connect(dialog.reject); layout.addWidget(close); dialog.exec()

    def external_ui(self,command,args):
        future=Future(); self.requests.requested.emit(command,args,future); return future.result(10)

    def ui_request(self,command,args,future):
        try:
            if command=='focus':
                self.showNormal(); self.raise_(); self.activateWindow(); future.set_result(dict(shown=True)); return
            if command!='snapshot': raise DataError('未知桌面操作')
            if args.get('graph_name'):
                found=False
                for i in range(1,self.preview_choice.count()):
                    if self.preview_choice.itemData(i)['graph']==args['graph_name']:
                        self.preview_choice.setCurrentIndex(i); found=True; break
                if not found: raise DataError('预览菜单中尚未找到这张图谱，请稍后重试')
            path=Path(args['path']).resolve()
            if path.suffix.lower()!='.png': raise DataError('预览保存路径必须以 .png 结尾')
            path.parent.mkdir(parents=True,exist_ok=True)
            pix=QPixmap(self.size()); self.render(pix)
            if not pix.save(str(path),'PNG'): raise DataError('预览图保存失败')
            future.set_result(dict(path=str(path),width=self.width(),height=self.height()))
        except Exception as exc: future.set_exception(exc)

    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self,event):
        paths=[u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths: self.submit('import',dict(paths=paths),self.import_done,busy=True)

    def closeEvent(self,event):
        if self.busy or self.broker.engine.progress:
            self.close_requested=True; self.message('正在完成绘图，完成后会关闭工作台。'); event.ignore(); return
        self.timer.stop(); self.broker.engine.ui=None
        if self.bridge: self.bridge.close()
        self.broker.close(); event.accept()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'data_card'):
            self.data_card.setFixedHeight(min(326,max(260,round(260+(self.height()-700)*.45))))
            self.canvas.setMinimumHeight(230 if self.height()>=830 else 145)

def run_gui(paths=None,recovery=True,snapshot_path=None):
    app=QApplication.instance() or QApplication(sys.argv[:1]); app.setApplicationName('绘图器'); app.setOrganizationName('Plotter')
    if not QFontDatabase.families():
        for name in ('msyh.ttc','msyhbd.ttc','segoeui.ttf','segoeuib.ttf'):
            QFontDatabase.addApplicationFont(str(Path(os.environ.get('WINDIR',r'C:\Windows'))/'Fonts'/name))
    app.setFont(QFont('Microsoft YaHei UI',10))
    broker=Broker(recovery=recovery); bridge=Bridge(broker) if not snapshot_path else None
    if paths: broker.call('import',dict(paths=paths))
    window=MainWindow(broker,bridge); window.show()
    if snapshot_path:
        window.resize(1360,900)
        app.processEvents(); window.ui_request('snapshot',{'path':snapshot_path},future:=Future()); result=future.result()
        window.close(); return result
    return app.exec()
