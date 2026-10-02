from __future__ import annotations
import json, sys, os
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from .bridge import Gateway
from .models import DataError
from . import __version__

def create_server(gateway):
    server=FastMCP('绘图器',log_level='WARNING',instructions='绘图器 1.0：统一 XPS/XRD 绘图。优先连接已打开的桌面窗口。先导入与 validate_plot，再 plot_in_origin。保持 Origin 模板尺寸与原生轴标题；不提供任意脚本执行。')
    # Pin the advertised application version rather than the SDK version.
    server._mcp_server.version=__version__
    ro=ToolAnnotations(readOnlyHint=True,destructiveHint=False)
    rw=ToolAnnotations(readOnlyHint=False,destructiveHint=False)

    @server.tool(annotations=ro)
    def get_workspace() -> dict:
        """查看数据、勾选状态、绘图选项和成图记录。"""
        return gateway.call('state')

    @server.tool(annotations=rw)
    def import_files(paths:list[str], mapping:dict | None=None) -> dict:
        """导入本地 XPS 表格、XRD 文本或 PDF 参考卡；同一来源重复导入会更新，不会叠出重复条目。mapping 示例：{\"Sheet1\":{\"y_column\":3}}。"""
        return gateway.call('import',dict(paths=paths,mapping=mapping))

    @server.tool(annotations=rw)
    def update_dataset(dataset_id:str, label:str | None=None, color:str | None=None, enabled:bool | None=None) -> dict:
        """修改样品名、#RRGGBB 颜色或是否参与绘图。"""
        changes={k:v for k,v in dict(label=label,color=color,enabled=enabled).items() if v is not None}
        return gateway.call('update',dict(id=dataset_id,changes=changes))

    @server.tool(annotations=rw)
    def set_plot_options(options:dict) -> dict:
        """设置 mode: separate/stack/overlay，connection: existing/new，x_min/x_max，reverse_xps，normalize_xrd，peak_fill，peak_labels，legend，line_width，x_title，y_title，show_y_values，template。自动范围用 x_min=null,x_max=null。"""
        return gateway.call('options',options)

    @server.tool(annotations=ro)
    def validate_plot(dataset_ids:list[str] | None=None, options:dict | None=None) -> dict:
        """检查选中的数据和范围，返回拟创建的图页；不会连接或修改 Origin。"""
        return gateway.call('validate',dict(ids=dataset_ids,options=options or {}))

    @server.tool(annotations=rw)
    def plot_in_origin(dataset_ids:list[str] | None=None, options:dict | None=None, preview_directory:str | None=None) -> dict:
        """创建可编辑的原生 Origin 工作簿和图页。失败时清理本次新增页。可选输出 PNG 预览。已有工程不会被保存、重置或关闭。"""
        args=dict(ids=dataset_ids,options=options or {})
        if preview_directory: args['preview_dir']=preview_directory
        return gateway.call('plot',args)

    @server.tool(annotations=ro)
    def origin_status() -> dict:
        """读取当前连接的 Origin 进程、工程和版本状态。"""
        return gateway.call('origin_status')

    @server.tool(annotations=ro)
    def audit_graph(graph_name:str) -> dict:
        """回读工作台创建图页的实际尺寸、绘图区、原生轴标题及字体，用于回归测试。"""
        return gateway.call('audit',dict(graph=graph_name))

    @server.tool(annotations=rw)
    def open_origin_graph(graph_name:str) -> dict:
        """在 Origin 中显示本工作区创建的图页。"""
        return gateway.call('activate_graph',dict(graph=graph_name))

    @server.tool(annotations=rw)
    def save_workspace(path:str) -> dict:
        """保存为 .json 工作区；包含导入快照、名称、颜色和选项。"""
        return gateway.call('save',dict(path=path))

    @server.tool(annotations=rw)
    def load_workspace(path:str) -> dict:
        """打开先前保存的 .json 工作区。"""
        return gateway.call('load',dict(path=path))

    @server.tool(annotations=ro)
    def capture_app_preview(path:str, graph_name:str | None=None) -> dict:
        """通过工作台自身渲染接口保存窗口 PNG，无需 computer use；需要桌面窗口已打开。可指定工作区成图名称以切换预览。"""
        return gateway.call('ui_snapshot',dict(path=path,graph_name=graph_name))

    return server

def run(headless=False):
    gateway=Gateway(headless)
    original=sys.stdin,sys.stdout
    # The SDK owns its wrappers. Duplicating file descriptors keeps PyInstaller's
    # shutdown flush from accessing buffers closed by the stdio transport.
    stdin=open(os.dup(original[0].fileno()),'r',encoding='utf-8',errors='replace')
    stdout=open(os.dup(original[1].fileno()),'w',encoding='utf-8',buffering=1)
    sys.stdin,sys.stdout=stdin,stdout
    try: create_server(gateway).run(transport='stdio')
    finally:
        sys.stdin,sys.stdout=original
        stdin.close(); stdout.close(); gateway.close()
