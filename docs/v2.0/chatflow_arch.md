# ChatFlow v2.0 架构设计总结：赋予 AI "思考-分解-执行" 的类人能力

## 一、架构定位
ChatFlow v2.0 是从**线性工作流引擎**到**递归任务编排系统**的质变升级。它不再只是按预设步骤执行，而是让 AI 具备了 **"思考 → 分解 → 执行"** 的类人认知循环能力，能够自主处理复杂、模糊的开发任务。

> **核心突破**：AI 不再是“执行者”，而是具备**任务分解智能**的“项目经理”。

---

## 二、核心演进目标

| 能力 | v1.1 | v2.0 |
|------|------|------|
| **任务粒度** | 单一工作流 | 父-子递归结构 |
| **智能层级** | 条件分支 | 自主任务分解 |
| **执行模式** | 线性/并行 | 树状拓扑执行 |
| **状态视图** | 平面化 | 层次化聚合 |
| **资源管理** | 无控制 | 配额继承与限制 |

v2.0 的本质是：**将人类解决复杂问题的思维模式（分而治之）编码为可执行的系统机制**。

---

## 三、关键设计总结

### 1. **递归工作流模型（树状拓扑）**
- **设计**：
  - 每个工作流实例可创建**子工作流**。
  - 实例间形成 `parent_instance_id → children[]` 的树状关系。
  - 支持动态创建子流程，无需预先定义。
- **价值**：
  - **实现任务分解**：主工作流“重构用户服务” → 子工作流“修改数据库表”、“更新API接口”、“编写迁移脚本”。
  - **层次化执行**：父流程监控子流程，子流程失败可触发父流程的补偿逻辑。
  - **心智模型对齐**：符合人类“大任务拆小任务”的自然思维。

```python
# 主工作流中动态创建子工作流
sub_id = engine.create_subworkflow(
    parent_id="wfi_main",
    schema_id="database-migration",
    context={"table": "users", "add_column": "last_login"}
)
```

### 2. **深度限制与安全边界**
- **设计**：
  - 全局配置 `max_recursion_depth: int` (默认 3-5)。
  - 创建子工作流时自动检查当前深度。
  - 支持按 Schema 设置不同深度限制。
- **价值**：
  - **防止无限递归**：避免 AI 因提示词缺陷陷入“分解→再分解”的死循环。
  - **资源保护**：限制嵌套层数，防止系统资源耗尽。
  - **行为可预测**：为 AI 的自主性划定安全边界。

```python
def create_subworkflow(parent_id, schema_id, context):
    parent_state = engine.get_workflow_state(parent_id)
    if parent_state.recursion_depth >= config.max_depth:
        raise MaxRecursionError(f"Max depth {config.max_depth} exceeded")
    # ... 创建逻辑
```

### 3. **跨层级状态聚合**
- **设计**：
  - 引入 `WorkflowTreeStatus` 概念，聚合整棵树的状态。
  - 状态计算规则：
    - **COMPLETED**: 所有子节点 COMPLETED
    - **FAILED**: 任一子节点 FAILED
    - **RUNNING**: 至少一个 RUNNING，且无 FAILED
- **价值**：
  - **全局视图**：开发者一眼看清整个任务树的健康状况。
  - **智能决策**：父流程可根据子流程状态决定下一步（如“任一测试失败则回滚”）。
  - **高效查询**：`get_feature_status` 可返回树状摘要。

### 4. **父子上下文继承与隔离**
- **设计**：
  - **继承**：子工作流自动继承父级的 `feature_id`, `meta`, `automation_level`。
  - **覆盖**：子流程可指定自己的配额和策略。
  - **通信**：支持 `publish_result_to_parent()` 将结果上传。
- **价值**：
  - **减少重复配置**：不必在每个子流程中重新指定项目信息。
  - **灵活定制**：关键子流程可设置更高自动化级别。
  - **数据流动**：子任务结果可用于驱动父流程决策。

### 5. **资源配额继承与控制**
- **设计**：
  - 定义 `ResourceQuota`：`max_tokens`, `max_duration`, `max_cost`。
  - 子工作流默认继承父级配额，可被覆盖。
  - 引擎在执行前检查配额余额。
- **价值**：
  - **成本控制**：防止单个复杂任务消耗过多 LLM Token。
  - **时间保障**：避免长任务阻塞整体进度。
  - **风险隔离**：高风险子任务可分配有限资源。

```yaml
# schema/major-refactor.yaml
name: major-refactor
resource_quota:
  max_tokens: 50000
  max_duration: 3600  # 1小时
phases:
  - name: analyze_impact
    task: ai_analysis
  - name: execute_subtasks
    task: subworkflow_launcher
```

