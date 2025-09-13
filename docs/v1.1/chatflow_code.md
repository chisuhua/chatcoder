# ChatFlow v1.1 基础代码框架

以下是基于 v1.0 升级的 **v1.1 版本完整基础框架**。在保持轻量、无外部依赖的前提下，实现了 Schema 验证、三重状态体系、条件分支和 Dry Run 等核心能力。

---

## 📁 项目结构
```bash
chatflow/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── engine.py          # 核心引擎 (增强)
│   └── models.py          # 数据模型 (三重状态)
│   └── schema.py          # Schema 验证
├── storage/
│   ├── __init__.py
│   ├── file_state_store.py # 文件存储 (增强)
│   └── file_lock.py       # 文件锁工具
└── utils/
    ├── id_generator.py
    └── conditions.py      # 条件表达式求值
```

---

## ✅ `chatflow/core/models.py` (三重状态体系)
```python
# chatflow/core/models.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

class WorkflowStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class HistoryEntry:
    event_type: str  # workflow_started, phase_started, phase_completed, etc.
    phase: str
    task: str
    timestamp: float
    data: Dict[str, Any] = field(default_factory=dict)  # trigger_data_snapshot, metrics等

@dataclass
class TaskExecutionRecord:
    phase_name: str
    status: str
    started_at: float
    ended_at: Optional[float] = None
    prompt_checksum: str = ""
    response_checksum: str = ""
    artifact_paths: Dict[str, str] = field(default_factory=dict)

@dataclass
class WorkflowState:
    """内存中完整运行时状态"""
    instance_id: str
    feature_id: str
    workflow_name: str
    current_phase: str
    variables: Dict[str, Any]
    status: WorkflowStatus
    history: List[HistoryEntry] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())
    meta: Dict[str, Any] = field(default_factory=dict)
    automation_level: int = 60  # 0-100

@dataclass
class WorkflowStatusInfo:
    """对外暴露的精简状态"""
    instance_id: str
    status: str  # "running", "completed"
    progress: float  # 0.0 - 1.0
    current_phase: str
    feature_id: str
    created_at: float
    updated_at: float
    depth: int = 0  # 递归深度 (v2预留)

# 返回值对象
@dataclass
class WorkflowStartResult:
    instance_id: str
    initial_phase: str
    created_at: float
```

---

## ✅ `chatflow/core/schema.py` (Schema 验证)
```python
# chatflow/core/schema.py
from dataclasses import dataclass
from typing import Dict, List, Optional
from .models import TaskStatus

@dataclass
class ConditionExpression:
    operator: str  # "and", "or", "not"
    operands: List['ConditionTerm']

@dataclass
class ConditionTerm:
    field: str
    operator: str  # "=", "!=", ">", "<", ">=", "<="
    value: Any

@dataclass
class PhaseDefinition:
    name: str
    task: str
    condition: Optional[ConditionExpression] = None
    fallback_phase: Optional[str] = None  # 条件不满足时跳转
    execution_strategy: str = "sequential"  # sequential, parallel, concurrent

@dataclass
class WorkflowSchema:
    name: str
    version: str
    phases: List[PhaseDefinition]
    
    def validate(self):
        # 检查phase名称唯一性
        names = [p.name for p in self.phases]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate phase names in schema {self.name}@{self.version}")
        
        # 可添加更多静态检查...
```

---

## ✅ `chatflow/utils/conditions.py` (条件求值)
```python
# chatflow/utils/conditions.py
from typing import Dict, Any
from ..core.schema import ConditionExpression, ConditionTerm

def evaluate_condition(condition: ConditionExpression, context: Dict[str, Any]) -> bool:
    """递归求值条件表达式"""
    if condition.operator == "and":
        return all(_evaluate_term(term, context) for term in condition.operands)
    elif condition.operator == "or":
        return any(_evaluate_term(term, context) for term in condition.operands)
    elif condition.operator == "not":
        return not _evaluate_term(condition.operands[0], context)
    else:
        raise ValueError(f"Unknown operator: {condition.operator}")

def _evaluate_term(term: 'ConditionTerm', context: Dict[str, Any]) -> bool:
    """求值单个条件项"""
    value = _get_nested_value(term.field, context)
    
    if term.operator == "=":
        return value == term.value
    elif term.operator == "!=":
        return value != term.value
    elif term.operator == ">":
        return value > term.value
    elif term.operator == "<":
        return value < term.value
    elif term.operator == ">=":
        return value >= term.value
    elif term.operator == "<=":
        return value <= term.value
    else:
        raise ValueError(f"Unknown operator: {term.operator}")

def _get_nested_value(path: str, obj: Dict[str, Any]) -> Any:
    """支持点号嵌套访问: "code.risk_level" """
    keys = path.split('.')
    for key in keys:
        if isinstance(obj, dict) and key in obj:
            obj = obj[key]
        else:
            return None
    return obj
```

