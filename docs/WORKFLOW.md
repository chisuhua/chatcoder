# ChatCoder 智能工作流与动态上下文管理 (WORKFLOW.md)

**版本**: 1.0
**状态**: 阶段 0 - 准备与规划 (补充)
**作者**: [您的姓名或团队名称]
**日期**: 2023-10-27

## 1. 概述

本文档深入阐述 ChatCoder 的两大核心智能化特性：**智能工作流 (Intelligent Workflow)** 和 **动态上下文管理 (Dynamic Context Management)**。这些机制共同作用，旨在将 ChatCoder 从一个静态的提示词生成工具，提升为一个能够根据项目进展和 AI 输出内容，智能引导开发流程并提供精准上下文的 AI 辅助开发平台。

## 2. 智能工作流 (Intelligent Workflow)

### 2.1. 目标

智能工作流的目标是自动化和优化软件开发任务的流转顺序。它不仅定义了标准的开发阶段（如分析、设计、编码、测试），还能根据任务执行的结果（特别是 AI 的输出内容）动态调整后续步骤，甚至触发特殊的审查或验证流程。

### 2.2. 核心组件

1.  **工作流定义 (Workflow Schema)**:
    *   **位置**: `ai-prompts/workflows/<workflow_name>.yaml`
    *   **内容**: 定义一个工作流包含哪些阶段（Phase），每个阶段的名称、标题、使用的模板、以及它们之间的顺序关系。
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
    *   **可扩展性**: 用户可以创建自定义的 `.yaml` 文件来定义特定项目或任务类型的工作流。

2.  **工作流引擎 (Workflow Engine)**:
    *   **模块**: `chatcoder/core/workflow.py`
    *   **职责**:
        *   加载和解析指定的工作流定义文件 (`load_workflow_schema`)。
        *   管理和追踪 **特性 (Feature)** 的整体状态。一个特性通常对应一个用户故事或功能点，它由一系列相关的任务（按阶段划分）组成。
        *   **智能决策**: 这是核心。根据已完成任务的结果（尤其是 AI 的文本输出）和预设规则，决定下一个最合适的任务阶段是什么。
        *   **状态查询**: 提供接口查询特定特性的当前阶段、下一个推荐阶段、完成度等信息 (`get_feature_status`)。

3.  **特性状态追踪 (Feature Status Tracking)**:
    *   **机制**: 通过扫描 `.chatcoder/tasks/` 目录下所有与特定 `feature_id` 关联的任务状态文件，聚合这些任务的状态（如 `pending`, `confirmed`）来确定整个特性的进度。
    *   **状态计算**:
        *   识别出最后一个状态为 `confirmed` 的任务对应的阶段。
        *   根据工作流定义，确定该阶段的下一个阶段。
        *   如果所有阶段都已完成，则标记特性为完成。

### 2.3. 智能决策流程 (核心逻辑)

智能决策是工作流引擎的“大脑”。其基本流程如下：

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
5.  **输出**: 为 `chatcoder task-next` 或 `chatcoder task-create` 提供明确的建议，例如推荐创建一个 `design` 阶段的任务，或者一个 `security_review` 阶段的任务。

### 2.4. 与 CLI 的集成

*   `chatcoder start <description>`: 根据默认或指定的工作流，创建第一个 `analyze` 阶段的任务。
*   `chatcoder task-next`: 调用工作流引擎的智能决策逻辑，推荐下一个最合适的任务。
*   `chatcoder task-create`: 可以根据工作流引擎的推荐或用户手动指定来创建任务。
*   `chatcoder feature status/list/show`: 展示基于工作流定义和任务状态聚合的特性进度。

## 3. 动态上下文管理 (Dynamic Context Management)

### 3.1. 目标

动态上下文管理的目标是确保在 ChatCoder 生成提示词的任何阶段，AI 都能获得最相关、最适量的项目信息。这不仅仅是静态地包含项目名称和框架，而是根据当前任务的类型、阶段以及 AI 之前的输出，智能地调整提供给 AI 的上下文内容。

### 3.2. 核心组件

