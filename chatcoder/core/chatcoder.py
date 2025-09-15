# chatcoder/core/chatcoder.py
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import asdict

# === 强依赖 ChatFlow v1.1.2 ===
try:
    from chatflow.core.workflow_engine import WorkflowEngine
    from chatflow.core.models import WorkflowStatusInfo, WorkflowStartResult, WorkflowState
    from chatflow.storage.file_state_store import FileStateStore
    CHATFLOW_AVAILABLE = True
except ImportError as e:
    CHATFLOW_AVAILABLE = False
    raise RuntimeError(f"ChatFlow v1.1.2 is required but not available: {e}")

# === 导入内部模块 ===
from .detector import detect_project_type
from .orchestrator import TaskOrchestrator
from .ai_manager import AIInteractionManager
from .models import ChangeSet
from ..utils.console import console, success, error, warning, info, confirm

TASKS_DIR = Path(".chatcoder") / "workflow_instances"

class ChatCoder:
    def __init__(self, storage_dir: str = str(TASKS_DIR)):
        self.storage_dir = storage_dir
        TASKS_DIR.mkdir(parents=True, exist_ok=True)
        
        self.workflow_engine = WorkflowEngine(storage_dir=self.storage_dir)
        self.ai_manager = AIInteractionManager()
        self.task_orchestrator = TaskOrchestrator()
        success("ChatCoder v1.1 initialized successfully.")

    # ==================== 特性/实例生命周期 ====================
    
    def start_new_feature(
        self, 
        description: str, 
        workflow_name: str = "default",
        user_id: Optional[str] = None
    ) -> Dict[str, str]:
        try:
            feature_id = self.task_orchestrator.generate_feature_id(description)
            project_type = detect_project_type()
            automation_level = self.task_orchestrator.generate_automation_level()
            
            initial_context = {
                "user_request": description,
                "project_type": project_type,
            }
            
            meta = {"user_id": user_id or "unknown", "automation_level": automation_level}
            
            result: WorkflowStartResult = self.workflow_engine.start_workflow_instance(
                schema_name=workflow_name,
                initial_context=initial_context,
                feature_id=feature_id,
                meta=meta
            )
            
            success(f"✅ Feature '{description}' started! (ID: {feature_id}, Instance: {result.instance_id})")
            return {
                "feature_id": feature_id, 
                "description": description, 
                "instance_id": result.instance_id
            }
            
        except Exception as e:
            error_msg = f"❌ Failed to start feature '{description}': {e}"
            error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def confirm_task_and_advance(
        self, 
        instance_id: str, 
        ai_response_summary: Optional[str] = None,
        user_confirmation: bool = True
    ) -> Optional[Dict[str, Any]]:
        try:
            state = self.workflow_engine.get_workflow_state(instance_id)
            if not state:
                raise ValueError(f"Instance {instance_id} not found")
            
            if user_confirmation:
                preview_state = self.workflow_engine.trigger_next_step(
                    instance_id=instance_id,
                    trigger_data={"summary": ai_response_summary},
                    dry_run=True
                )
                next_phase = preview_state.current_phase
                info(f"🔄 Next step will be: '{next_phase}'. Proceed?")
                if not confirm("Confirm advance?", default=True):
                    warning("Advance cancelled by user.")
                    return None
            
            updated_state = self.workflow_engine.trigger_next_step(
                instance_id=instance_id,
                trigger_data={"summary": ai_response_summary},
                meta={"user_confirmed": user_confirmation}
            )
            
            next_phase_info = {
                "next_phase": updated_state.current_phase, 
                "status": updated_state.status.value,
                "feature_id": updated_state.feature_id
            }
            
            success(f"✅ Task advanced. Current phase: {updated_state.current_phase}")
            return next_phase_info
            
        except Exception as e:
            error(f"❌ Failed to advance instance {instance_id}: {e}")
            raise
    
    # ==================== 查询接口 ====================
    
    def list_all_features(self) -> List[str]:
        """列出所有特性ID"""
        try:
            return self.workflow_engine.state_store.list_features()
        except Exception as e:
            error(f"Failed to list features: {e}")
            return []

    def get_feature_instances(self, feature_id: str) -> List[Dict[str, Any]]:
        """获取与 feature_id 关联的所有实例的精简状态"""
        try:
            instance_ids = self.workflow_engine.state_store.list_instances_by_feature(feature_id)
            summaries = []
            for iid in instance_ids:
                status_info = self.workflow_engine.get_workflow_status_info(iid)
                if status_info:
                   summaries.append(asdict(status_info))
            return summaries
        except Exception as e:
            error(f"Failed to get instances for feature {feature_id}: {e}")
            return []

    def get_active_instance_for_feature(self, feature_id: str) -> Optional[str]:
        """获取 feature_id 关联的当前活动实例 ID"""
        try:
            return self.workflow_engine.state_store.get_current_task_id_for_feature(feature_id)
        except NotImplementedError:
             instances_info = self.get_feature_instances(feature_id)
             active_ones = [info for info in instances_info if info.get("status", "").strip() == "running"]
             if active_ones:
                 return active_ones[0].get("instance_id")
             return None
        except Exception as e:
             error(f"Failed to get active instance for feature {feature_id}: {e}")
             return None

    
    def get_instance_detail_status(self, instance_id: str) -> Dict[str, Any]:
        """获取实例的详细状态"""
        try:
            state = self.workflow_engine.get_workflow_state(instance_id)
            if not state:
                raise ValueError(f"Instance {instance_id} not found")
            return asdict(state)
        except Exception as e:
            error(f"Failed to get detail status for {instance_id}: {e}")
            raise
    
    # ==================== 提示词相关 ====================
    
    def generate_prompt_for_current_task(self, instance_id: str) -> str:
        """为当前任务生成提示词"""
        try:
            state = self.workflow_engine.get_workflow_state(instance_id)
            if not state:
                raise ValueError(f"Instance {instance_id} not found")
            
            prompt = self.ai_manager.render_prompt_for_feature_current_task(
                instance_id=instance_id,
                workflow_state=state
            )
            return prompt
        except Exception as e:
            error(f"Failed to generate prompt for {instance_id}: {e}")
            raise
    
    def preview_prompt_for_phase(self, instance_id: str, phase_name: str, task_description: str) -> str:
        """预览特定阶段的提示词"""
        try:
            return self.ai_manager.preview_prompt_for_phase(
                instance_id=instance_id,
                phase_name=phase_name,
                task_description=task_description
            )
        except Exception as e:
            error(f"Failed to preview prompt for phase '{phase_name}': {e}")
            raise
    
    # ==================== 辅助方法 ====================
    def delete_feature(self, feature_id: str) -> bool:
        """删除与 feature_id 关联的所有实例"""
        try:
            instance_ids = self.workflow_engine.state_store.list_instances_by_feature(feature_id)
            deleted_count = 0
            for instance_id in instance_ids:
                 instance_file_path = Path(self.workflow_engine.state_store.instances_dir) / f"{instance_id}.json"
                 instance_dir_path = Path(self.workflow_engine.state_store.instances_dir) / instance_id
                 try:
                     if instance_file_path.exists():
                         instance_file_path.unlink()
                     if instance_dir_path.exists() and instance_dir_path.is_dir():
                         import shutil
                         shutil.rmtree(instance_dir_path)
                     deleted_count += 1
                 except Exception as e_del:
                     error(f"Warning: Failed to delete instance {instance_id} for feature {feature_id}: {e_del}")
            return deleted_count > 0
        except Exception as e:
             error(f"Failed to delete feature {feature_id}: {e}")
             return False