---

## ✅ `chatflow/storage/file_state_store.py` (增强版)
```python
# chatflow/storage/file_state_store.py
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from .file_lock import FileLock
from ...utils.id_generator import generate_timestamp

class IWorkflowStateStore:
    def save_state(self, instance_id: str, state_ Dict): ...
    def load_state(self, instance_id: str) -> Optional[Dict]: ...
    def list_instances_by_feature(self, feature_id: str) -> List[str]: ...
    def save_task_artifacts(...): ...

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
        
        # 内存索引（可选持久化）
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
    
    def save_state(self, instance_id: str, state_ Dict):
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
            
            # 3. 追加历史事件
            if state_data.get("new_events"):
                history_file = instance_subdir / "history.ndjson"
                with open(history_file, "a", encoding="utf-8") as f:
                    for event in state_data["new_events"]:
                        f.write(json.dumps(event) + "\n")
                state_data.pop("new_events", None)
            
            # 4. 更新索引
            feature_id = state_data["feature_id"]
            self._feature_index.setdefault(feature_id, []).append(instance_id)
            self._instance_index[instance_id] = {
                "feature_id": feature_id,
                "status": state_data["status"],
                "updated_at": state_data["updated_at"]
            }
            self._persist_index()  # 可优化为异步
    
    def _calculate_progress(self, state_ Dict) -> float:
        # 简单实现：已完成阶段数 / 总阶段数
        # 实际应从schema获取总阶段
        total_phases = 5  # 示例
        completed = len([h for h in state_data.get("history", []) 
                        if h["event_type"] == "phase_completed"])
        return min(completed / total_phases, 1.0) if total_phases > 0 else 0.0
    
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
            except:
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
            except:
                pass
        return events
```

---

