# ChatFlow v2.0 基础代码框架

以下是基于 v1.1 升级的 **v2.0 版本完整基础框架**。在保留轻量、无外部依赖的前提下，实现了递归工作流、树状状态聚合和资源配额控制等核心能力。

---

## 📁 项目结构
```bash
chatflow/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── engine.py          # 核心引擎 (递归增强)
│   └── models.py          # 数据模型 (树状拓扑)
│   └── schema.py          # Schema 验证 (含配额)
│   └── tree_status.py     # 树状状态聚合
├── storage/
│   ├── __init__.py
│   ├── file_state_store.py # 文件存储 (树状索引)
│   └── file_lock.py       # 文件锁工具
└── utils/
    ├── id_generator.py
    └── conditions.py      # 条件表达式求值
```

---

## ✅ `chatflow/core/models.py` (树状拓扑模型)
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
    TERMINATED = "terminated"

@dataclass
class ResourceQuota:
    max_tokens: Optional[int] = None
    max_duration_sec: Optional[float] = None  # 最大执行时间(秒)
    max_cost_usd: Optional[float] = None
    max_children: Optional[int] = None  # 最大子工作流数

@dataclass
class HistoryEntry:
    event_type: str
    phase: str
    task: str
    timestamp: float
     Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkflowState:
    """内存中完整运行时状态"""
    instance_id: str
    feature_id: str
    workflow_name: str
    current_phase: str
    variables: Dict[str, Any]
    status: WorkflowStatus
    
    # === v2.0 新增：递归与层级信息 ===
    parent_instance_id: Optional[str] = None
    children: List[str] = field(default_factory=list)  # 直接子节点
    recursion_depth: int = 0
    resource_quota: ResourceQuota = field(default_factory=ResourceQuota)
    
    # === 基础字段 ===
    history: List[HistoryEntry] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())
    meta: Dict[str, Any] = field(default_factory=dict)
    automation_level: int = 60

@dataclass
class WorkflowStatusInfo:
    """对外暴露的精简状态"""
    instance_id: str
    status: str
    progress: float
    current_phase: str
    feature_id: str
    created_at: float
    updated_at: float
    depth: int = 0
    
    # === v2.0 新增：树状摘要 ===
    child_count: int = 0
    running_children: int = 0
    failed_children: int = 0
    completed_children: int = 0

@dataclass
class WorkflowTreeStatus:
    """整棵工作流树的状态"""
    root_instance_id: str
    status: str  # aggregated status
    total_nodes: int
    completed_nodes: int
    failed_nodes: int
    running_nodes: int
    max_depth: int
    execution_time_sec: float
    total_cost_usd: float = 0.0
```

---

## ✅ `chatflow/core/schema.py` (含配额定义)
```python
# chatflow/core/schema.py
from dataclasses import dataclass
from typing import Dict, List, Optional
from .models import ResourceQuota, ConditionExpression

@dataclass
class PhaseDefinition:
    name: str
    task: str
    condition: Optional[ConditionExpression] = None
    fallback_phase: Optional[str] = None
    execution_strategy: str = "sequential"

@dataclass
class WorkflowSchema:
    name: str
    version: str
    phases: List[PhaseDefinition]
    
    # === v2.0 新增：默认资源配额 ===
    default_resource_quota: Optional[ResourceQuota] = None
    max_recursion_depth: Optional[int] = 5  # 全局深度限制
    
    def validate(self):
        names = [p.name for p in self.phases]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate phase names in schema {self.name}@{self.version}")
        
        # 检查深度限制合理性
        if self.max_recursion_depth is not None and self.max_recursion_depth < 1:
            raise ValueError("max_recursion_depth must be >= 1")
```

---

## ✅ `chatflow/core/tree_status.py` (树状状态聚合)
```python
# chatflow/core/tree_status.py
from typing import Dict, List
from .models import WorkflowTreeStatus, WorkflowStatusInfo
from ..storage.file_state_store import FileStateStore

