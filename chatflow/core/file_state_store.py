# chatflow/core/file_state_store.py
"""
ChatFlow 核心实现 - 文件状态存储 (FileWorkflowStateStore)
提供基于文件系统的工作流实例状态存储实现。
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from .state import IWorkflowStateStore

# --- 默认配置 ---
# 状态文件存储的默认目录
DEFAULT_STATE_DIR = Path(".chatcoder") / "workflow_instances"

class FileWorkflowStateStore(IWorkflowStateStore):
    """
    基于文件系统的工作流状态存储实现。
    将每个工作流实例的状态保存为一个独立的 JSON 文件。
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """
        初始化文件状态存储。

        Args:
            base_dir (Optional[Path]): 状态文件存储的基目录。
                                     如果未提供，则使用默认目录 '.chatcoder/workflow_instances'。
        """
        self.base_dir = base_dir or DEFAULT_STATE_DIR
        self._ensure_base_dir()

    def _ensure_base_dir(self) -> None:
        """确保基目录存在。"""
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_state_file_path(self, instance_id: str) -> Path:
        """
        获取指定实例 ID 对应的状态文件路径。

        Args:
            instance_id (str): 工作流实例 ID。

        Returns:
            Path: 状态文件的完整路径。
        """
        # 为了安全，可以对 instance_id 做一些清理，防止路径遍历
        # 例如，确保它不包含 '/' 或 '..' 等
        safe_instance_id = "".join(c for c in instance_id if c.isalnum() or c in ('-', '_')).rstrip()
        if not safe_instance_id:
             raise ValueError("Invalid instance_id")
        return self.base_dir / f"{safe_instance_id}.json"

    def save_state(self, instance_id: str, state_data: Dict[str, Any]) -> None:
        """
        保存工作流实例的状态到 JSON 文件。
        """
        state_file = self._get_state_file_path(instance_id)
        
        # 确保目录存在（虽然 _ensure_base_dir 已经做了，但作为防御性编程）
        state_file.parent.mkdir(parents=True, exist_ok=True) 
        
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # 可以记录日志
            raise IOError(f"Failed to save state for instance {instance_id} to {state_file}: {e}")

    def load_state(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """
        从 JSON 文件加载指定工作流实例的状态。
        """
        state_file = self._get_state_file_path(instance_id)
        if not state_file.exists():
            return None

        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            # 可以记录警告日志
            # print(f"Warning: Failed to load state for instance {instance_id} from {state_file}: {e}")
            return None

    # --- 扩展方法：支持按特性 ID 查询 (为 workflow_engine.py 中的 _load_tasks_for_feature 提供基础) ---
    # 注意：这超出了 IWorkflowStateStore 的原始接口，但对实现功能至关重要。
    # 可以通过继承 IWorkflowStateStore 并添加新方法，或者在 FileWorkflowStateStore 中作为特有方法实现。
    # 这里作为 FileWorkflowStateStore 的特有方法实现。

    def list_all_state_files(self) -> List[Path]:
        """
        (FileWorkflowStateStore 特有) 列出基目录下所有状态文件的路径。
        """
        if not self.base_dir.exists():
            return []
        return list(self.base_dir.glob("*.json"))

    def list_states_by_feature(self, feature_id: str) -> List[Dict[str, Any]]:
        """
        (FileWorkflowStateStore 特有) 根据特性 ID 加载所有相关实例的状态。
        通过扫描所有状态文件并检查其内容实现。
        注意：这在大型项目中可能效率不高。
        """
        matching_states = []
        all_state_files = self.list_all_state_files()
        
        for state_file in all_state_files:
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                # 检查状态数据中是否包含 feature_id 且匹配
                # 这要求保存的状态数据中包含 'feature_id' 字段
                if state_data.get("feature_id") == feature_id:
                    matching_states.append(state_data)
            except (json.JSONDecodeError, IOError, KeyError):
                # 跳过损坏的或不包含 feature_id 的文件
                continue
        
        return matching_states

    def list_instances_by_feature(self, feature_id: str) -> List[Dict[str, Any]]:
        """
        (FileWorkflowStateStore 特有) 根据特性 ID 加载所有相关实例的状态。
        通过扫描所有状态文件并检查其内容实现。
        注意：这在大型项目中可能效率不高。
        """
        matching_states = []
        # 确保基目录存在，如果不存在则直接返回空列表
        if not self.base_dir.exists():
            return matching_states

        # 遍历基目录下所有 .json 文件
        for state_file in self.base_dir.glob("*.json"):
            try:
                # 打开并加载 JSON 文件内容
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                # 检查状态数据中是否包含 'feature_id' 字段且其值与查询的 feature_id 匹配
                # 这要求在保存状态时，必须将 feature_id 包含在 state_data 字典中
                if state_data.get("feature_id") == feature_id:
                    matching_states.append(state_data)
            except (json.JSONDecodeError, IOError, KeyError):
                # 跳过损坏的、无法读取的或不包含 'feature_id' 字段的文件
                # 可以选择记录警告日志
                # print(f"Warning: Skipping invalid or unreadable state file {state_file}")
                continue
        # 返回所有匹配的实例状态数据列表
        return matching_states

    def get_current_task_id_for_feature(self, feature_id: str) -> Optional[str]:
        """根据 feature_id 获取当前活动（非完成）任务的 instance_id。"""
        pass

    def list_all_feature_ids(self) -> List[str]:
        """获取所有已知的 feature_id 列表。"""
        pass

