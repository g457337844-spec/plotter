import os,time,json
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from concurrent.futures import Future
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from studio.gui import MainWindow
from studio.service import Broker

ROOT=Path(__file__).resolve().parents[1]
XPS=r'E:\Desktop\小图\第二体系\表征\XPS\TC.xlsx'
XRD=r'E:\Desktop\表征\第二体系\XRD\T TC C CAG\高树良-XRD-5°-四个样品\1.txt'

@pytest.fixture
def window():
    app=QApplication.instance() or QApplication([])
    if not QFontDatabase.families():
        for name in ('msyh.ttc','segoeui.ttf','msyhbd.ttc'):
            QFontDatabase.addApplicationFont(str(Path(r'C:\Windows\Fonts')/name))
    broker=Broker(recovery=False)
    assert len(broker.call('import',dict(paths=[XPS,XRD]))['imported'])==6
    win=MainWindow(broker); win.resize(1360,900); win.show(); app.processEvents()
    yield win
    win.close(); app.processEvents()

def pump(win,predicate):
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        QApplication.processEvents(); win.poll()
        if predicate(): return
        QTest.qWait(25)
    assert predicate()

def test_filter_and_preview_switch_without_losing_selection(window):
    window.nav['xrd'].click(); assert window.table.rowCount()==1
    assert window.canvas.datasets[0].kind=='xrd'
    window.nav['all'].click(); assert window.table.rowCount()==6
    assert sum(d.enabled for d in window.datasets)==6

def test_rename_and_checkbox_use_shared_service(window):
    window.table.item(0,2).setText('TC 改名')
    window.table.item(0,0).setCheckState(Qt.Unchecked)
    pump(window,lambda:window.broker.engine.datasets[0].label=='TC 改名' and not window.broker.engine.datasets[0].enabled)
    pump(window,lambda:window.datasets[0].label=='TC 改名' and not window.datasets[0].enabled)
    assert window.drawbtn.isEnabled()

def test_invalid_range_stays_visible_and_cannot_reach_origin(window):
    window.auto_range.setChecked(False); window.xmin.setText('10'); window.xmax.setText('1e999')
    window.draw()
    assert window.banner.isVisible() and '有限' in window.banner.text()
    assert window.broker.engine.session.app is None

def test_all_unchecked_disables_plot(window):
    window.select_all()
    pump(window,lambda:not any(d.enabled for d in window.datasets))
    assert not window.drawbtn.isEnabled()

def test_small_and_large_layout_and_native_snapshot(window):
    out=ROOT/'validation'; out.mkdir(exist_ok=True)
    for name,size in [('ui_large',(1360,900)),('ui_small',(1040,700))]:
        window.resize(*size); QApplication.processEvents()
        future=Future(); window.ui_request('snapshot',dict(path=str(out/f'{name}.png')),future)
        result=future.result(); assert result['width']==size[0]
        assert window.drawbtn.isVisible() and window.drawbtn.geometry().width()>150
        assert window.table.viewport().height()>=3*36
    window.advanced.click(); QApplication.processEvents(); assert window.advanced_box.isVisible()

def test_mcp_bridge_state_change_refreshes_gui(window):
    from studio.bridge import Bridge,remote_call
    bridge=Bridge(window.broker)
    try:
        remote_call(bridge.info,'options',{'normalize_xrd':True})
        pump(window,lambda:window.normalize.isChecked())
        ds_id=window.datasets[-1].id
        remote_call(bridge.info,'update',dict(id=ds_id,changes={'label':'自动化样品'}))
        pump(window,lambda:window.datasets[-1].label=='自动化样品')
    finally: bridge.close()

def completed_plot(window):
    graph=dict(graph='SGPreview',title='TC · O1s',preview='',size_inches=[10.72,8.205])
    value=window.broker.call('state',{'full':True})
    value['history']=[dict(graphs=[graph])]
    value['origin']=dict(connected=True,project='UNTITLED')
    window.refresh(value)
    return graph

def test_external_plot_completion_updates_visible_status(window):
    window.status.setText('正在绘制 6/6')
    completed_plot(window)
    assert '绘图完成' in window.status.text()
    assert '已连接' in window.target_info.text()

def test_completed_preview_still_obeys_checkbox_selection(window):
    completed_plot(window); window.preview_choice.setCurrentIndex(1)
    window.select_all()
    pump(window,lambda:not any(d.enabled for d in window.datasets))
    assert not window.drawbtn.isEnabled()

def test_external_plot_disables_controls_until_complete(window):
    window.broker.engine.progress='正在绘制 1/6'; window.poll()
    assert not window.drawbtn.isEnabled() and not window.importbtn.isEnabled()
    window.broker.engine.progress=''; window.poll()
    assert window.drawbtn.isEnabled() and window.importbtn.isEnabled()