def aggregate_tree_status(
    root_instance_id: str,
    state_store: FileStateStore,
    current_timestamp: float
) -> WorkflowTreeStatus:
    """
    聚合以 root_instance_id 为根的整棵树状态
    使用 .indexes/tree_index.json 提升性能
    """
    # 获取所有后代实例ID
    descendant_ids = _get_all_descendants(root_instance_id, state_store)
    all_ids = [root_instance_id] + descendant_ids
    
    # 加载所有状态（可优化为批量加载）
    statuses = []
    for iid in all_ids:
        info = state_store.get_workflow_status_info(iid)
        if info:
            statuses.append(WorkflowStatusInfo(**info))
    
    if not statuses:
        raise ValueError(f"No instances found for tree {root_instance_id}")
    
    # 计算聚合指标
    status_map = {
        'completed': sum(1 for s in statuses if s.status == 'completed'),
        'failed': sum(1 for s in statuses if s.status == 'failed'),
        'running': sum(1 for s in statuses if s.status == 'running'),
        'other': sum(1 for s in statuses if s.status not in ['completed', 'failed', 'running'])
    }
    
    max_depth = max((s.depth for s in statuses), default=0)
    start_time = min((s.created_at for s in statuses), default=current_timestamp)
    execution_time = current_timestamp - start_time
    
    return WorkflowTreeStatus(
        root_instance_id=root_instance_id,
        status=_aggregate_status(status_map),
        total_nodes=len(statuses),
        completed_nodes=status_map['completed'],
        failed_nodes=status_map['failed'],
        running_nodes=status_map['running'],
        max_depth=max_depth,
        execution_time_sec=execution_time
    )

def _get_all_descendants(root_id: str, state_store: FileStateStore) -> List[str]:
    """从索引文件获取所有后代"""
    index_file = state_store.indexes_dir / "tree_index.json"
    if index_file.exists():
        try:
            data = json.loads(index_file.read_text())
            return data.get(root_id, [])
        except:
            pass
    return []

def _aggregate_status(status_map: Dict[str, int]) -> str:
    """根据子节点状态计算聚合状态"""
    if status_map['failed'] > 0:
        return 'failed'
    elif status_map['running'] > 0:
        return 'running'
    elif status_map['completed'] == status_map['completed'] + status_map['other']:
        return 'completed'
    else:
        return 'unknown'
```

---

## ✅ `chatflow/storage/file_state_store.py` (树状索引)
```python
# chatflow/storage/file_state_store.py
import json
from pathlib import Path
from typing import Dict, List, Optional
from .file_lock import FileLock
from ...utils.id_generator import generate_timestamp

