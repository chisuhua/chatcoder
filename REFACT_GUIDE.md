好的，这是一个基于您当前 ChatCoder 代码库，逐步演进到 ChatCoder/ChatFlow/ChatContext 分离架构的详细计划。每一步都将确保现有单元测试能够通过。

**演进目标**：

1.  **解耦**：将工作流管理和上下文生成的核心逻辑从 `chatcoder` 主包中分离出来。
2.  **模块化**：创建独立的 `chatflow` 和 `chatcontext` Python 包/库。
3.  **演进性**：`chatcoder` 作为客户端，通过调用 `chatflow` 和 `chatcontext` 来实现其功能。
4.  **兼容性**：每一步都保证现有功能和单元测试的完整性。

**演进计划**

**阶段 0: 准备与评估 (当前状态)**

*   **目标**: 理解当前代码结构，确认单元测试基线。
*   **任务**:
    1.  **代码审查**: 确认当前 `chatcoder/core/engine.py` (工作流相关) 和 `chatcoder/core/context.py` (上下文相关) 的功能范围。
    2.  **测试基线**: 运行所有现有单元测试 (`pytest`)，确保它们全部通过。记录当前测试覆盖率。
    3.  **依赖分析**: 明确 `chatcoder` 主包内各模块之间的依赖关系，特别是 `cli.py` 如何调用 `engine.py` 和 `manager.py`/`context.py`。
*   **产出**: 一份当前架构和测试状态的评估报告。

**阶段 1: 核心逻辑抽象与内聚 (强化 ChatCoder 内部)**

*   **目标**: 在不拆分包的情况下，将工作流和上下文逻辑在 `chatcoder` 内部进一步内聚和抽象，为后续拆分做准备。确保现有功能不变。
*   **任务**:
    1.  **强化 `WorkflowEngine`**:
        *   确保 `WorkflowEngine` 完全封装了与工作流定义 (`load_workflow_schema`)、状态追踪 (`get_feature_status`) 和智能决策 (`determine_next_phase`, `recommend_next_phase`) 相关的所有逻辑。
        *   移除 `chatcoder/core/workflow.py` 中剩余的顶层函数，将功能迁移至 `WorkflowEngine` 类（如果尚未完成）。
        *   确保 `WorkflowEngine` 通过其构造函数或方法接收 `TaskOrchestrator` 实例，而不是直接调用旧的 `state.py` 函数。
    2.  **强化 `Context` 相关逻辑**:
        *   确保 `chatcoder/core/context.py` 中的 `generate_context_snapshot` 是生成上下文信息的唯一入口点。
        *   (可选) 将 `PHASE_SPECIFIC_PATTERNS` 和 `CORE_PATTERNS` 等常量移到 `context.py` 内部或一个专门的配置模块。
        *   确保 `AIInteractionManager` (在 `manager.py` 中) 通过调用 `generate_context_snapshot(phase=...)` 来获取上下文。
    3.  **强化 `TaskOrchestrator`**:
        *   确保所有与任务状态 (`task.json` 文件) 的 CRUD 操作都由 `TaskOrchestrator` 类处理。
        *   移除 `chatcoder/core/state.py` 中的顶层函数（如果它们不再是 `TaskOrchestrator` 的内部实现细节）。
    4.  **更新 CLI 调用**:
        *   确保 `chatcoder/cli.py` 中所有与工作流和上下文相关的命令都通过 `workflow_engine` 和 `ai_manager` (间接调用 `context`) 实例进行。
    5.  **单元测试调整**:
        *   更新针对 `engine.py`, `context.py`, `orchestrator.py` 的单元测试，确保它们测试的是类的公共接口，而不是旧的模块级函数。
        *   如果有直接调用旧模块函数的测试，将其修改为调用相应的服务类实例方法。
    6.  **验证**:
        *   运行所有单元测试，确保全部通过。
        *   手动测试核心 CLI 命令 (`chatcoder start`, `chatcoder prompt`, `chatcoder task-next`, `chatcoder state-confirm`, `chatcoder context`)，确保功能正常。
*   **产出**: 一个内部结构更清晰、模块化程度更高的 `chatcoder` 包，核心逻辑已集中到服务类中。

**阶段 2: 创建 `chatflow` 库骨架**

