# ChatCoder 智能工作流与动态上下文管理 (WORKFLOW.md - 改进版)

**版本**: 1.1
**状态**: 阶段 0 - 准备与规划 (补充/改进)
**作者**: [您的姓名或团队名称]
**日期**: 2023-10-27
**修订**: 2024-05-22 (基于竞品分析更新)

## 1. 概述

本文档深入阐述 ChatCoder 的两大核心智能化特性：**智能工作流 (Intelligent Workflow)** 和 **动态上下文管理 (Dynamic Context Management)**。这些机制共同作用，旨在将 ChatCoder 从一个静态的提示词生成工具，提升为一个能够根据项目进展、用户指令和 AI 输出内容，智能引导开发流程并提供精准、实时上下文的 AI 辅助开发平台。

**修订说明**:
*   **智能工作流**: 强调了与用户指令的交互、任务分解与规划能力，并借鉴了自主代理（如 Devin）的决策思想。
*   **动态上下文管理**: 明确了上下文的多维度（项目级、任务级、实时编辑级），并强调了上下文的显式选择和精细化管理，借鉴了 Copilot、Cursor 和 Aider 的经验。

## 2. 智能工作流 (Intelligent Workflow)

### 2.1. 目标

智能工作流的目标是为开发者提供一个**结构化但灵活**的开发路径。它不仅定义了标准的开发阶段（如分析、设计、编码、测试），还能根据用户指令、任务执行结果（特别是 AI 的输出内容）以及预设规则，动态调整后续步骤，甚至触发特殊的审查或验证流程。其核心是**在结构化流程中融入智能决策和自主规划能力**。

### 2.2. 核心组件

1.  **工作流定义 (Workflow Schema)**:
    *   **位置**: `ai-prompts/workflows/<workflow_name>.yaml`
    *   **内容**: 定义一个工作流包含哪些阶段（Phase），每个阶段的名称、标题、使用的模板、以及它们之间的顺序关系。支持条件分支和可选阶段。
    *   **示例 (`ai-prompts/workflows/default.yaml`)**:
        ```yaml
        # ai-prompts/workflows/default.yaml
        name: "default"
        description: "Standard development workflow: Analyze -> Design -> Implement -> Test -> Summary"
        phases:
          - name: "analyze"
            title: "需求分析"
            template: "analyze"
          - name: "design"
            title: "架构设计"
            template: "design"
          - name: "implement"
            title: "编码实现"
            template: "implement"
          - name: "test"
            title: "测试用例"
            template: "test"
          - name: "summary"
            title: "总结归档"
            template: "summary"
        ```
    *   **可扩展性**: 用户可以创建自定义的 `.yaml` 文件来定义特定项目或任务类型的工作流，支持更复杂的 DAG（有向无环图）结构。

2.  **工作流引擎 (Workflow Engine)**:
    *   **模块**: `chatcoder/core/engine.py` (`WorkflowEngine` 类)
    *   **职责**:
        *   加载和解析指定的工作流定义文件 (`load_workflow_schema`)。
        *   管理和追踪 **特性 (Feature)** 的整体状态。一个特性通常对应一个用户故事或功能点，它由一系列相关的任务（按阶段划分）组成。
        *   **智能决策与规划 (核心)**:
            *   **基于规则的决策**: 根据已完成任务的结果（尤其是 AI 的文本输出）和预设规则（如关键词匹配），决定下一个最合适的任务阶段（如触发 `security_review`）。
            *   **基于状态的决策**: 根据特性的当前状态（如所有任务都已完成）来决定是否结束流程。
            *   **（未来）基于模型的规划**: 分析用户高层次指令，分解为具体的子任务，并规划执行路径。
        *   **状态查询与推荐**: 提供接口查询特定特性的当前阶段、下一个推荐阶段、完成度等信息 (`get_feature_status`, `recommend_next_phase`)。

3.  **特性状态追踪 (Feature Status Tracking)**:
    *   **机制**: 通过扫描 `.chatcoder/tasks/` 目录下所有与特定 `feature_id` 关联的任务状态文件，聚合这些任务的状态（如 `pending`, `confirmed`, `completed`）来确定整个特性的进度。
    *   **状态计算**:
        *   识别出最后一个状态为 `confirmed` 或 `completed` 的任务对应的阶段。
        *   根据工作流定义和智能决策结果，确定该阶段的下一个阶段。
        *   如果所有阶段都已完成或达到结束条件，则标记特性为完成。