class FileStateStore:
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
        
        # 内存索引
        self._feature_index = self._load_index("feature_index.json")
        self._instance_index = self._load_index("instance_index.json")
        self._tree_index = self._load_index("tree_index.json")  # v2.0 新增
    
    def _load_index(self, filename: str) -> Dict:
        index_file = self.indexes_dir / filename
        if index_file.exists():
            try:
                return json.loads(index_file.read_text())
            except:
                pass
        return {}
    
    def _persist_index(self):
        indexes = [
            ("feature_index.json", self._feature_index),
            ("instance_index.json", self._instance_index),
            ("tree_index.json", self._tree_index)  # v2.0 新增
        ]
        for filename, data in indexes:
            (self.indexes_dir / filename).write_text(json.dumps(data, indent=2))
    
    def save_state(self, instance_id: str, state_ Dict):
        with FileLock(str(self.locks_dir / f"{instance_id}.lock")):
            # ... (同v1.1保存full_state和status_info)
            
            # === v2.0 新增：更新树状索引 ===
            parent_id = state_data.get("parent_instance_id")
            if parent_id:
                # 将当前实例加入父节点的children列表
                if parent_id not in self._instance_index:
                    # 父节点可能未在内存索引中
                    parent_file = self.instances_dir / f"{parent_id}.json"
                    if parent_file.exists():
                        try:
                            parent_data = json.loads(parent_file.read_text())
                            self._instance_index[parent_id] = parent_data
                        except: pass
                
                # 更新父子关系
                parent_children = self._instance_index.get(parent_id, {}).get("children", [])
                if instance_id not in parent_children:
                    parent_children.append(instance_id)
                    self._instance_index[parent_id]["children"] = parent_children
                
                # 构建树状索引：root -> [all descendants]
                self._update_tree_index(parent_id, instance_id)
            
            self._persist_index()
    
    def _update_tree_index(self, parent_id: str, child_id: str):
        """更新树状索引，将child_id及其后代加入所有祖先的索引"""
        # 找到根节点
        root_id = parent_id
        while True:
            parent_info = self._instance_index.get(root_id, {})
            if not parent_info.get("parent_instance_id"):
                break
            root_id = parent_info["parent_instance_id"]
        
        # 获取child_id的所有后代
        descendants = [child_id]
        if child_id in self._tree_index:
            descendants.extend(self._tree_index[child_id])
        
        # 将descendants加入根节点的树索引
        if root_id not in self._tree_index:
            self._tree_index[root_id] = []
        for desc in descendants:
            if desc not in self._tree_index[root_id]:
                self._tree_index[root_id].append(desc)
        
        # 递归更新所有中间节点
        current = parent_id
        while current != root_id:
            if current not in self._tree_index:
                self._tree_index[current] = []
            for desc in descendants:
                if desc not in self._tree_index[current]:
                    self._tree_index[current].append(desc)
            # 移动到上一级
            current = self._instance_index.get(current, {}).get("parent_instance_id")
            if not current:
                break
```

---

## ✅ `chatflow/core/engine.py` (v2.0 递归引擎)
```python
# chatflow/core/engine.py
import threading
from typing import Dict, Optional, List, Any
from dataclasses import asdict
from pathlib import Path

from .models import *
from .schema import WorkflowSchema
from .tree_status import aggregate_tree_status
from ..storage.file_state_store import FileStateStore, IWorkflowStateStore
from ...utils.id_generator import generate_id, generate_timestamp
from ...utils.conditions import evaluate_condition

class IWorkflowEngine:
    # ... (v1.1 接口)
    def create_subworkflow(...) -> str: ...
    def get_workflow_tree_status(...) -> WorkflowTreeStatus: ...
    def monitor_workflow_tree(...) -> Dict: ...
    def terminate_workflow_tree(...): ...