*   **目标**: 建立 `chatflow` 库的基本目录结构和核心接口，开始将工作流逻辑迁移出去。
*   **任务**:
    1.  **创建新包**:
        *   在项目根目录（与 `chatcoder/` 同级）创建 `chatflow/` 目录。
        *   添加 `chatflow/__init__.py`。
        *   创建 `chatflow/core/` 目录用于核心逻辑。
    2.  **定义核心接口 (API)**:
        *   在 `chatflow/core/` 下创建抽象基类或协议，定义 `chatflow` 库对外暴露的核心能力：
            *   `IWorkflowEngine`: 定义 `load_workflow_schema`, `get_feature_status`, `recommend_next_phase` 等方法的签名。
            *   `IWorkflowStateStore`: 定义 `save_state`, `load_state` 的签名（为后续解耦状态存储做准备）。
            *   `WorkflowInstance`: 定义工作流实例的数据结构模型 (Pydantic 或 dataclass)。
    3.  **创建适配器层 (在 `chatcoder` 内)**:
        *   在 `chatcoder/` 内创建一个新模块，例如 `chatcoder/chatflow_adapter.py`。
        *   创建一个类，例如 `ChatCoderWorkflowEngine`，它实现 `chatflow.core.IWorkflowEngine` 接口。
        *   这个类的内部实现暂时**委托**给现有的 `chatcoder.core.engine.WorkflowEngine` 实例。
            ```python
            # chatcoder/chatflow_adapter.py (conceptual)
            from chatflow.core import IWorkflowEngine
            from chatcoder.core.engine import WorkflowEngine # Current implementation

            class ChatCoderWorkflowEngine(IWorkflowEngine):
                def __init__(self, legacy_workflow_engine: WorkflowEngine):
                    self._legacy_engine = legacy_workflow_engine

                def load_workflow_schema(self, name: str = "default"):
                    return self._legacy_engine.load_workflow_schema(name)

                def get_feature_status(self, feature_id: str, schema_name: str = "default"):
                    return self._legacy_engine.get_feature_status(feature_id, schema_name)

                def recommend_next_phase(self, feature_id: str, schema_name: str = "default"):
                    return self._legacy_engine.recommend_next_phase(feature_id, schema_name)
                # ... implement other methods ...
            ```
    4.  **更新 `chatcoder` 以使用适配器**:
        *   修改 `chatcoder/cli.py`，使其不再直接使用 `chatcoder.core.engine.WorkflowEngine`。
        *   而是实例化 `ChatCoderWorkflowEngine`，并将旧的 `WorkflowEngine` 实例传递给它。
        *   CLI 命令现在调用 `ChatCoderWorkflowEngine` 的方法。
    5.  **单元测试**:
        *   为 `ChatCoderWorkflowEngine` 编写单元测试，确保它正确地委托调用。
        *   运行所有现有测试，确保它们仍然通过。
*   **产出**: `chatflow` 库的骨架和接口定义；`chatcoder` 通过适配器使用 `chatflow` 接口的初步实现。

**阶段 3: 迁移工作流逻辑到 `chatflow`**