### 6. **树状执行监控器**
- **设计**：
  - 新增 `monitor_workflow_tree(instance_id)` 接口。
  - 返回实时的树状执行图，包含各节点状态、耗时、产物链接。
  - 支持暂停/恢复/终止整个子树。
- **价值**：
  - **可视化洞察**：清晰展示任务分解与执行路径。
  - **主动干预**：发现某个子任务卡住时，可手动介入。
  - **性能分析**：识别瓶颈环节（哪个子任务最耗时）。

---

## 四、架构优势对比

| 能力 | v1.1 | v2.0 |
|------|------|------|
| **任务处理** | 简单线性任务 | 复杂嵌套任务 |
| **AI智能** | 条件判断 | 自主分解 |
| **执行拓扑** | 链状/网状 | 树状 |
| **状态视图** | 单实例 | 整体树 |
| **资源控制** | 无 | 继承+限额 |
| **适用场景** | 功能开发 | 系统重构/迁移 |

---

## 五、关键接口演进

### 新增核心接口
```python
def create_subworkflow(
    self,
    parent_instance_id: str,
    schema_id: str,
    context: Dict,
    resource_quota: Optional[ResourceQuota] = None,
    meta: Optional[Dict] = None
) -> str:
    """
    创建子工作流
    :return: 子实例ID
    """

def get_workflow_tree_status(
    self,
    root_instance_id: str
) -> WorkflowTreeStatus:
    """
    获取以某实例为根的整棵树状态
    包含所有后代节点的聚合信息
    """

def monitor_workflow_tree(
    self,
    root_instance_id: str
) -> Dict:
    """
    监控树状执行过程
    返回实时的树形结构数据，用于UI渲染
    """

def terminate_workflow_tree(
    self,
    root_instance_id: str,
    reason: str
):
    """
    终止整个工作流树（包括所有子流程）
    用于紧急中断
    """
```

### 增强现有接口
```python
# 在状态模型中增加层级信息
class WorkflowState:
    instance_id: str
    parent_instance_id: Optional[str]  # 新增
    children: List[str] = field(default_factory=list)  # 新增
    recursion_depth: int  # 新增
    resource_quota: ResourceQuota  # 新增
    
class WorkflowStatusInfo:
    depth: int  # 递归深度
    child_count: int  # 子节点数量
    failed_children: int  # 失败子节点数
```

---

## 六、存储结构演进

```
.chatflow/
├── instances/
│   ├── wfi_main.json               # 父实例状态
│   └── wfi_main/
│       ├── full_state.json
│       ├── history.ndjson
│       ├── tasks/
│       └── children/               # 子实例目录索引
│           └── wfi_db_migrate.link # 内容: "wfi_step1,wfi_step2"
│
│   ├── wfi_db_migrate.json         # 子实例状态
│   └── wfi_db_migrate/
│       ├── parent_link.txt         # 内容: "wfi_main"
│       ├── full_state.json
│       └── ...
└── .indexes/
    └── tree_index.json             # {root_id: [all_descendant_ids]}
```

> **说明**：通过 `.link` 文件和反向引用，构建高效的树状查询能力。

---

## 七、典型使用场景

### 场景1：大型系统重构
```python
# 主工作流
1. 分析代码依赖 → 触发多个子工作流
   ├─ 子工作流A: 重构模块X
   │   ├─ 子子工作流: 更新X的单元测试
   │   └─ 子子工作流: 迁移X的数据库
   ├─ 子工作流B: 重构模块Y
   └─ 子工作流C: 更新API文档
2. 所有子工作流完成后 → 执行集成测试
```

### 场景2：问题根因排查
```python
# 主工作流
1. 收到错误报告 → 分解排查任务
   ├─ 子工作流: 分析应用日志
   ├─ 子工作流: 检查数据库性能
   ├─ 子工作流: 验证网络连接
   └─ 子工作流: 审查最近变更
2. 汇总各子工作流结论 → 生成诊断报告
```

---

## 总结

ChatFlow v2.0 的成功在于：**将“任务分解”这一人类高级认知能力，转化为 AI Agent 可执行的系统原语**。它不再是被动地执行指令，而是能够：

1. **思考**（Analyze）：理解复杂任务的本质
2. **分解**（Decompose）：将其拆解为可管理的子任务
3. **执行**（Execute）：协调资源完成各子任务
4. **聚合**（Aggregate）：整合结果并汇报

这套设计使得 ChatFlow 能够真正处理现实世界中模糊、复杂的软件工程挑战，迈出了从“工具”到“协作者”的关键一步。