class WorkflowEngine(IWorkflowEngine):
    _instance = None
    _lock = threading.RLock()
    
    def __init__(self, storage_dir: str = ".chatflow", state_store: IWorkflowStateStore = None):
        if not hasattr(self, 'initialized'):
            with self._lock:
                if not hasattr(self, 'initialized'):
                    self.state_store = state_store or FileStateStore(storage_dir)
                    self._state_cache = {}
                    self._schema_cache = {}
                    self.config = {
                        "max_recursion_depth": 5  # 全局默认
                    }
                    self.initialized = True
    
    # ==== v2.0 核心：创建子工作流 ====
    def create_subworkflow(
        self,
        parent_instance_id: str,
        schema_id: str,
        context: Dict,
        resource_quota: Optional[ResourceQuota] = None,
        meta: Optional[Dict] = None
    ) -> str:
        with self._lock:
            # 1. 加载父实例状态
            parent_state = self.get_workflow_state(parent_instance_id)
            if not parent_state:
                raise ValueError(f"Parent instance {parent_instance_id} not found")
            
            # 2. 安全检查：递归深度
            new_depth = parent_state.recursion_depth + 1
            global_limit = self.config["max_recursion_depth"]
            schema = self._load_schema_from_file(schema_id)
            schema_limit = schema.max_recursion_depth
            
            effective_limit = min(
                d for d in [global_limit, schema_limit] if d is not None
            ) if any(d is not None for d in [global_limit, schema_limit]) else 5
            
            if new_depth > effective_limit:
                raise MaxRecursionDepthExceededError(
                    current=new_depth, 
                    max=effective_limit,
                    instance_id=parent_instance_id
                )
            
            # 3. 继承与合并配置
            inherited_meta = {**parent_state.meta}
            if meta:
                inherited_meta.update(meta)
            
            final_quota = resource_quota or parent_state.resource_quota
            if not final_quota.max_children:
                final_quota.max_children = parent_state.resource_quota.max_children
            
            # 4. 创建子实例
            sub_id = f"wfi_{generate_id()}"
            schema = self._load_schema_from_file(schema_id)
            initial_phase = schema.phases[0].name if schema.phases else "unknown"
            
            child_state = WorkflowState(
                instance_id=sub_id,
                feature_id=parent_state.feature_id,
                workflow_name=schema.name,
                current_phase=initial_phase,
                variables=context.copy(),
                status=WorkflowStatus.CREATED,
                parent_instance_id=parent_instance_id,
                recursion_depth=new_depth,
                resource_quota=final_quota,
                meta=inherited_meta
            )
            
            # 5. 建立父子关系
            parent_state.children.append(sub_id)
            self.state_store.save_state(parent_instance_id, asdict(parent_state))
            self._clear_cache(parent_instance_id)
            
            # 6. 保存子实例
            self.state_store.save_state(sub_id, asdict(child_state))
            self._cache_state(sub_id, child_state)
            
            # 7. 记录事件
            parent_state.history.append(HistoryEntry(
                event_type="subworkflow_created",
                phase="system",
                task="orchestration",
                timestamp=generate_timestamp(),
                data={"child_id": sub_id, "schema": schema_id}
            ))
            
            return sub_id
    
    # ==== v2.0 核心：获取树状状态 ====
    def get_workflow_tree_status(self, root_instance_id: str) -> WorkflowTreeStatus:
        current_ts = generate_timestamp()
        return aggregate_tree_status(root_instance_id, self.state_store, current_ts)
    
    # ==== v2.0 核心：监控树状执行 ====
    def monitor_workflow_tree(self, root_instance_id: str) -> Dict:
        """返回可用于UI渲染的树状结构数据"""
        tree_status = self.get_workflow_tree_status(root_instance_id)
        
        # 获取根节点状态
        root_info = self.get_workflow_status_info(root_instance_id)
        
        # 获取直接子节点状态
        children_statuses = []
        if root_info and hasattr(root_info, 'children'):
            for child_id in getattr(root_info, 'children', []):
                child_info = self.get_workflow_status_info(child_id)
                if child_info:
                    children_statuses.append(child_info)
        
        return {
            "root": root_info,
            "tree_status": asdict(tree_status),
            "children": [asdict(c) for c in children_statuses],
            "timestamp": generate_timestamp()
        }
    
    # ==== v2.0 核心：终止整个工作流树 ====
    def terminate_workflow_tree(self, root_instance_id: str, reason: str):
        with self._lock:
            # 1. 获取所有后代
            descendant_ids = self.state_store._tree_index.get(root_instance_id, [])
            all_ids = [root_instance_id] + descendant_ids
            
            # 2. 终止每个实例
            for instance_id in all_ids:
                state_data = self.state_store.load_state(instance_id)
                if state_data and state_data.get("status") not in ["completed", "failed", "terminated"]:
                    state_data["status"] = "terminated"
                    state_data["updated_at"] = generate_timestamp()
                    
                    # 记录终止事件
                    history = state_data.get("history", [])
                    history.append({
                        "event_type": "workflow_terminated",
                        "phase": "system",
                        "task": "orchestration",
                        "timestamp": generate_timestamp(),
                        "data": {"reason": reason}
                    })
                    state_data["history"] = history
                    
                    self.state_store.save_state(instance_id, state_data)
                    self._clear_cache(instance_id)
    
    # ==== 原有方法 (略作调整) ====
    def trigger_next_step(...):
        # ... (同v1.1)
        # 在推进时检查资源配额
        if state.resource_quota.max_duration_sec:
            elapsed = generate_timestamp() - state.created_at
            if elapsed > state.resource_quota.max_duration_sec:
                state.status = WorkflowStatus.FAILED
                # ... 记录失败
        # ...
