# ChatFlow v1.1 架构设计总结

## 一、架构定位
ChatFlow v1.1 是在 v1.0 轻量基础之上的**可信工作流引擎**。它保留了单机优先、无外部依赖的核心特性，同时引入关键的健壮性、智能性和可观测性机制，使 AI 工作流从“能用”迈向“可靠、可控、可审计”。

---

## 二、核心演进目标

| 维度 | v1.0 | v1.1 |
|------|------|------|
| **可靠性** | 基础文件存储 | Schema 验证 + 校验和 |
| **智能性** | 线性流程 | 条件分支决策 |
| **可控性** | 全自动或全手动 | 渐进式自动化控制 |
| **可观测性** | 状态快照 | 三重状态体系 + 完整历史 |
| **安全性** | 冲突防护 | Dry Run + 操作预检 |

v1.1 的本质是：**让 AI 的自主行为变得可预测、可验证、可干预**。

---

## 三、关键设计总结

### 1. **Schema 驱动执行（声明式配置）**
- **设计**：
  - 工作流定义采用 YAML/JSON Schema。
  - 使用 `pydantic` 进行结构化验证（字段类型、必填项、ID 唯一性）。
  - Schema 中内置 `version` 字段支持未来演进。
- **价值**：
  - 将配置错误从运行时提前到加载时，避免“AI 执行到一半发现配置错”。
  - 版本化 Schema 支持平滑升级，实例绑定特定版本。
  - 为团队共享和复用工作流模板奠定基础。

```yaml
# schema/code_review.yaml
name: code-review
version: "1.1"
phases:
  - id: static_analysis
    type: tool
  - id: ai_review
    type: ai_task
    condition: 
      field: "static_issues.count"
      operator: "<", 
      value: 10
```

### 2. **三重状态管理体系**
- **设计**：将单一状态对象拆分为三个职责分明的层次：
  1. **`WorkflowState`**: 内存中完整状态（含变量、执行上下文）
  2. **`WorkflowStatusInfo`**: 对外暴露的精简状态（用于 API 返回）
  3. **`WorkflowHistoryEvent`**: 不可变事件流（用于审计与回放）

- **价值**：
  - **性能分离**：前端查询用轻量 `StatusInfo`，避免加载巨大状态对象。
  - **审计完整**：`HistoryEvent` 记录每一次状态变更，支持时间点回溯。
  - **内存优化**：长期运行的工作流可将完整 `State` 序列化到磁盘，仅保留 `StatusInfo` 在内存。

### 3. **条件与分支决策机制**
- **设计**：
  - 在 `PhaseDefinition` 中增加 `condition` 字段，支持嵌套逻辑表达式。
  - 引擎在 `get_next_phase` 时求值条件，动态决定流程走向。
  - 支持 `Sequential`、`Parallel` 等执行策略。
- **价值**：
  - 实现真正的智能流程：“如果测试覆盖率高，则跳过人工审查”。
  - 支持 Fail-Fast 策略：检测到高风险变更时自动暂停。
  - 为复杂任务的自适应执行提供基础。

```python
if phase.condition and not evaluate_condition(phase.condition, instance.variables):
    # 跳过此阶段或走备用路径
    next_phase = phase.fallback_phase
```

### 4. **渐进式自动化控制**
- **设计**：
  - 引入 `automation_level: int` (0-100) 全局配置。
  - 结合 `risk_assessment` 模块计算操作风险分。
  - 当 `risk_score > (100 - automation_level)` 时，自动进入“等待人工确认”状态。
- **价值**：
  - 用户可根据信任度调节自动化程度（新手设为 30，专家设为 80）。
  - 高风险操作（如删除代码、修改数据库）默认需要人工介入。
  - 实现人机协同的黄金平衡点。

### 5. **Dry Run 模式（安全沙箱）**
- **设计**：
  - `trigger_next_step(dry_run=True)` 不保存任何状态。
  - 返回“模拟推进后”的状态，用于预览下一步。
- **价值**：
  - ChatCoder UI 可实现“预览下一步”功能，提升用户体验。
  - 开发者可在执行耗时 AI 任务前，先验证流程逻辑。
  - 成为调试和测试工作流定义的必备工具。

### 6. **增强型产物管理**
- **设计**：
  - 产物文件与元数据分离：`tasks/phase.json` 存元数据，`artifacts/phase/` 存大文件。
  - 元数据中记录 `prompt_checksum` 和 `response_checksum`。
  - 支持软删除（`deleted_at` 字段），保留审计链。
- **价值**：
  - 便于未来扩展云存储适配器（S3/GCS）。
  - 校验和确保产物未被篡改，增强可信度。
  - 误删可恢复，符合个人使用习惯。

---

## 四、架构优势对比

| 能力 | v1.0 | v1.1 |
|------|------|------|
| **配置安全** | 无验证 | Schema + 类型检查 |
| **流程智能** | 线性 | 条件分支/并行 |
| **执行可控** | 全自动 | 渐进式自动化 |
| **调试体验** | 查日志 | Dry Run 预演 |
| **状态查询** | 慢（读大文件） | 快（精简Status） |
| **审计能力** | 有限 | 完整事件流 |

---

## 五、关键接口演进

### 新增/修改接口
```python
# 1. 启动返回结构化结果
class WorkflowStartResult:
    instance_id: str
    initial_phase: str
    created_at: datetime

def start_workflow_instance(...) -> WorkflowStartResult:

# 2. 支持 Dry Run
def trigger_next_step(
    instance_id: str,
    trigger_data: Optional[Dict] = None,
    dry_run: bool = False,        # 新增
    meta: Optional[Dict] = None
) -> WorkflowInstanceState:

# 3. 获取精简状态（推荐用于UI）
def get_workflow_status_info(self, instance_id: str) -> WorkflowStatusInfo:

# 4. 获取完整历史（用于审计）
def get_workflow_history(self, instance_id: str) -> List[WorkflowHistoryEvent]:
```

### 接口设计哲学
- **向后兼容**：旧版 `get_workflow_instance_status` 仍可用。
- **场景化**：不同接口服务于不同用途（UI 显示 vs 调试审计）。
- **安全第一**：所有状态变更仍需通过 `trigger_next_step`。

---

## 六、存储结构演进

```
.chatflow/
├── schemas/                     # Schema版本化
│   ├── default@v1.0.yaml
│   └── refactor@v1.1.yaml
├── instances/
│   ├── wfi_abc.json             # 精简状态 (StatusInfo)
│   └── wfi_abc/
│       ├── full_state.pkl       # 完整状态 (State) - 可选
│       ├── history.ndjson       # 事件流 (History) - 换行JSON
│       ├── tasks/               # 任务元数据
│       └── artifacts/           # 实际产物文件
├── .indexes/
│   └── feature_index.json       # 性能索引
└── .trash/                      # 软删除暂存
```

> **说明**：`.ndjson` (Newline Delimited JSON) 格式便于流式读取和追加写入，是日志系统的事实标准。

---

## 七、适用场景扩展

✅ **新增适用场景**：
- 需要根据代码质量动态调整流程的 CI/CD 集成
- 多人协作项目中的标准化开发流程
- 高风险操作（生产环境部署）的自动化审批
- AI Agent 自主决策但需人类监督的场景

---

## 总结

ChatFlow v1.1 的成功在于：**在不增加运维复杂性的前提下，极大提升了系统的可信度与智能化水平**。它不再是被动的状态记录者，而是成为了能够**理解意图、评估风险、自主决策、安全执行**的智能协作者。

这套设计体现了：
> **真正的智能不是无所不能，而是在正确的时候做正确的事，并知道何时该寻求帮助**。