### 2.3. 智能决策与规划流程 (核心逻辑 - 增强)

智能决策是工作流引擎的“大脑”，其能力将逐步增强。

**当前阶段 (规则驱动)**:
1.  **触发点**: 当用户执行 `chatcoder state-confirm <task_id>` 并确认一个任务后，或者在 `chatcoder task-next` 查询推荐任务时。
2.  **分析输入**:
    *   **已确认任务**: 获取刚刚被确认的任务的完整状态，特别是 AI 生成的响应内容 (`context.rendered`)。
    *   **特性状态**: 查询该任务所属 `feature_id` 的当前整体状态 (`get_feature_status`)。
3.  **内容分析 (初期实现)**:
    *   **关键词匹配**: 在已确认任务的 AI 响应 (`context.rendered`) 中搜索预定义的关键词或短语。
        *   **示例规则**:
            *   如果在响应中发现 "security implications" 或 "high-risk change"，则可能需要触发一个 `security_review` 阶段（即使它不在默认工作流中）。
            *   如果发现 "new library" 或 "significant architectural change"，则可能需要一个 `tech_spike` (技术预研) 阶段。
            *   如果发现 "database migration"，则可能需要一个 `migration_plan` 阶段。
4.  **决策**:
    *   **匹配到特殊规则**: 工作流引擎推荐或直接创建一个特殊阶段的任务（如 `security_review`），并将其作为下一个任务。
    *   **未匹配到特殊规则**: 遵循标准工作流定义，推荐下一个顺序阶段的任务。
5.  **输出**: 为 `chatcoder task-next` 或 `chatcoder task-create` 提供明确的建议。

**未来阶段 (自主规划)**:
*   **目标驱动**: 用户输入高层次目标（如“实现用户登录功能”）。
*   **任务分解**: AI/引擎将目标分解为 `analyze` -> `design` -> `implement` -> `test` 等子任务。
*   **动态调整**: 在执行过程中，根据中间结果（如设计文档）和智能决策规则，动态调整后续任务。

### 2.4. 与 CLI 的集成 (增强交互)

*   `chatcoder start <description>`: 根据默认或指定的工作流，创建第一个 `analyze` 阶段的任务。
*   `chatcoder task-next`: 调用工作流引擎的智能决策逻辑，推荐下一个最合适的任务。
*   `chatcoder task-create`: 可以根据工作流引擎的推荐或用户手动指定来创建任务。
*   `chatcoder feature status/list/show`: 展示基于工作流定义和任务状态聚合的特性进度。
*   **(未来)** `chatcoder plan <goal>`: (高级) 根据用户目标，生成并规划任务序列。

## 3. 动态上下文管理 (Dynamic Context Management - 增强版)

### 3.1. 目标

动态上下文管理的目标是确保在 ChatCoder 生成提示词的任何阶段，AI 都能获得**最相关、最适量、最精准**的项目信息。这不仅仅是静态地包含项目名称和框架，而是根据当前任务的类型、阶段、用户显式选择以及 AI 之前的输出，智能地、多维度地调整提供给 AI 的上下文内容。

**借鉴点**:
*   **Copilot/Tabnine**: 强大的实时编辑上下文感知。
*   **Cursor/Aider**: 显式上下文选择和项目级上下文传递。
*   **ChatCoder**: 结构化的项目快照和阶段相关性。

### 3.2. 核心组件与策略 (增强)

1.  **上下文探测器 (Context Detector)**:
    *   **模块**: `chatcoder/core/detector.py`
    *   **职责**: 通过扫描项目根目录下的特定文件（如 `pyproject.toml`, `CMakeLists.txt`, `manage.py`）和文件内容，智能识别项目的类型（如 `python-django`, `cpp-bazel`）。这为后续的上下文生成提供了基础。

