# chatcoder/core/chatcoder.py
"""
ChatCoder 核心服务类 (ChatCoder Service)
封装了 ChatCoder 的核心业务逻辑，作为 CLI 和底层库 (chatflow, chatcontext, AI manager) 之间的协调者。
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# --- 导入 chatflow 库 (强依赖) ---
try:
    from chatflow.core.workflow_engine import WorkflowEngine as ChatFlowEngine
    from chatflow.core.file_state_store import FileWorkflowStateStore
    from chatflow.core.models import WorkflowDefinition, WorkflowInstanceState, WorkflowInstanceStatus
    CHATFLOW_AVAILABLE = True
except ImportError as e:
    CHATFLOW_AVAILABLE = False
    raise RuntimeError(
        "chatflow library is required for ChatCoder service but is not available. "
        "Please ensure it is installed correctly. "
        "Error: " + str(e)
    ) from e

# --- 导入 chatcontext 库 (强依赖) ---
try:
    from chatcontext.core.manager import ContextManager
    from chatcontext.core.models import ContextRequest
    CHATCONTEXT_AVAILABLE = True
except ImportError as e:
    CHATCONTEXT_AVAILABLE = False
    raise RuntimeError(
        "chatcontext library is required for ChatCoder service but is not available. "
        "Please ensure it is installed correctly. "
        "Error: " + str(e)
    ) from e

# --- 导入 ChatCoder 内部模块 ---
from .manager import AIInteractionManager
from .init import init_project, validate_config
from .context import generate_project_context # 精简后备
from .detector import detect_project_type
# 简化后的 TaskOrchestrator，仅用于 ID 生成
from .orchestrator import TaskOrchestrator

TASKS_DIR = Path.cwd().resolve() / ".chatcoder" / "tasks"

class ChatCoder:
    """
    ChatCoder 核心服务类。
    """

    def __init__(self):
        """
        初始化 ChatCoder 服务。
        强制依赖 chatflow 和 chatcontext。
        """
        self.state_store = FileWorkflowStateStore(base_path=str(TASKS_DIR))
        self.workflow_engine = ChatFlowEngine(state_store=self.state_store)

        Path(TASKS_DIR).mkdir(parents=True, exist_ok=True)

        self.context_manager = ContextManager()
        self.ai_manager = AIInteractionManager()
        # 仅用于 ID 生成
        self.task_orchestrator = TaskOrchestrator()

    # --- 项目初始化 ---
    def initialize_project(self, interactive: bool = True, **config_kwargs) -> bool:
        try:
            if interactive:
                 init_project()
            else:
                raise NotImplementedError("Non-interactive init not yet implemented.")
            return True
        except Exception as e:
            raise RuntimeError(f"Project initialization failed: {e}") from e

    def is_project_initialized(self) -> bool:
        config_file = Path(".chatcoder") / "config.yaml"
        context_file = Path(".chatcoder") / "context.yaml"
        return config_file.exists() and context_file.exists()

    def validate_configuration(self) -> Dict[str, Any]:
        try:
            is_valid = self.is_project_initialized()
            errors = [] if is_valid else ["Config or context file missing."]
            return {"is_valid": is_valid, "errors": errors}
        except Exception as e:
             return {"is_valid": False, "errors": [str(e)]}

    # --- 特性管理 ---
    def start_new_feature(self, description: str, workflow_name: str = "default") -> Dict[str, str]:
        try:
            schema: WorkflowDefinition = self.workflow_engine.load_workflow_schema(workflow_name)
            if not schema.phases:
                 raise ValueError(f"Workflow '{workflow_name}' has no phases defined.")

            feature_id = self.task_orchestrator.generate_feature_id(description)
            # first_phase_def = schema.phases[0] # 可用于返回更多信息

            initial_context = {
                "source": "cli_start",
                "workflow": workflow_name,
                "feature_description": description
            }
            
            instance_id: str = self.workflow_engine.start_workflow_instance(
                workflow_definition=schema,
                initial_context=initial_context,
                feature_id=feature_id
            )

            return {
                "feature_id": feature_id,
                "description": description
                # "instance_id": instance_id, # 可选返回
            }
        except Exception as e:
            raise RuntimeError(f"Failed to start feature: {e}") from e

    # --- 任务管理 ---
    def generate_prompt_for_current_task(self, feature_id: str) -> str:
        try:
            rendered_prompt = self.ai_manager.render_prompt_for_feature_current_task(
                feature_id=feature_id
            )
            return rendered_prompt
        except Exception as e:
            # 区分错误来源
            if "chatflow" in str(e).lower() or "chatcontext" in str(e).lower():
                raise RuntimeError(f"Failed to get context or state for feature {feature_id}: {e}") from e
            else:
                raise RuntimeError(f"Failed to generate prompt for feature {feature_id}: {e}") from e

    def confirm_task_and_advance(self, feature_id: str, ai_response_summary: Optional[str] = None) -> Optional[Dict[str, Any]]:
        try:
            # 1. 获取当前任务 ID
            current_task_id: Optional[str] = self.workflow_engine.get_current_task_id_for_feature(feature_id)
            if not current_task_id:
                 raise ValueError(f"Could not find current active task ID for feature {feature_id}.")

            # 2. 更新状态并触发下一步
            trigger_data = {"summary": ai_response_summary or ""}
            updated_state: Optional[WorkflowInstanceState] = self.workflow_engine.trigger_next_step(
                current_task_id,
                trigger_data=trigger_data
            )

            # 3. 获取推荐
            recommendation: Optional[Dict[str, Any]] = self.workflow_engine.recommend_next_phase(feature_id)
            
            if recommendation and recommendation.get("phase"):
                 return {
                      "next_phase": recommendation["phase"],
                      "reason": recommendation.get("reason", "Standard workflow progression."),
                      "source": recommendation.get("source", "unknown"),
                      "feature_id": feature_id
                 }
            return None # 可能已完成

        except Exception as e:
            error_msg = f"Failed to confirm task and advance for feature {feature_id}"
            if "not found" in str(e).lower():
                raise RuntimeError(f"{error_msg}: No active task found.") from e
            elif "workflow" in str(e).lower():
                 raise RuntimeError(f"{error_msg}: Error interacting with chatflow engine: {e}") from e
            else:
                 raise RuntimeError(f"{error_msg}: An unexpected error occurred: {e}") from e

    def preview_prompt_for_phase(self, phase_name: str, feature_id: str) -> str:
        try:
            # 为预览，可以传递一个特殊标志或使用后备 context
            rendered_prompt = self.ai_manager.render_prompt_for_feature_phase_preview(
                 feature_id=feature_id,
                 phase_name=phase_name,
            )
            return rendered_prompt
        except Exception as e:
            raise RuntimeError(f"Failed to preview prompt for phase '{phase_name}' of feature {feature_id}: {e}") from e

    # --- 查询特性状态 ---
    def get_all_features_status(self) -> List[Dict[str, Any]]:
        try:
            # 假设 chatflow 提供此方法
            all_feature_ids: List[str] = self.workflow_engine.list_all_feature_ids()
            summaries = []
            for fid in all_feature_ids:
                try:
                    detail_status: Dict[str, Any] = self.workflow_engine.get_feature_status(fid, "default")
                    completed_count = detail_status.get("completed_count", 0)
                    total_count = detail_status.get("total_count", 0)
                    description = detail_status.get("description", "N/A")
                    
                    if total_count > 0:
                        if completed_count == total_count:
                            status_str = "completed"
                        elif completed_count > 0:
                            status_str = "in_progress"
                        else:
                            status_str = "pending"
                    else:
                        status_str = "unknown"

                    summaries.append({
                        "feature_id": fid,
                        "description": description,
                        "status": status_str,
                        "progress": f"{completed_count}/{total_count}"
                    })
                except Exception:
                    summaries.append({
                        "feature_id": fid,
                        "description": "Error fetching status",
                        "status": "error",
                        "progress": "N/A"
                    })
            return summaries
        except NotImplementedError:
             raise RuntimeError("chatflow does not support listing all feature IDs.")
        except Exception as e:
            raise RuntimeError(f"Failed to get all features status: {e}") from e

    def get_feature_detail_status(self, feature_id: str) -> Dict[str, Any]:
        try:
             status: Dict[str, Any] = self.workflow_engine.get_feature_status(feature_id, "default")
             return status
        except Exception as e:
            raise RuntimeError(f"Failed to get status for feature {feature_id}: {e}") from e

    # --- 特性删除 ---
    def delete_feature(self, feature_id: str) -> bool:
        try:
            # 假设 state_store 提供 list_instances_by_feature
            workflow_states_data = self.state_store.list_instances_by_feature(feature_id)
            deleted_count = 0
            for state_data in workflow_states_data:
                 instance_id = state_data.get("instance_id")
                 if instance_id:
                      task_file_path = Path(self.state_store.base_path) / f"{instance_id}.json"
                      if task_file_path.exists():
                           try:
                                task_file_path.unlink()
                                deleted_count += 1
                           except Exception:
                                pass # Log warning?
            return deleted_count > 0
        except Exception as e:
             raise RuntimeError(f"Failed to delete feature {feature_id}: {e}") from e

    # --- 辅助方法 ---
    def list_available_workflows(self) -> List[str]:
        workflows_dir = Path("ai-prompts") / "workflows"
        if not workflows_dir.exists():
            return []
        return [f.stem for f in workflows_dir.glob("*.yaml")]

    def get_project_context_snapshot(self) -> Dict[str, Any]:
        """获取项目静态上下文（后备）"""
        try:
            # 使用精简后的 generate_project_context
            return generate_project_context()
        except Exception as e:
             raise RuntimeError(f"Failed to get project context snapshot: {e}") from e