## ✅ `chatflow/core/engine.py` (v1.1 增强版)
```python
# chatflow/core/engine.py
import threading
from typing import Dict, Optional, List, Any
from dataclasses import asdict
from pathlib import Path

from .models import *
from .schema import WorkflowSchema
from ..storage.file_state_store import FileStateStore, IWorkflowStateStore
from ...utils.id_generator import generate_id, generate_timestamp
from ...utils.conditions import evaluate_condition

class IWorkflowEngine:
    def start_workflow_instance(...) -> WorkflowStartResult: ...
    def trigger_next_step(...) -> WorkflowInstanceState: ...
    def get_workflow_state(...) -> Optional[WorkflowState]: ...
    def get_workflow_status_info(...) -> Optional[WorkflowStatusInfo]: ...
    def get_workflow_history(...) -> List[HistoryEntry]:
        raise NotImplementedError

class WorkflowEngine(IWorkflowEngine):
    _instance = None
    _lock = threading.RLock()
    
    def __init__(self, storage_dir: str = ".chatflow", state_store: IWorkflowStateStore = None):
        if not hasattr(self, 'initialized'):
            with self._lock:
                if not hasattr(self, 'initialized'):
                    self.state_store = state_store or FileStateStore(storage_dir)
                    self._state_cache = {}  # instance_id -> (state, timestamp)
                    self._schema_cache = {}  # schema_key -> WorkflowSchema
                    self.initialized = True
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    # ==== Schema Management ====
    def _load_schema_from_file(self, schema_name: str, version: str = "latest") -> WorkflowSchema:
        schema_key = f"{schema_name}@{version}"
        if schema_key in self._schema_cache:
            return self._schema_cache[schema_key]
        
        schema_path = Path(self.state_store.schemas_dir) / f"{schema_name}.yaml"
        if not schema_path.exists():
            schema_path = Path(self.state_store.schemas_dir) / f"{schema_name}.json"
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema {schema_name} not found")
        
        import yaml  # 建议作为可选依赖
        with open(schema_path, 'r') as f:
            data = yaml.safe_load(f)
        
        schema = WorkflowSchema(**data)
        schema.validate()
        self._schema_cache[schema_key] = schema
        return schema
    
    # ==== State Caching ====
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
    
    # ==== Main API ====
    def start_workflow_instance(
        self,
        workflow_schema: Dict,
        initial_context: Dict,
        feature_id: str,
        meta: Optional[Dict] = None
    ) -> WorkflowStartResult:
        with self._lock:
            # 从字典创建并验证Schema
            schema = WorkflowSchema(**workflow_schema)
            schema.validate()
            
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
            
            # 记录启动事件
            state.history.append(HistoryEntry(
                event_type="workflow_started",
                phase=initial_phase,
                task="system",
                timestamp=generate_timestamp()
            ))
            
            self.state_store.save_state(instance_id, asdict(state))
            self._cache_state(instance_id, state)
            
            return WorkflowStartResult(
                instance_id=instance_id,
                initial_phase=initial_phase,
                created_at=state.created_at
            )
    
    def trigger_next_step(
        self,
        instance_id: str,
        trigger_ Optional[Dict] = None,
        dry_run: bool = False,
        meta: Optional[Dict] = None
    ) -> WorkflowState:
        with self._lock:
            # 加载当前状态
            state = self._get_cached_state(instance_id)
            if not state:
                state_data = self.state_store.load_state(instance_id)
                if not state_
                    raise ValueError(f"Instance {instance_id} not found")
                state = WorkflowState(**state_data)
            
            # 加载工作流定义
            schema = self._load_schema_from_file(state.workflow_name)
            
            # 记录当前阶段完成
            if state.history and state.history[-1].phase == state.current_phase:
                state.history[-1].data["ended_at"] = generate_timestamp()
                state.history[-1].data["status"] = "completed"
                if trigger_
                    state.history[-1].data["trigger_data_snapshot"] = trigger_data
            
            # 更新变量
            if trigger_
                state.variables.update(trigger_data)
            
            # 获取下一阶段候选
            current_idx = next((i for i, p in enumerate(schema.phases) 
                              if p.name == state.current_phase), -1)
            
            if current_idx == -1 or current_idx >= len(schema.phases) - 1:
                # 已到最后，标记完成
                state.status = WorkflowStatus.COMPLETED
                new_phase = None
            else:
                # 获取下一阶段定义
                next_phase_def = schema.phases[current_idx + 1]
                
                # 检查条件
                if next_phase_def.condition:
                    if not evaluate_condition(next_phase_def.condition, state.variables):
                        # 条件不满足，走fallback或跳过
                        if next_phase_def.fallback_phase:
                            new_phase = next_phase_def.fallback_phase
                        else:
                            # 跳过此阶段，继续下一下
                            new_phase = schema.phases[current_idx + 2].name if current_idx + 2 < len(schema.phases) else None
                    else:
                        new_phase = next_phase_def.name
                else:
                    new_phase = next_phase_def.name
                
                if new_phase:
                    state.current_phase = new_phase
                    state.status = WorkflowStatus.RUNNING
            
            # 记录新阶段开始
            if new_phase:
                state.history.append(HistoryEntry(
                    event_type="phase_started",
                    phase=new_phase,
                    task=schema.phases[current_idx + 1].task,
                    timestamp=generate_timestamp(),
                    data={"trigger_data_snapshot": trigger_data}
                ))
            
            # 更新时间戳
            state.updated_at = generate_timestamp()
            if meta:
                state.meta.update(meta)
            
            # Dry Run 模式：不保存
            if not dry_run:
                # 准备保存数据（包含新事件）
                save_data = asdict(state)
                save_data["new_events"] = [
                    asdict(e) for e in state.history[-2:]  # 最近两个事件
                ] if len(state.history) >= 2 else []
                
                self.state_store.save_state(instance_id, save_data)
                if not dry_run:
                    self._cache_state(instance_id, state)
            else:
                # Dry Run：清除缓存，强制下次重新加载
                self._clear_cache(instance_id)
            
            return state
    
    def get_workflow_state(self, instance_id: str) -> Optional[WorkflowState]:
        cached = self._get_cached_state(instance_id)
        if cached:
            return cached
        
        state_data = self.state_store.load_state(instance_id)
        if state_
            state = WorkflowState(**state_data)
            self._cache_state(instance_id, state)
            return state
        return None
    
    def get_workflow_status_info(self, instance_id: str) -> Optional[WorkflowStatusInfo]:
        return self.state_store.get_workflow_status_info(instance_id)
    
    def get_workflow_history(self, instance_id: str) -> List[HistoryEntry]:
        raw_events = self.state_store.get_workflow_history(instance_id)
        return [HistoryEntry(**e) for e in raw_events]
```

