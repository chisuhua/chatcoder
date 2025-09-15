# chatcoder/core/chatcoder.py
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

try:
    from chatflow.core.workflow_engine import WorkflowEngine as WorkFlowEngine
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
from .context import generate_project_context_from_data # 精简后备
from .detector import detect_project_type
from .orchestrator import TaskOrchestrator

TASKS_DIR = Path.cwd().resolve() / ".chatcoder" / "tasks"

class ChatCoder:
    def __init__(self, config_data: Dict[str, Any], context_data: Dict[str, Any]):
        """
        初始化 ChatCoder 服务。
        强制依赖 chatflow 和 chatcontext。
        """
        self.config_data = config_data
        self.context_data = context_data
        # --- chatflow 初始化 ---
        self.state_store = FileWorkflowStateStore(base_dir=TASKS_DIR)
        self.workflow_engine = WorkFlowEngine(state_store=self.state_store)
        TASKS_DIR.mkdir(parents=True, exist_ok=True)

        # --- chatcontext 初始化 ---
        self.context_manager = ContextManager()

        # --- ChatCoder 内部模块 ---
        self.ai_manager = AIInteractionManager()
        self.task_orchestrator = TaskOrchestrator()

        # --- 预生成静态项目上下文 (后备) ---
        # 如果 chatcontext 不可用，可以使用这个
        self._static_project_context = generate_project_context_from_data(
            config_data=self.config_data,
            context_data=self.context_data
        )


    # --- 特性管理 ---
    def start_new_feature(self, description: str, workflow_name: str = "default") -> Dict[str, str]:
        try:
            schema: dict = self.workflow_engine.load_workflow_schema(workflow_name)
            if not schema.get("phases"):
                 raise ValueError(f"Workflow '{workflow_name}' has no phases defined.")

            feature_id = self.task_orchestrator.generate_feature_id(description)

            initial_context = {
                "source": "cli_start",
                "workflow": workflow_name,
                "feature_description": description
            }
            
            instance_id: str = self.workflow_engine.start_workflow_instance(
                workflow_schema=schema,
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

    def confirm_task_and_advance(self, 
                                 feature_id: str, 
                                 ai_response_summary: Optional[str] = None) -> Optional[Dict[str, Any]]:
        try:
            # 1. 获取当前任务 ID
            current_task_id: Optional[str] = self.state_store.get_current_task_id_for_feature(feature_id)
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


    # --- 查询特性状态 ---
    def get_all_features_status(self) -> List[Dict[str, Any]]:
        try:
            # 假设 chatflow 提供此方法
            all_feature_ids: List[str] = self.state_store.list_all_feature_ids()
            import pdb
            pdb.set_trace()
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

    # Placeholder for apply_task
    def apply_task(self, feature_id: str, ai_response: str) -> bool:
        """
        [Placeholder] Apply an AI response to the current task of a feature.

        This method would typically:
        1. Find the current active task for the given feature_id.
        2. Parse the ai_response content (e.g., looking for file changes).
        3. Apply the changes to the local file system.
        4. Update the task state (e.g., mark as 'applied' or 'needs_review').

        Args:
            feature_id (str): The ID of the feature.
            ai_response (str): The raw text response from the AI.

        Returns:
            bool: True if the application was successful, False otherwise.
        """
        # TODO: Implement the logic to apply the AI response.
        # This is a placeholder implementation.
        print(f"[PLACEHOLDER] Applying AI response to feature '{feature_id}'...")
        print(f"[PLACEHOLDER] AI Response Preview (first 200 chars): {ai_response[:200]}...")
        # Example steps (not implemented):
        # 1. current_task = self._find_current_active_task(feature_id)
        # 2. changeset = parse_ai_response_for_changes(ai_response)
        # 3. for change in changeset.changes:
        #       if change.operation == "create" or change.operation == "modify":
        #           Path(change.file_path).write_text(change.new_content, encoding='utf-8')
        # 4. self._update_task_status(current_task.instance_id, "applied") # Or use chatflow
        # 5. return True
        return True # Placeholder return

