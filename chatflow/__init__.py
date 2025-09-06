# chatflow/__init__.py
"""
ChatFlow 库 - 用于管理 AI 辅助软件开发的工作流。
"""

# 从 core 模块导入主要接口
from .core.engine import IWorkflowEngine
# from .core.state import IWorkflowStateStore
# from .core.models import WorkflowDefinition, WorkflowInstanceStatus # 如果有

# 定义包的公开 API
__all__ = [
    "IWorkflowEngine",
    # "IWorkflowStateStore",
    # "WorkflowDefinition",
    # "WorkflowInstanceStatus",
]
