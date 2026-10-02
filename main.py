from __future__ import annotations
import argparse, json, os, sys, multiprocessing

def main():
    parser=argparse.ArgumentParser(description='绘图器 1.0 · XPS / XRD')
    parser.add_argument('--mcp',action='store_true',help='运行标准 stdio MCP 服务')
    parser.add_argument('--headless',action='store_true',help='MCP 使用独立工作区')
    parser.add_argument('--no-recovery',action='store_true',help='不恢复上次桌面工作区')
    parser.add_argument('--ui-snapshot',help='在离屏窗口渲染 PNG，用于界面回归检查')
    parser.add_argument('--open',nargs='*',default=[],help='导入指定数据文件')
    args=parser.parse_args()
    if args.mcp:
        from studio.mcp_server import run
        return run(args.headless)
    if args.ui_snapshot: os.environ['QT_QPA_PLATFORM']='offscreen'
    mutex=None
    if not args.ui_snapshot:
        import win32event,win32api,winerror
        mutex=win32event.CreateMutex(None,False,'Local\\Plotter.Desktop.1')
        if win32api.GetLastError()==winerror.ERROR_ALREADY_EXISTS:
            from studio.bridge import remote_call
            from studio.service import app_data
            try:
                info=json.loads((app_data()/'bridge.json').read_text(encoding='utf-8'))
                if args.open: remote_call(info,'import',{'paths':args.open})
                remote_call(info,'ui_focus',{})
            except Exception: pass
            return 0
    from studio.gui import run_gui
    result=run_gui(args.open,not args.no_recovery and not args.ui_snapshot,args.ui_snapshot)
    if args.ui_snapshot and sys.stdout: print(json.dumps(result,ensure_ascii=True))
    return 0 if args.ui_snapshot else result

if __name__=='__main__':
    multiprocessing.freeze_support()
    try: raise SystemExit(main())
    except Exception:
        import traceback
        from studio.service import app_data
        path=app_data()/'startup_error.log'; path.write_text(traceback.format_exc(),encoding='utf-8')
        if sys.stderr: traceback.print_exc()
        if getattr(sys,'frozen',False) and '--mcp' not in sys.argv:
            from PySide6.QtWidgets import QApplication,QMessageBox
            app=QApplication.instance() or QApplication([])
            QMessageBox.critical(None,'绘图器启动失败',f'软件未能启动。诊断记录已保存到：\n{path}')
        raise SystemExit(1)
