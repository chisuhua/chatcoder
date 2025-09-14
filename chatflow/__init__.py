# chatflow/__init__.py
"""
ChatFlow 库 - 用于管理 AI 辅助软件开发的工作流。
"""

# 从 core 模块导入主要接口
from .core.engine import IWorkflowEngine
from .core.workflow_engine import WorkflowEngine

engine = WorkflowEngine()

def init(storage_dir: str = ".chatflow") -> WorkflowEngine:
    """初始化ChatFlow引擎"""
    global engine
    engine = WorkflowEngine(storage_dir=storage_dir)
    return engine

__all__ = ['WorkflowEngine', 'init', 'engine']