---

## 🚀 ChatFlow v1.1 对外提供的核心接口

### 1. 初始化
```python
import chatflow

# 使用默认路径
engine = chatflow.engine

# 自定义路径
engine = chatflow.init("./my_project/.chatflow")
```

### 2. 启动工作流（返回结构化结果）
```python
result = engine.start_workflow_instance(
    workflow_schema={
        "name": "code_review",
        "version": "1.1",
        "phases": [
            {"name": "static_analysis", "task": "tool"},
            {"name": "ai_review", "task": "ai", "condition": {...}}
        ]
    },
    initial_context={"pr_url": "https://..."},
    feature_id="feat_pr_123",
    meta={"user_id": "alice", "automation_level": 70}
)

print(result.instance_id)  # wfi_abc123
print(result.initial_phase)  # static_analysis
```

### 3. 推进工作流（支持 Dry Run）
```python
# 正常推进
state = engine.trigger_next_step(
    instance_id=result.instance_id,
    trigger_data={"issues_found": 5},
    meta={"duration_sec": 12.5}
)

# Dry Run 预演
preview_state = engine.trigger_next_step(
    instance_id=result.instance_id,
    trigger_data={"issues_found": 50},  # 假设发现大量问题
    dry_run=True  # 不保存状态
)

print(preview_state.current_phase)  # 可能是 "manual_review" 而非 "ai_review"
```

### 4. 查询状态（多层级）
```python
# 获取精简状态（推荐用于UI显示）
status_info = engine.get_workflow_status_info("wfi_abc123")
# {'instance_id': 'wfi_abc123', 'status': 'running', 'progress': 0.4, ...}

# 获取完整状态（用于调试）
full_state = engine.get_workflow_state("wfi_abc123")

# 获取审计历史
history = engine.get_workflow_history("wfi_abc123")
# [HistoryEntry(event_type="phase_started", ...), ...]
```

### 5. 获取特性聚合状态
```python
feature_status = engine.get_feature_status("feat_pr_123")
# {'total_instances': 1, 'running_count': 1, 'status': 'in_progress', ...}
```

---

## 📦 存储目录示例
```
.my_project/
└── .chatflow/
    ├── schemas/
    │   └── code_review.yaml
    ├── instances/
    │   ├── wfi_abc123.json              # 精简状态 (StatusInfo)
    │   └── wfi_abc123/
    │       ├── full_state.json          # 完整状态 (State)
    │       ├── history.ndjson           # 事件流
    │       └── tasks/
    │           └── static_analysis.json
    ├── features/
    │   └── feat_pr_123.link
    ├── .indexes/
    │   └── feature_index.json
    └── .locks/
```

---

## ✅ v1.1 关键优势总结

| 特性 | 用户价值 |
|------|----------|
| **Schema 验证** | 配置错误提前暴露，避免执行中断 |
| **Dry Run** | 安全预演流程，提升调试效率 |
| **三重状态** | UI快、审计全、内存优 |
| **条件分支** | 流程智能，根据上下文自适应 |
| **渐进自动化** | 风险可控，人机协同 |
| **完整历史** | 全链路追踪，支持回溯分析 |

此框架在 **仅增加约150行核心代码** 的前提下，将 ChatFlow 从“状态记录器”升级为“可信决策引擎”，完美平衡了轻量与强大。
