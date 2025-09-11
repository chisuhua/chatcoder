# chatcoder/core/engine.py
"""
ChatCoder 核心服务 - 工作流引擎 (WorkflowEngine) [精简适配器]
负责加载工作流定义。
[注意] 此类现在是 chatflow 库的精简适配器。
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List

# 导入 chatflow 库
try:
    from chatflow.core.workflow_engine import WorkflowEngine as ChatFlowEngine
    from chatflow.core.file_state_store import FileWorkflowStateStore
    from chatflow.core.models import WorkflowDefinition
    CHATFLOW_AVAILABLE = True
except ImportError as e:
    CHATFLOW_AVAILABLE = False
    ChatFlowEngine = None
    FileWorkflowStateStore = None
    WorkflowDefinition = Dict # Fallback type

# 项目根目录和模板目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "ai-prompts"

def get_workflow_path() -> Path:
    """获取工作流定义文件的目录路径"""
    return TEMPLATES_DIR / "workflows"

class WorkflowEngine:
    """
    工作流引擎 (精简适配器)，用于管理 ChatCoder 的工作流定义加载。
    """

    def __init__(self):
        """
        初始化工作流引擎 (适配器)。
        """
        if not CHATFLOW_AVAILABLE:
            raise RuntimeError("chatflow library is required for WorkflowEngine adapter but is not available.")
        # 不再直接实例化 chatflow 引擎，由 ChatCoder 服务管理

    def get_workflow_path(self) -> Path:
        """
        获取工作流定义文件的目录路径。
        """
        return get_workflow_path()

    def load_workflow_schema(self, name: str = "default") -> dict:
        """
        加载指定名称的工作流模式（YAML 定义）。
        优先尝试使用 chatflow 加载，如果失败则回退到旧的文件加载逻辑。
        """
        # --- 旧逻辑 (作为后备或 chatflow 不直接提供 schema 加载时) ---
        # 这是加载 YAML 文件定义的标准方式
        custom_path = self.get_workflow_path() / f"{name}.yaml"
        if custom_path.exists():
            content = custom_path.read_text(encoding="utf-8")
            return yaml.safe_load(content)
        
        raise ValueError(f"Workflows schema not found: {name}. Looked in {custom_path}")

    # --- 以下方法已移除 ---
    # 因为状态管理、特性状态聚合、阶段推荐等功能已由 chatflow 和 ChatCoder 服务处理
    # def get_feature_status(self, ...): ...
    # def recommend_next_phase(self, ...): ...
    # def get_phase_order(self, ...): ...
    # def get_next_phase(self, ...): ...
    # def determine_next_phase(self, ...): ...
    # def start_workflow_instance(self, ...): ...
    # def trigger_next_step(self, ...): ...