1.  **上下文探测器 (Context Detector)**:
    *   **模块**: `chatcoder/core/detector.py`
    *   **职责**: 通过扫描项目根目录下的特定文件（如 `pyproject.toml`, `CMakeLists.txt`, `manage.py`）和文件内容，智能识别项目的类型（如 `python-django`, `cpp-bazel`）。这为后续的上下文生成提供了基础。

2.  **上下文生成器 (Context Generator)**:
    *   **模块**: `chatcoder/core/context.py` (`generate_context_snapshot`)
    *   **职责**: 生成一个结构化的上下文字典，供 Jinja2 模板渲染时使用。
    *   **内容来源**:
        *   **用户配置**: 从 `.chatcoder/context.yaml` 和 `.chatcoder/config.yaml` 加载用户手动输入的项目信息。
        *   **自动探测**: 利用 `detector.py` 的结果。
        *   **核心文件摘要**: 根据项目类型或 `config.yaml` 中的 `core_patterns` 配置，扫描关键源代码文件，并提取其结构化的摘要（如类、函数签名、主要逻辑片段）。这极大地丰富了 AI 对项目现有架构和风格的理解。
    *   **输出**: 一个包含 `project_name`, `project_language`, `project_type`, `framework`, `core_files` (及其摘要), `context_snapshot` (Markdown 格式汇总) 等字段的字典。

3.  **动态策略 (Dynamic Strategy)**:
    *   **概念**: 上下文生成器不是每次都提供相同的内容。它可以根据不同的情况调整策略。
    *   **基于阶段的策略 (初期)**:
        *   **`analyze`/`design` 阶段**: 重点提供项目整体上下文，如项目描述、框架、核心文件摘要，帮助 AI 理解全局。
        *   **`implement` 阶段**: 除了整体上下文，还可以考虑提供更多与当前实现相关的细节。例如，如果前一个 `design` 任务提到了某个特定模块 `UserManager`，则可以尝试在上下文中突出与 `UserManager` 相关的核心文件内容。
        *   **`test` 阶段**: 重点提供待测试功能的实现细节（来自 `implement` 阶段任务的上下文）和项目现有的测试框架、风格信息。
    *   **基于 AI 输出的策略 (未来增强)**:
        *   在 `implement` 阶段后，`ResponseProcessor` 会解析出 AI 建议创建或修改的文件列表。在后续的 `test` 阶段，上下文管理器可以将这些新生成的或被修改的文件内容作为重点上下文提供给 AI，以便它能基于最新的代码来编写测试。

### 3.3. 与模板系统的集成

*   **模板变量**: `generate_context_snapshot` 生成的字典直接作为变量传递给 Jinja2 模板渲染器。
*   **模板使用**: 模板文件（如 `ai-prompts/workflows/step3-code.md.j2`）通过 `{% include "common/context.md.j2" %}` 将上下文信息嵌入到提示词的开头。
*   **动态包含**: `common/context.md.j2` 模板本身可以根据传入的上下文变量（如 `phase`）有条件地包含不同的信息块，实现更精细的动态控制。

### 3.4. 与 CLI 和状态管理的集成

*   `chatcoder context`: 直接调用 `generate_context_snapshot` 并将结果（特别是 `context_snapshot` Markdown 字段）展示给用户，方便调试和验证。
*   `chatcoder prompt <template>`: 在调用 `render_prompt` 时，会自动调用 `generate_context_snapshot` 获取上下文，并将其传入模板渲染过程。
*   `chatcoder/core/state.py`: 保存的任务状态 (`context` 字段) 中不仅包含 AI 的原始输出，未来也可能包含生成该输出时所使用的上下文快照，便于追溯。

## 4. 总结

通过智能工作流，ChatCoder 能够根据开发进展和 AI 的洞察，智能地引导用户完成复杂的任务序列。通过动态上下文管理，ChatCoder 确保 AI 在每个阶段都能获得最相关的信息，从而生成更精准、更贴合项目实际的输出。这两者结合，构成了 ChatCoder 作为 AI 辅助开发“瑞士军刀”的核心竞争力。
