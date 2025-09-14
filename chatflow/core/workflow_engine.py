# chatflow/core/workflow_engine.py

import threading
import yaml
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import asdict
from enum import Enum
from .engine import IWorkflowEngine
from .models import WorkflowStatus, HistoryEntry, WorkflowState, WorkflowStartResult, WorkflowStatusInfo
from .schema import WorkflowSchema, PhaseDefinition, ConditionExpression, ConditionTerm
from ..storage.file_state_store import FileStateStore, IWorkflowStateStore
from ..utils.id_generator import generate_id, generate_timestamp
from ..utils.conditions import evaluate_condition
from ..utils.risk_assessment import assess_risk

def get_workflow_path() -> Path:
    return Path.cwd() / "workflows"

def workflow_state_to_dict(state: WorkflowState) -> Dict[str, Any]:
    state_dict = asdict(state)
    if 'status' in state_dict and isinstance(state_dict['status'], Enum):
        state_dict['status'] = state_dict['status'].value
    return state_dict

class WorkflowEngine(IWorkflowEngine):
    def __init__(self, storage_dir: str = ".chatflow", state_store: IWorkflowStateStore = None):
        self.state_store = state_store or FileStateStore(storage_dir)
        self._state_cache: Dict[str, tuple[WorkflowState, float]] = {}
        self._schema_cache: Dict[str, WorkflowSchema] = {}
        self._lock = threading.RLock()

    def _load_schema_from_file(self, schema_name: str, version: str = "latest") -> WorkflowSchema:
        schema_key = f"{schema_name}@{version}"
        if schema_key in self._schema_cache:
            return self._schema_cache[schema_key]
        
        schema_path = Path(self.state_store.schemas_dir) / f"{schema_name}.yaml"
        if not schema_path.exists():
            schema_path = Path(self.state_store.schemas_dir) / f"{schema_name}.json"
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema {schema_name} not found")
        
        import yaml
        with open(schema_path, 'r') as f:
            data = yaml.safe_load(f)
        
        if 'phases' in data and data['phases'] and isinstance(data['phases'][0], dict):
            def dict_to_phase_definition(phase_dict: Dict) -> PhaseDefinition:
                if not isinstance(phase_dict, dict):
                    return phase_dict
                phase_data = phase_dict.copy()
                if 'task' not in phase_data:
                    phase_data['task'] = 'default_task' # 或者 'unknown_task'
                condition_data = phase_data.get('condition')
                if condition_data and isinstance(condition_data, dict):
                    def dict_to_condition_expression(cond_dict: Dict) -> ConditionExpression:
                        if not isinstance(cond_dict, dict):
                            return cond_dict
                        operands_data = cond_dict.get('operands', [])
                        converted_operands = []
                        for op_data in operands_data:
                            if isinstance(op_data, dict) and 'field' in op_data and 'operator' in op_data and 'value' in op_data:
                                converted_operands.append(ConditionTerm(**op_data))
                            elif isinstance(op_data, dict) and 'operator' in op_data:
                                converted_operands.append(dict_to_condition_expression(op_data))
                            else:
                                converted_operands.append(op_data)
                        return ConditionExpression(operator=cond_dict['operator'], operands=converted_operands)
                    phase_data['condition'] = dict_to_condition_expression(condition_data)
                return PhaseDefinition(**phase_data)
            
            data['phases'] = [dict_to_phase_definition(p_dict) for p_dict in data['phases']]
        
        schema = WorkflowSchema(**data)
        schema.validate()
        self._schema_cache[schema_key] = schema
        self._schema_cache[schema.name] = schema
        return schema

    def _get_cached_state(self, instance_id: str) -> Optional[WorkflowState]:
        if instance_id in self._state_cache:
            state, ts = self._state_cache[instance_id]
            if generate_timestamp() - ts < 30:
                return state
            else:
                del self._state_cache[instance_id]
        return None

    def _cache_state(self, instance_id: str, state: WorkflowState):
        self._state_cache[instance_id] = (state, generate_timestamp())

    def _clear_cache(self, instance_id: str):
        self._state_cache.pop(instance_id, None)
 
    def start_workflow_instance(
        self,
        workflow_schema: Dict[str, Any],
        initial_context: Dict[str, Any],
        feature_id: str,
        meta: Optional[Dict] = None
    ) -> WorkflowStartResult:
        with self._lock:
            def dict_to_phase_definition(phase_dict: Dict) -> PhaseDefinition:
                if not isinstance(phase_dict, dict):
                    return phase_dict
                phase_data = phase_dict.copy()
                if 'task' not in phase_data:
                    phase_data['task'] = 'default_task' # 或者 'unknown_task'
                condition_data = phase_data.get('condition')
                if condition_data and isinstance(condition_data, dict):
                    def dict_to_condition_expression(cond_dict: Dict) -> ConditionExpression:
                        if not isinstance(cond_dict, dict):
                            return cond_dict
                        operands_data = cond_dict.get('operands', [])
                        converted_operands = []
                        for op_data in operands_data:
                            if isinstance(op_data, dict) and 'field' in op_data and 'operator' in op_data and 'value' in op_data:
                                converted_operands.append(ConditionTerm(**op_data))
                            elif isinstance(op_data, dict) and 'operator' in op_data:
                                converted_operands.append(dict_to_condition_expression(op_data))
                            else:
                                converted_operands.append(op_data)
                        return ConditionExpression(operator=cond_dict['operator'], operands=converted_operands)
                    phase_data['condition'] = dict_to_condition_expression(condition_data)
                return PhaseDefinition(**phase_data)

            schema_phases_data = workflow_schema.get('phases', [])
            converted_phases = [dict_to_phase_definition(p_dict) for p_dict in schema_phases_data]

            schema_data_for_init = {
                "name": workflow_schema['name'],
                "version": workflow_schema.get('version', '1.0'),
                "phases": converted_phases
            }
            schema = WorkflowSchema(**schema_data_for_init)
            schema.validate()

            self._schema_cache[schema.name] = schema
            schema_key = f"{schema.name}@{schema.version}"
            self._schema_cache[schema_key] = schema

            instance_id = f"wfi_{generate_id()}"
            initial_phase = schema.phases[0].name if schema.phases else "unknown"
            state = WorkflowState(
                instance_id=instance_id,
                feature_id=feature_id,
                workflow_name=schema.name,
                current_phase=initial_phase,
                variables=initial_context.copy(),
                status=WorkflowStatus.CREATED,
                meta=meta or {},
                automation_level=meta.get("automation_level", 60) if meta else 60
            )
            
            state.history.append(HistoryEntry(
                event_type="workflow_started",
                phase=initial_phase,
                task="system",
                timestamp=generate_timestamp()
            ))
            
            self.state_store.save_state(instance_id, workflow_state_to_dict(state))
            self._cache_state(instance_id, state)
            return WorkflowStartResult(
                instance_id=instance_id,
                initial_phase=initial_phase,
                created_at=state.created_at
            )

    def trigger_next_step(self,
        instance_id: str,
        trigger_data: Optional[Dict] = None,
        dry_run: bool = False,
        meta: Optional[Dict] = None
    ) -> WorkflowState:
        with self._lock:
            state = self._get_cached_state(instance_id)
            if not state:
                state_data = self.state_store.load_state(instance_id)
                if not state_data:
                    raise ValueError(f"Instance {instance_id} not found")
                state = WorkflowState.from_dict(state_data)
            schema = self._load_schema_from_file(state.workflow_name)
            
            last_phase_started_idx = None
            for i in range(len(state.history) - 1, -1, -1):
                if (state.history[i].event_type == "phase_started" and
                    state.history[i].phase == state.current_phase):
                    last_phase_started_idx = i
                    break

            if last_phase_started_idx is not None:
                state.history[last_phase_started_idx].data["ended_at"] = generate_timestamp()
                state.history[last_phase_started_idx].data["status"] = "completed"
                if trigger_data:
                    state.history[last_phase_started_idx].data["trigger_data_snapshot"] = trigger_data

            if trigger_data:
                state.variables.update(trigger_data)
            
            current_idx = next((i for i, p in enumerate(schema.phases) 
                              if p.name == state.current_phase), -1)
            
            if current_idx == -1 or current_idx >= len(schema.phases) - 1:
                state.status = WorkflowStatus.COMPLETED
                new_phase = None
            else:
                next_phase_def = schema.phases[current_idx + 1]
                
                if next_phase_def.condition:
                    if not evaluate_condition(next_phase_def.condition, state.variables):
                        if next_phase_def.fallback_phase:
                            fallback_phase_name = next_phase_def.fallback_phase
                            fallback_phase_exists = any(p.name == fallback_phase_name for p in schema.phases)
                            
                            if fallback_phase_exists:
                                new_phase = fallback_phase_name
                            else:
                                # --- 修改开始 ---
                                # fallback_phase 不存在，跳过当前阶段 (next_phase_def) 和它指定的 fallback，
                                # 进入 next_phase_def 之后定义的下一个阶段。
                                # next_phase_def 的索引是 current_idx + 1
                                # 下一个定义的阶段索引是 (current_idx + 1) + 1 = current_idx + 2
                                next_valid_idx = current_idx + 2
                                if next_valid_idx < len(schema.phases):
                                    new_phase = schema.phases[next_valid_idx].name
                                else:
                                    # 如果没有更多阶段，则完成工作流
                                    new_phase = None
                                # --- 修改结束 ---
                        else:
                            new_phase = schema.phases[current_idx + 2].name if current_idx + 2 < len(schema.phases) else None
                    else:
                        new_phase = next_phase_def.name
                else:
                    new_phase = next_phase_def.name
                
                if new_phase:
                    state.current_phase = new_phase
                    state.status = WorkflowStatus.RUNNING
            
            if new_phase:
                new_phase_def = next((p for p in schema.phases if p.name == new_phase), None)
                task_for_new_phase = new_phase_def.task if new_phase_def else "unknown_task"
                
                state.history.append(HistoryEntry(
                    event_type="phase_started",
                    phase=new_phase,
                    task=task_for_new_phase,
                    timestamp=generate_timestamp(),
                    data={"trigger_data_snapshot": trigger_data}
                ))
            
            state.updated_at = generate_timestamp()
            if meta:
                state.meta.update(meta)
            
            if not dry_run:
                save_data = workflow_state_to_dict(state)
                self.state_store.save_state(instance_id, save_data)
                self._cache_state(instance_id, state)
            else:
                self._clear_cache(instance_id)
            
            return state

    def get_workflow_state(self, instance_id: str) -> Optional[WorkflowState]:
        cached = self._get_cached_state(instance_id)
        if cached:
            return cached
        
        state_data = self.state_store.load_state(instance_id)
        if state_data:
            #raw_history = state_data.get("history", [])
            #if raw_history and isinstance(raw_history[0], dict):
            #    # 假设如果列表第一个元素是 dict，则整个列表都需要转换
            #    converted_history = [HistoryEntry(**event_dict) for event_dict in raw_history]
            #    # 更新 state_data 中的 history 字段
            #    state_data["history"] = converted_history
            state = WorkflowState.from_dict(state_data)
            self._cache_state(instance_id, state)
            return state
        return None


    def get_workflow_status_info(self, instance_id: str) -> Optional[WorkflowStatusInfo]:
        return self.state_store.get_workflow_status_info(instance_id)
    
    def get_workflow_history(self, instance_id: str) -> List[HistoryEntry]:
        raw_events = self.state_store.get_workflow_history(instance_id)
        return [HistoryEntry(**e) for e in raw_events]

    def get_feature_status(self, feature_id: str, schema_name: str = "default") -> Dict:
        instance_ids = self.state_store.list_instances_by_feature(feature_id)
        instances = [self.get_workflow_status_info(iid) for iid in instance_ids]
        
        active_instances = [i for i in instances if i and i.get("status", "").strip() == "running"]
        completed_instances = [i for i in instances if i and i.get("status", "").strip() == "completed"]
        
        return {
            "feature_id": feature_id,
            "total_instances": len(instances),
            "running_count": len(active_instances),
            "completed_count": len(completed_instances),
            "latest_instance_id": instances[-1]["instance_id"] if instances and instances[-1] else None,
            "status": "completed" if completed_instances and not active_instances else "in_progress"
        }

    def get_workflow_path(self) -> Path:
        return get_workflow_path()
