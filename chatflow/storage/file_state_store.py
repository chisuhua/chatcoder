# chatflow/storage/file_state_store.py
"""
ChatFlow 核心实现 - 文件状态存储 (FileWorkflowStateStore)
提供基于文件系统的工作流实例状态存储实现。
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from .file_lock import FileLock
from .state import IWorkflowStateStore
from ..utils.checksum import calculate_checksum # 导入

class FileStateStore(IWorkflowStateStore):
    def __init__(self, base_dir: str = ".chatflow"):
        self.base_dir = Path(base_dir).resolve()
        self.instances_dir = self.base_dir / "instances"
        self.features_dir = self.base_dir / "features"
        self.schemas_dir = self.base_dir / "schemas"
        self.locks_dir = self.base_dir / ".locks"
        self.indexes_dir = self.base_dir / ".indexes"

        for dir_path in [self.instances_dir, self.features_dir, self.schemas_dir,
                        self.locks_dir, self.indexes_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        self._feature_index = self._load_index("feature_index.json")
        self._instance_index = self._load_index("instance_index.json")

    def _load_index(self, filename: str) -> Dict:
        index_file = self.indexes_dir / filename
        if index_file.exists():
            try:
                return json.loads(index_file.read_text())
            except:
                pass
        return {}

    def _persist_index(self):
        # 异步或定期保存
        (self.indexes_dir / "feature_index.json").write_text(
            json.dumps(self._feature_index, indent=2)
        )
        (self.indexes_dir / "instance_index.json").write_text(
            json.dumps(self._instance_index, indent=2)
        )

    def save_state(self, instance_id: str, state_data: Dict):
        with FileLock(str(self.locks_dir / f"{instance_id}.lock")):
            # 1. 保存完整状态到子目录
            instance_subdir = self.instances_dir / instance_id
            instance_subdir.mkdir(exist_ok=True)

            full_state_file = instance_subdir / "full_state.json"
            temp_file = full_state_file.with_suffix(".json.tmp")
            temp_file.write_text(json.dumps(state_data, indent=2), encoding="utf-8")
            temp_file.rename(full_state_file)

            # 2. 保存精简状态到主目录（用于快速查询）
            status_info = {
                "instance_id": state_data["instance_id"],
                "status": state_data["status"],
                "current_phase": state_data["current_phase"],
                "feature_id": state_data["feature_id"],
                "created_at": state_data["created_at"],
                "updated_at": state_data["updated_at"],
                "progress": self._calculate_progress(state_data),
                "depth": state_data.get("recursion_depth", 0)
            }
            main_file = self.instances_dir / f"{instance_id}.json"
            main_temp = main_file.with_suffix(".json.tmp")
            main_temp.write_text(json.dumps(status_info, indent=2), encoding="utf-8")
            main_temp.rename(main_file)

            # 3. 保存/重写历史事件 (简单处理，可优化为增量)
            history_file = instance_subdir / "history.ndjson"
            temp_history_file = history_file.with_suffix(".ndjson.tmp")
            try:
                with open(temp_history_file, "w", encoding="utf-8") as f:
                    for event in state_data.get("history", []):
                        f.write(json.dumps(event) + "\n")
                temp_history_file.replace(history_file) # 原子替换
            except Exception as e:
                temp_history_file.unlink(missing_ok=True) # 出错则删除临时文件
                raise e

            # 4. 更新索引
            feature_id = state_data["feature_id"]
            # 确保 instance_id 不重复添加到 feature_index
            if instance_id not in self._feature_index.get(feature_id, []):
                 self._feature_index.setdefault(feature_id, []).append(instance_id)
            self._instance_index[instance_id] = {
                "feature_id": feature_id,
                "status": state_data["status"],
                "updated_at": state_data["updated_at"]
            }
            self._persist_index()  # 可优化为异步

    def _calculate_progress(self, state_data: Dict) -> float:
        # 计算已完成的阶段数
        # 兼容两种标记方式：
        # 1. 旧的 phase_completed 事件类型
        # 2. phase_started 事件的 data.status = 'completed'
        completed_count = len([
            h for h in state_data.get("history", [])
            if h.get("event_type") == "phase_completed" or
               (h.get("event_type") == "phase_started" and h.get("data", {}).get("status") == "completed")
        ])

        # 注意：总阶段数的计算依赖于外部传入或在状态中存储。
        # 这里使用一个临时方案，假设状态中存有 'total_phases' 字段。
        # 更健壮的做法是在 save_state 时传入 schema 或计算好的总阶段数。
        # 如果没有 'total_phases' 字段，则进度无法准确计算，这里默认为 1 以避免除零错误。
        # 实际应用中，应在工作流启动时计算并存储总阶段数。
        total_phases = state_data.get("total_phases", 1) # 默认值 1
        if total_phases <= 0:
             total_phases = 1 # 防御性编程

        if completed_count >= total_phases:
            return 1.0
        else:
            return completed_count / total_phases

    def load_state(self, instance_id: str) -> Optional[Dict]:
        full_state_file = self.instances_dir / instance_id / "full_state.json"
        with FileLock(str(self.locks_dir / f"{instance_id}.lock")):
            if full_state_file.exists():
                try:
                    content = full_state_file.read_text(encoding="utf-8")
                    return json.loads(content)
                except (IOError, json.JSONDecodeError) as e:
                    print(f"Error loading state for {instance_id}: {e}")
        return None

    def get_workflow_status_info(self, instance_id: str) -> Optional[Dict]:
        """获取精简状态（推荐用于UI）"""
        status_file = self.instances_dir / f"{instance_id}.json"
        if status_file.exists():
            try:
                content = status_file.read_text(encoding="utf-8")
                return json.loads(content)
            except():
                pass
        return None

    def get_workflow_history(self, instance_id: str) -> List[Dict]:
        """获取完整历史事件流"""
        history_file = self.instances_dir / instance_id / "history.ndjson"
        events = []
        if history_file.exists():
            try:
                for line in history_file.open(encoding="utf-8"):
                    if line.strip():
                        events.append(json.loads(line))
            except():
                pass
        return events


    def list_all_state_files(self) -> List[Path]:
        """
        (FileWorkflowStateStore 特有) 列出基目录下所有状态文件的路径。
        """
        if not self.base_dir.exists():
            return []
        return list(self.base_dir.glob("*.json"))

    def list_instances_by_feature(self, feature_id: str) -> List[str]:
        # 使用内存中的 _feature_index
        return self._feature_index.get(feature_id, [])

    # --- 添加缺失的方法 ---
    def _get_instance_tasks_dir(self, instance_id: str) -> Path:
        tasks_dir = self.instances_dir / instance_id / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True) # 确保目录存在
        return tasks_dir

    def _get_instance_artifacts_dir(self, instance_id: str) -> Path:
        artifacts_dir = self.instances_dir / instance_id / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        return artifacts_dir
    # --- 添加结束 ---

    def save_task_artifacts(
        self,
        feature_id: str,
        instance_id: str,
        phase_name: str,
        task_record_data: Dict,
        prompt_content: str,
        ai_response_content: str
    ):
        tasks_dir = self._get_instance_tasks_dir(instance_id) # 使用新方法
        artifacts_dir = self._get_instance_artifacts_dir(instance_id) # 使用新方法
        # 假设产物文件存放在 artifacts_dir 下以 phase_name 命名的子目录
        phase_artifacts_dir = artifacts_dir / phase_name
        phase_artifacts_dir.mkdir(parents=True, exist_ok=True)

        base_name = phase_name.replace(" ", "_").lower() # 替换单个空格

        prompt_checksum = calculate_checksum(prompt_content)
        response_checksum = calculate_checksum(ai_response_content)

        artifact_paths = {
            "prompt": f"artifacts/{phase_name}/{base_name}.prompt.md",
            "response": f"artifacts/{phase_name}/{base_name}.ai_response.md"
        }
        # --- ---

        # 更新 task_record_data
        task_record_data["prompt_checksum"] = prompt_checksum
        task_record_data["response_checksum"] = response_checksum
        task_record_data["artifact_paths"] = artifact_paths
        # --- ---

        # 保存元数据
        record_file = tasks_dir / f"{base_name}.json"
        record_file.write_text(json.dumps(task_record_data, indent=2))
        # 保存文本产物
        prompt_file = phase_artifacts_dir / f"{base_name}.prompt.md"
        response_file = phase_artifacts_dir / f"{base_name}.ai_response.md"
        prompt_file.write_text(prompt_content)
        response_file.write_text(ai_response_content)

    def get_current_task_id_for_feature(self, feature_id: str) -> Optional[str]:
        """根据 feature_id 获取当前活动（非完成）任务的 instance_id。"""
        # TODO: 实现此方法逻辑
        pass

    def list_features(self) -> List[str]:
        """获取所有已知的 feature_id 列表。"""
        # TODO: 实现此方法逻辑，例如返回 self._feature_index.keys()
        return list(self._feature_index.keys()) # 示例实现
