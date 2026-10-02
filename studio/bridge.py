from __future__ import annotations
import hmac, json, os, secrets, threading, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .models import DataError
from .service import Broker, app_data, atomic_json
from . import __version__

ALLOWED={'state','import','excel_live','update','remove','reorder','clear','options','validate','plot','origin_status',
         'origin_disconnect','audit','activate_graph','save','load','ui_snapshot','ui_focus'}

class Bridge:
    def __init__(self, broker:Broker):
        self.token=secrets.token_urlsafe(32); token=self.token
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                if self.path!='/api' or not hmac.compare_digest(self.headers.get('Authorization',''),f'Bearer {token}'):
                    self.send_error(403); return
                try:
                    length=int(self.headers.get('Content-Length','0'))
                    if not 0<length<=2_000_000: raise DataError('请求大小无效')
                    value=json.loads(self.rfile.read(length)); command=value.get('command')
                    if command not in ALLOWED: raise DataError('不支持的操作')
                    result=broker.call(command,value.get('args',{}),timeout=240)
                    payload=dict(ok=True,result=result)
                except Exception as exc:
                    payload=dict(ok=False,error=str(exc),code=getattr(exc,'code','operation_failed'),details=getattr(exc,'details',{}))
                raw=json.dumps(payload,ensure_ascii=False,allow_nan=False).encode('utf-8')
                self.send_response(200); self.send_header('Content-Type','application/json; charset=utf-8')
                self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.server.daemon_threads=True
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True,name='OriginStudio-Bridge'); self.thread.start()
        self.path=app_data()/'bridge.json'
        self.info=dict(port=self.server.server_port,token=self.token,pid=os.getpid(),version=__version__)
        atomic_json(self.path,self.info)

    def close(self):
        self.server.shutdown(); self.server.server_close()
        try:
            if json.loads(self.path.read_text(encoding='utf-8')).get('token')==self.token: self.path.unlink()
        except Exception: pass

def remote_call(info,command,args):
    port=info.get('port')
    if type(port) is not int or not 1<=port<=65535: raise DataError('桌面接口地址无效')
    data=json.dumps(dict(command=command,args=args or {}),ensure_ascii=False,allow_nan=False).encode('utf-8')
    req=urllib.request.Request(f'http://127.0.0.1:{port}/api',data,headers={'Authorization':f'Bearer {info["token"]}','Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=240 if command=='plot' else 12) as response: value=json.load(response)
    if not value.get('ok'): raise DataError(value.get('error','桌面操作失败'),value.get('code'),value.get('details'))
    return value['result']

class Gateway:
    def __init__(self,headless=False):
        self.broker=None; self.remote=None
        if not headless:
            try:
                info=json.loads((app_data()/'bridge.json').read_text(encoding='utf-8'))
                remote_call(info,'state',{})
                self.remote=info
            except Exception: pass
        if self.remote is None: self.broker=Broker(recovery=False)

    def call(self,command,args=None):
        return remote_call(self.remote,command,args) if self.remote else self.broker.call(command,args)

    def close(self):
        if self.broker: self.broker.close()