*   **目标**: 将实际的工作流管理逻辑从 `chatcoder.core.engine` 迁移到 `chatflow` 库中。
*   **任务**:
    1.  **迁移核心类**:
        *   将 `chatcoder/core/engine.py` 的内容（主要是 `WorkflowEngine` 类）复制到 `chatflow/core/engine.py`。
        *   修改 `chatflow/core/engine.py` 中的导入路径，使其适应新包结构（例如，导入 `chatflow.core.models` 而不是 `chatcoder.core.models`）。
        *   更新 `chatflow/core/engine.py` 中的 `TaskOrchestrator` 依赖方式（可能需要定义 `chatflow` 内部的接口或直接依赖）。
    2.  **实现状态存储接口**:
        *   在 `chatflow/core/` 中创建状态存储的具体实现，例如 `FileWorkflowStateStore`，它实现 `IWorkflowStateStore`。
        *   修改 `chatflow/core/engine.py`，使其依赖 `IWorkflowStateStore` 接口，并在其构造函数中接收一个实例。
    3.  **更新 `chatcoder` 适配器**:
        *   修改 `chatcoder/chatflow_adapter.py`。
        *   不再委托给旧的 `chatcoder.core.engine.WorkflowEngine`。
        *   而是直接使用 `chatflow.core.engine.WorkflowEngine`。
        *   实例化 `chatflow` 的 `WorkflowEngine` 时，需要给它传递一个实现了 `IWorkflowStateStore` 的实例。这个实例可以是专门为 `chatcoder` 设计的，它内部调用 `chatcoder.core.orchestrator.TaskOrchestrator` 来进行实际的状态读写。
            ```python
            # chatcoder/chatflow_adapter.py (updated conceptual)
            from chatflow.core import IWorkflowEngine, WorkflowEngine, IWorkflowStateStore
            from chatcoder.core.orchestrator import TaskOrchestrator

            class ChatCoderWorkflowStateStore(IWorkflowStateStore):
                def __init__(self, task_orchestrator: TaskOrchestrator):
                    self._task_orch = task_orchestrator
                def save_state(self, instance_id, state_data):
                    # Convert state_data to task format and save using task_orchestrator
                    self._task_orch.save_workflow_state(...) # Hypothetical method
                def load_state(self, instance_id):
                    # Load using task_orchestrator and convert to state_data format
                    return self._task_orch.load_workflow_state(...) # Hypothetical method

            class ChatCoderWorkflowEngine(IWorkflowEngine): # Or just use chatflow.WorkflowEngine directly
                def __init__(self, task_orchestrator: TaskOrchestrator):
                    state_store = ChatCoderWorkflowStateStore(task_orchestrator)
                    # Delegate to the real chatflow engine
                    self._engine = WorkflowEngine(state_store=state_store)

                def load_workflow_schema(self, name: str = "default"):
                    return self._engine.load_workflow_schema(name)
                # ... delegate all other methods to self._engine ...
            ```
    4.  **清理 `chatcoder`**:
        *   移除 `chatcoder/core/engine.py` 文件（其功能已迁移）。
        *   更新 `chatcoder` 内其他可能导入 `engine.py` 的模块（如果有的话）。
    5.  **单元测试**:
        *   为 `chatflow` 库的核心功能（`engine.py`, `state_store.py`）编写单元测试。
        *   更新 `chatcoder` 的单元测试，如果它们直接测试了旧 `engine.py` 的行为，需要调整为测试通过 `chatflow` 接口的行为。
        *   运行所有测试，确保通过。
*   **产出**: 独立的 `chatflow` 库，包含工作流引擎和状态管理逻辑；`chatcoder` 通过适配器和状态存储代理与之交互。

**阶段 4: 创建 `chatcontext` 库骨架**

*   **目标**: 建立 `chatcontext` 库的基本目录结构和核心接口。
*   **任务**:
    1.  **创建新包**:
        *   在项目根目录创建 `chatcontext/` 目录。
        *   添加 `chatcontext/__init__.py`。
        *   创建 `chatcontext/core/` 目录。
    2.  **定义核心接口 (API)**:
        *   在 `chatcontext/core/` 下定义接口：
            *   `IContextProvider`: 定义 `provide(context_request) -> ProvidedContext` 方法。
            *   `IContextManager`: 定义 `get_context(request) -> Dict` 方法。
            *   `ContextRequest` 和 `ProvidedContext`: 定义数据模型。
    3.  **创建适配器层 (在 `chatcoder` 内)**:
        *   在 `chatcoder/` 内创建 `chatcoder/chatcontext_adapter.py`。
        *   创建 `ChatCoderContextManager`，实现 `chatcontext.core.IContextManager`。
        *   内部暂时委托给 `chatcoder.core.context.generate_context_snapshot`。
    4.  **更新 `chatcoder` 以使用适配器**:
        *   修改 `chatcoder/core/manager.py` (`AIInteractionManager`)，使其调用 `ChatCoderContextManager` 而不是直接调用 `generate_context_snapshot`。
    5.  **单元测试**:
        *   为适配器编写测试。
        *   运行所有测试，确保通过。
*   **产出**: `chatcontext` 库的骨架和接口定义；`chatcoder` 通过适配器使用 `chatcontext` 接口的初步实现。

**阶段 5: 迁移上下文逻辑到 `chatcontext`**

