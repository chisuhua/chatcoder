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

这个计划通过逐步抽象、创建适配器、迁移核心逻辑的方式，可以平稳地将 ChatCoder 演进到您所设想的架构中，同时保证每一步的稳定性和可测试性。