2.  **上下文生成器 (Context Generator)**:
    *   **模块**: `chatcoder/core/context.py` (`generate_context_snapshot`)
    *   **职责**: 生成一个结构化的上下文字典，供 Jinja2 模板渲染时使用。未来可扩展为管理多个上下文片段。
    *   **内容来源**:
        *   **用户配置**: 从 `.chatcoder/context.yaml` 和 `.chatcoder/config.yaml` 加载用户手动输入的项目信息。
        *   **自动探测**: 利用 `detector.py` 的结果。
        *   **核心文件摘要**: 根据项目类型或 `config.yaml` 中的 `core_patterns` 配置，扫描关键源代码文件，并提取其结构化的摘要（如类、函数签名、主要逻辑片段）。这极大地丰富了 AI 对项目现有架构和风格的理解。
        *   **(未来) 任务链上下文**: 显式包含前序任务（如 `design` 任务）的关键输出，作为当前任务（如 `implement` 任务）的输入。
        *   **(未来) 显式选择的文件/片段**: 允许用户在 CLI 中指定需要包含在上下文中的特定文件或代码块。
    *   **输出**: 一个包含 `project_name`, `project_language`, `project_type`, `framework`, `core_files` (及其摘要), `context_snapshot` (Markdown 格式汇总) 等字段的字典。未来可包含 `selected_files`, `task_chain_context` 等。

3.  **动态策略 (Dynamic Strategy - 多维度)**:
    *   **概念**: 上下文生成器不是每次都提供相同的内容。它根据多个维度动态调整策略。
    *   **基于阶段的策略 (增强)**:
        *   **`analyze`/`design` 阶段**: 重点提供项目整体上下文，如项目描述、框架、核心文件摘要，帮助 AI 理解全局。
        *   **`implement` 阶段**: 除了整体上下文，重点提供与当前实现直接相关的上下文：
            *   前序 `design` 任务输出的接口定义。
            *   (未来) 用户显式选择的相关文件/代码片段。
            *   核心文件中与实现模块相关的部分。
        *   **`test` 阶段**: 重点提供待测试功能的实现细节（来自 `implement` 阶段任务的上下文或新生成的文件）和项目现有的测试框架、风格信息。
    *   **基于 AI 输出的策略 (未来增强)**:
        *   在 `implement` 阶段后，`ResponseProcessor` 会解析出 AI 建议创建或修改的文件列表。在后续的 `test` 阶段，上下文管理器可以将这些新生成的或被修改的文件内容作为重点上下文提供给 AI，以便它能基于最新的代码来编写测试。
    *   **基于用户显式选择的策略 (新增)**:
        *   在 CLI 命令（如 `chatcoder prompt implement ...`) 中，允许用户通过参数（如 `--context-files src/module.py,tests/`) 显式指定需要包含在上下文中的文件，实现更精确的控制。

### 3.3. 与模板系统的集成 (保持)

*   **模板变量**: `generate_context_snapshot` 生成的字典直接作为变量传递给 Jinja2 模板渲染器。
*   **模板使用**: 模板文件（如 `ai-prompts/workflows/step3-code.md.j2`）通过 `{% include "common/context.md.j2" %}` 将上下文信息嵌入到提示词的开头。
*   **动态包含**: `common/context.md.j2` 模板本身可以根据传入的上下文变量（如 `phase`）有条件地包含不同的信息块，实现更精细的动态控制。

### 3.4. 与 CLI 和状态管理的集成 (增强)

*   `chatcoder context`: 直接调用 `generate_context_snapshot` 并将结果（特别是 `context_snapshot` Markdown 字段）展示给用户，方便调试和验证。
*   `chatcoder prompt <template>`: 在调用 `render_prompt` 时，会自动调用 `generate_context_snapshot` 获取上下文，并将其传入模板渲染过程。**未来可增加参数支持显式上下文**。
*   `chatcoder/core/orchestrator.py` (`TaskOrchestrator`): 保存的任务状态 (`context` 字段) 中不仅包含 AI 的原始输出，未来也可能包含生成该输出时所使用的上下文快照或上下文片段引用，便于追溯和复现。

## 4. 总结

通过智能工作流，ChatCoder 能够在提供清晰结构化路径的同时，根据内容和规则进行智能决策，引导用户完成复杂的任务序列。通过增强的动态上下文管理，ChatCoder 能够在不同阶段、根据不同维度（阶段、任务链、用户选择）提供最精准、最适量的信息给 AI，从而生成更高质量、更贴合项目实际的输出。这两者的结合，使 ChatCoder 成为一个强大且灵活的 AI 驱动开发伙伴，兼具 Cursor/Aider 的交互性和 Copilot 的上下文感知能力，同时保留了自身结构化流程的优势。