```

---

## 🚀 ChatFlow v2.0 对外提供的核心接口

### 1. 初始化
```python
import chatflow
engine = chatflow.engine  # 或 chatflow.init("./path")
```

### 2. 启动主工作流
```python
main_result = engine.start_workflow_instance(
    workflow_schema={
        "name": "major-refactor",
        "version": "1.0",
        "max_recursion_depth": 4,
        "default_resource_quota": {
            "max_tokens": 100000,
            "max_duration_sec": 7200  # 2小时
        },
        "phases": [...]
    },
    initial_context={...},
    feature_id="feat_refactor_v2"
)
```

### 3. 创建子工作流（任务分解）
```python
# 主工作流执行到某阶段时
sub_id = engine.create_subworkflow(
    parent_instance_id=main_result.instance_id,
    schema_id="database-migration",
    context={
        "table": "users", 
        "migration_plan": "..."
    },
    resource_quota=ResourceQuota(
        max_tokens=20000,
        max_duration_sec=1800  # 30分钟
    ),
    meta={"priority": "high"}
)
```

### 4. 监控工作流树
```python
# 实时获取树状执行状态
tree_monitor = engine.monitor_workflow_tree(main_result.instance_id)

print(f"整体状态: {tree_monitor['tree_status']['status']}")
print(f"耗时: {tree_monitor['tree_status']['execution_time_sec']:.1f}s")
for child in tree_monitor['children']:
    print(f"  子任务 {child['instance_id']}: {child['status']} ({child['current_phase']})")
```

### 5. 获取树状聚合状态
```python
tree_status = engine.get_workflow_tree_status(main_result.instance_id)
if tree_status.failed_nodes > 0:
    print("有子任务失败，需人工介入")
elif tree_status.running_nodes == 0:
    print("所有任务完成！")
```

### 6. 紧急终止
```python
# 发现严重问题时终止整个任务树
engine.terminate_workflow_tree(
    main_result.instance_id,
    reason="Critical error detected in subtask"
)
```

### 7. 查询单个实例状态
```python
# 与v1.1兼容
state = engine.get_workflow_state(sub_id)
status_info = engine.get_workflow_status_info(sub_id)
```

---

## 📦 存储目录示例
```
.my_project/
└── .chatflow/
    ├── instances/
    │   ├── wfi_main.json               # 主实例状态
    │   └── wfi_main/
    │       ├── full_state.json
    │       ├── history.ndjson
    │       ├── children/               # 子实例链接
    │       │   └── wfi_db_migrate.link # 内容: "wfi_step1,wfi_step2"
    │       └── tasks/
    │
    │   ├── wfi_db_migrate.json         # 子实例状态
    │   └── wfi_db_migrate/
    │       ├── parent_link.txt         # 内容: "wfi_main"
    │       ├── full_state.json
    │       └── ...
    ├── .indexes/
    │   ├── feature_index.json
    │   ├── instance_index.json  
    │   └── tree_index.json             # {wfi_main: [wfi_db_mig, wfi_api_upd, ...]}
    └── schemas/
        └── major-refactor.yaml
```

---

## ✅ v2.0 关键优势总结

| 特性 | 用户价值 |
|------|----------|
| **递归工作流** | AI 可自主分解复杂任务 |
| **树状监控** | 全局掌控任务执行全景 |
| **深度限制** | 防止无限递归，保障安全 |
| **资源配额** | 控制成本与执行时间 |
| **紧急终止** | 风险可控，随时干预 |
| **向后兼容** | 旧接口仍可用 |

此框架让 ChatFlow 真正具备了处理“模糊、复杂”开发任务的能力，实现了从“执行者”到“协作者”的跃迁。