*   **目标**: 将实际的上下文生成逻辑从 `chatcoder.core.context` 迁移到 `chatcontext` 库中。
*   **任务**:
    1.  **迁移核心逻辑**:
        *   将 `chatcoder/core/context.py` 的内容（`generate_context_snapshot`, `_extract_code_snippet` 等）复制到 `chatcontext/core/context.py`。
        *   根据 `chatcontext` 的接口定义，重构 `generate_context_snapshot` 为 `ContextManager` 类的一个方法，并可能创建基础的 `ContextProvider` 实现（如 `CoreFilesProvider`）。
    2.  **实现 `ContextProvider` 和 `ContextPipeline`**:
        *   在 `chatcontext/core/` 中实现基础的 Providers (如 ProjectInfo, CoreFiles)。
        *   实现 `ContextPipeline` 类，用于编排 Providers。
    3.  **更新 `chatcoder` 适配器**:
        *   修改 `chatcoder/chatcontext_adapter.py`，使其使用真正的 `chatcontext.core.ContextManager`。
    4.  **清理 `chatcoder`**:
        *   移除 `chatcoder/core/context.py`（功能已迁移）。
        *   更新依赖。
    5.  **单元测试**:
        *   为 `chatcontext` 库编写单元测试。
        *   更新 `chatcoder` 的单元测试。
        *   运行所有测试，确保通过。
*   **产出**: 独立的 `chatcontext` 库，包含上下文生成和管理逻辑；`chatcoder` 通过适配器与之交互。

**阶段 6: 完善与优化**

*   **目标**: 完善两个库的功能，优化 `chatcoder` 的集成。
*   **任务**:
    1.  **实现高级功能**:
        *   在 `chatflow` 中实现动态决策、子工作流等高级功能。
        *   在 `chatcontext` 中实现基于 LLM 的提取器、RAG Provider 等高级功能。
    2.  **配置化**:
        *   让 `chatflow` 和 `chatcontext` 的行为可以通过配置文件定制。
    3.  **文档与示例**:
        *   为 `chatflow` 和 `chatcontext` 编写详细的文档和使用示例。
    4.  **最终测试**:
        *   全面运行所有单元测试、集成测试。
        *   进行端到端的手动测试，确保 `chatcoder` 作为客户端能正确使用两个库的所有功能。
*   **产出**: 功能完备、文档齐全的 `chatflow` 和 `chatcontext` 库；一个轻量级、作为客户端的 `chatcoder`。

好的，既然阶段 7.2 的工作（深化重构与优化 `chatflow` 和 `chatcontext`）已经完成，我们现在可以规划后续的演进路径。

**当前状态回顾**:

*   **`chatcoder`**: 作为 CLI 客户端和集成层，通过服务层 (`TaskOrchestrator`, `WorkflowEngine`, `AIInteractionManager`) 与 `chatflow` 和 `chatcontext` 交互。
*   **`chatflow`**: 作为一个独立的库，拥有自己的状态模型 (`WorkflowInstanceState`)、状态存储接口 (`IWorkflowStateStore`) 和文件存储实现 (`FileWorkflowStateStore`)。其核心引擎 (`WorkflowEngine`) 实现了工作流定义加载、实例状态管理 (`start_workflow_instance`, `trigger_next_step`) 和智能阶段推荐 (`recommend_next_phase`)。
*   **`chatcontext`**: 作为一个独立的库，定义了上下文提供者接口 (`IContextProvider`) 和管理器接口 (`IContextManager`)。它实现了 `ProjectInfoProvider` 和 `CoreFilesProvider`，并通过 `ContextManager` 协调它们生成上下文。它接收来自 `chatcoder` (通过 `ContextRequest`) 的项目信息 (`project_type`, `project_name`, `project_language`)。
*   **架构**: 三者之间的职责清晰，`chatcoder` 依赖 `chatflow` 和 `chatcontext`，而后两者相对独立。

**下一步：阶段 7.3 及后续计划**

**阶段 7.3: 增强 `chatflow` 的工作流执行与状态管理**

**目标**: 提升 `chatflow` 作为工作流引擎的核心能力，使其能够更自主地执行任务、管理状态，并与 `chatcoder` 进行更深层次的交互。

**核心任务**:

1.  **强化 `WorkflowEngine.trigger_next_step`**:
    *   **现状**: 当前实现是概念性的，它加载状态、更新历史、前进到下一阶段并保存。
    *   **增强点**:
        *   **状态更新**: 根据传入的 `trigger_data` (例如，AI 的响应) 更新 `WorkflowInstanceState.variables`。
        *   **规则引擎**: 集成一个简单的规则引擎，根据 `trigger_data` 内容决定是否需要暂停、回退、触发特殊阶段或终止工作流。
        *   **外部工具调用**: 允许 `trigger_next_step` 调用外部工具（如代码格式化器、测试运行器）并根据结果更新状态。
        *   **生命周期事件**: 在状态变更时触发事件（例如，进入新阶段、完成任务、失败），允许 `chatcoder` 或其他监听器订阅并作出反应。
    *   **实现**: 修改 `chatflow/core/workflow_engine.py` 中的 `trigger_next_step` 方法，添加上述逻辑。

2.  **实现 `determine_next_phase` 的增强版**:
    *   **现状**: 当前的 `determine_next_phase` 逻辑可能在 `chatflow` 内部或 `chatcoder` 中。
    *   **迁移与增强**: 将智能决策逻辑完全迁移到 `chatflow.core.workflow_engine.WorkflowEngine` 内部，并使其可配置。例如，定义一个规则文件 `rules.yaml`，`WorkflowEngine` 在初始化时加载它，并根据规则文件中的定义进行决策。
    *   **实现**:
        *   在 `chatflow/core/workflow_engine.py` 中实现或增强 `determine_next_phase` 方法。
        *   (可选) 创建 `chatflow/core/rules.py` 来管理规则加载和匹配逻辑。
        *   (可选) 在 `chatflow/core/models.py` 中定义规则的数据模型。

3.  **优化 `FileWorkflowStateStore`**:
    *   **现状**: `list_instances_by_feature` 通过扫描所有 `.json` 文件并检查其内容实现。
    *   **优化点**: 在大型项目中，这可能效率低下。
    *   **实现**:
        *   在 `FileWorkflowStateStore` 中引入一个索引文件（例如 `.chatcoder/workflow_instances/index.json`），记录 `feature_id` 到 `instance_id` 列表的映射。
        *   当 `save_state` 被调用时，同时更新索引文件。
        *   当 `list_instances_by_feature` 被调用时，先读取索引文件，然后只加载与 `feature_id` 关联的实例文件。
        *   需要处理索引文件损坏或不同步的情况（例如，定期重建索引或在加载失败时回退到扫描）。

4.  **文档化与示例**:
    *   为 `chatflow` 库编写详细的文档和示例，说明其设计理念、核心类/接口和基本用法。

**阶段 8: 增强 `chatcontext` 的上下文提供能力**

**目标**: 使 `chatcontext` 能够提供更智能、更动态、更相关的上下文信息。

**核心任务**:

1.  **实现 `TaskAwareFilesProvider`**:
    *   **目标**: 创建一个高级的 `ContextProvider`，它能分析前置任务（特别是 AI 的输出）的内容，提取提及的文件名/函数名，然后针对性地读取和摘要这些文件。
    *   **实现**:
        *   在 `chatcontext/core/providers.py` 中创建 `TaskAwareFilesProvider` 类，实现 `IContextProvider` 接口。
        *   `provide` 方法需要：
            *   从 `ContextRequest` 获取 `previous_outputs` 或通过 `feature_id` 查询历史任务。
            *   分析 AI 输出内容，使用 NLP 或简单的字符串匹配提取文件名、函数名等。
            *   读取这些特定文件/函数的内容。
            *   生成摘要。
            *   返回 `ProvidedContext`。
        *   **依赖**: 可能需要一个代码分析库或简单的 LLM 来辅助提取。

2.  **实现 `RAGProvider` (可选)**:
    *   **目标**: 创建一个 `ContextProvider`，集成 RAG (Retrieval-Augmented Generation) 系统，从知识库中检索相关信息作为上下文。
    *   **实现**:
        *   在 `chatcontext/core/providers.py` 中创建 `RAGProvider` 类，实现 `IContextProvider` 接口。
        *   `provide` 方法需要：
            *   从 `ContextRequest` 获取查询（如 `task_description`）。
            *   调用 RAG 系统进行检索。
            *   将检索到的信息格式化为 `ProvidedContext`。
        *   **依赖**: 需要一个 RAG 系统后端。

3.  **增强 `ContextManager` 的合并策略**:
    *   **目标**: 实现更复杂的上下文合并逻辑，例如基于 `ContextType` 或 `Provider` 优先级的合并。
    *   **实现**:
        *   修改 `chatcontext/core/manager.py` 中的 `_merge_contexts` 方法。
        *   引入合并策略配置，允许用户或 `chatcoder` 指定如何处理来自不同 `Provider` 的同名键。
        *   例如，`GUIDING` 类型的上下文可以覆盖 `INFORMATIONAL` 类型的同名键。

4.  **文档化与示例**:
    *   为 `chatcontext` 库编写详细的文档和示例，说明其设计理念、核心类/接口和基本用法。

**阶段 9: 增强 `chatcoder` 的集成与用户体验**

**目标**: 利用 `chatflow` 和 `chatcontext` 的增强功能，提升 `chatcoder` 作为 CLI 工具的智能性和易用性。

**核心任务**:

1.  **集成 `chatflow` 的增强执行能力**:
    *   **目标**: 让 `chatcoder` 能够触发 `chatflow` 的 `trigger_next_step`，并处理其返回的更新后状态和可能的事件。
    *   **实现**:
        *   修改 `chatcoder/cli.py` 中的命令（如 `task-next`, `task-create`）或创建新命令（如 `task-trigger`）。
        *   调用 `workflow_engine.trigger_next_step`。
        *   处理返回的 `WorkflowInstanceState`，更新 `chatcoder` 的本地任务状态（如果需要）。
        *   (可选) 监听 `chatflow` 触发的事件并作出响应。

2.  **集成 `chatcontext` 的高级 Provider**:
    *   **目标**: 让 `chatcoder` 在调用 `chatcontext` 时，能够传递更多信息给 `ContextRequest`，以便 `TaskAwareFilesProvider` 等高级 `Provider` 能正常工作。
    *   **实现**:
        *   修改 `chatcoder/core/manager.py` (`AIInteractionManager.render_prompt`)。
        *   在构造 `ContextRequest` 时，更精细地填充 `previous_outputs` 和 `user_inputs`。
        *   确保 `chatcoder` 的任务状态 (`task.json`) 包含了 `TaskAwareFilesProvider` 所需的信息（如 AI 输出）。

3.  **增强配置驱动**:
    *   **目标**: 在 `.chatcoder/config.yaml` 中添加更多与 `chatflow` 和 `chatcontext` 相关的配置项。
    *   **实现**:
        *   添加 `chatcontext.core_patterns` 配置项，允许用户自定义文件扫描模式。
        *   添加 `chatflow.rules_file` 配置项，允许用户指定自定义规则文件。
        *   添加 `chatcontext.providers` 配置项，允许用户启用/禁用特定的 `Provider`。
        *   修改 `chatcoder` 和 `chatflow`/`chatcontext` 的代码，使其能够读取并应用这些配置。

4.  **优化 CLI 交互**:
    *   **目标**: 提供更清晰、更智能的 CLI 交互体验。
    *   **实现**:
        *   增强 `chatcoder task-next` 的输出，显示更详细的推荐理由（来自 `chatflow`）。
        *   增强 `chatcoder prompt` 的调试输出，显示从 `chatcontext` 获取的上下文内容。
        *   添加新的 CLI 命令，例如 `chatcoder context show` 来查看当前上下文快照。

**总结**

通过完成阶段 7.3 及后续阶段的工作，我们将把 ChatCoder 项目推向一个新的高度：

*   **`chatflow`** 将成为一个功能强大、可扩展的工作流执行引擎。
*   **`chatcontext`** 将成为一个智能、动态的上下文生成和管理系统。
*   **`chatcoder`** 将成为一个高度集成、用户体验优秀的 AI 辅助开发 CLI 工具。

这将最终实现我们最初设定的目标：构建一个像瑞士军刀一样强大、灵活且智能的 AI 辅助软件开发协作平台。

这个计划通过逐步抽象、创建适配器、迁移核心逻辑的方式，可以平稳地将 ChatCoder 演进到您所设想的架构中，同时保证每一步的稳定性和可测试性。
