好的，我们来根据你提供的 `chatcoder/cli.py` (Thinker/Coder 架构) 和 `chatflow v1.1.2` 的接口，梳理其提供的 AI 辅助开发工作流命令的完整使用流程。

**核心思想**:

`chatcoder` CLI 的设计围绕 **`feature` (特性)** 这一逻辑概念展开。一个 `feature` 代表一个用户想要完成的开发任务（如“实现用户登录”）。每个 `feature` 对应一个或多个 **`instance` (实例)**，这些实例是 `chatflow` 管理的具体工作流执行过程。用户主要通过 `feature` ID 与系统交互，而 `chatcoder` 内部负责管理具体的 `instance` ID。

**典型 AI 辅助开发工作流命令使用流程**

**1. 项目初始化 (`init`)**

*   **命令**: `chatcoder init`
*   **目的**: 初始化项目，创建 `.chatcoder` 目录和配置文件 (`config.yaml`, `context.yaml`)。
*   **流程**:
    1.  用户运行 `chatcoder init`。
    2.  CLI 通过交互式提示（`click.prompt`）引导用户填写项目基本信息（语言、类型、框架等）。
    3.  CLI 使用这些信息渲染预定义的模板 (`ai-prompts/config.yaml`, `ai-prompts/context.yaml`)。
    4.  CLI 将渲染后的配置文件内容写入 `.chatcoder/config.yaml` 和 `.chatcoder/context.yaml`。
    5.  CLI 创建 `.chatcoder/workflow_instances` 目录用于存储 `chatflow` 的工作流实例状态。
*   **结果**: 项目配置完成，`chatcoder` 可以根据这些配置生成静态上下文。

**2. 启动新特性 (`feature start`)**
*   **命令**: `chatcoder feature start --description "实现用户认证功能"`
*   **目的**: 为一个新的开发任务（特性）启动一个关联的工作流实例。
*   **流程**:
    1.  用户运行 `chatcoder feature start` 并提供任务描述。
    2.  CLI 调用 `_load_thinker_service()` 加载配置并实例化 `Thinker` 服务。
    3.  `Thinker` 内部实例化 `WorkflowEngine` 和 `AIInteractionManager`。
    4.  `Thinker.start_new_feature()` 方法被调用。
    5.  `Thinker` 生成一个唯一的 `feature_id` (例如 `feat_user_authentication`)。
    6.  `Thinker` 调用 `WorkflowEngine.start_workflow_instance()`，传入工作流定义名称（默认或指定）、初始上下文（包含用户描述、探测到的项目类型等）和 `feature_id`。
    7.  `chatflow` 创建一个新的工作流实例 (`instance_id`，例如 `wfi_a1b2c3d4e5f6`)，将其与 `feature_id` 关联，并持久化到 `.chatcoder/workflow_instances/`。
    8.  `Thinker` 返回 `feature_id` 和初始 `instance_id`。
    9.  CLI 打印成功信息和 `feature_id`，并建议下一步命令。
*   **结果**: 一个新的开发任务（`feature`）被创建，关联的工作流实例（`instance`）启动并处于第一个阶段（如 `analyze`）。

**3. 获取当前任务提示词 (`feature task prompt`)**
*   **命令**: `chatcoder task prompt --feature feat_user_authentication` 或 `chatcoder feature task prompt feat_user_authentication`
*   **目的**: 为当前激活的工作流实例的当前阶段生成 AI 提示词。
*   **流程 (使用 `feature task`)**:
    1.  用户运行 `chatcoder feature task prompt feat_user_authentication`。
    2.  CLI 调用 `_load_thinker_service()`。
    3.  `Thinker` 实例被创建。
    4.  CLI 调用 `Thinker.get_active_instance_for_feature("feat_user_authentication")` 获取关联的活动 `instance_id`。
    5.  CLI 实例化 `Coder` 服务（传入 `Thinker` 实例）。
    6.  CLI 调用 `Thinker.generate_prompt_for_current_task(active_instance_id)`。
    7.  `Thinker` 调用 `WorkflowEngine.get_workflow_state(active_instance_id)` 获取当前实例的完整状态 (`WorkflowState`)。
    8.  `Thinker` 调用 `AIInteractionManager.render_prompt_for_feature_current_task()`。
    9.  `AIInteractionManager` (通过 `chatcontext`) 收集静态和动态上下文。
    10. `AIInteractionManager` 使用收集到的上下文和 `WorkflowState` 渲染 Jinja2 模板（如 `ai-prompts/workflows/step1-analyze.md.j2`）。
    11. 渲染后的提示词字符串返回给 CLI。
    12. CLI 使用 `rich` 将提示词高亮显示在终端。
*   **流程 (使用 `task prompt`)**:
    1.  用户运行 `chatcoder task prompt --feature feat_user_authentication`。
    2.  CLI 内部的 `_resolve_instance_id` 辅助函数被调用，它解析 `--feature` 参数，同样调用 `Thinker.get_active_instance_for_feature()` 得到 `active_instance_id`。
    3.  后续步骤与 `feature task prompt` 相同。
*   **结果**: 用户获得一个为当前任务（例如，分析用户认证需求）定制的 AI 提示词。

**4. 执行与交互 (隐式)**
*   **目的**: 用户将生成的提示词复制给 AI 模型（如 Claude, GPT），并与之交互，获取代码、分析或建议。
*   **流程**: 此步骤在 CLI 命令之外进行。用户可能将 AI 的响应保存到一个文件中（例如 `response.txt`）。

**5. 应用 AI 响应 (`feature task apply` 或 `task apply`)**
*   **命令**: `chatcoder task apply --feature feat_user_authentication response.txt` 或 `chatcoder feature task apply feat_user_authentication response.txt`
*   **目的**: 将 AI 生成的代码或文件变更应用到本地项目文件系统中。
*   **流程 (使用 `feature task`)**:
    1.  用户运行 `chatcoder feature task apply feat_user_authentication response.txt`。
    2.  CLI 加载 `Thinker` 服务。
    3.  CLI 通过 `Thinker.get_active_instance_for_feature()` 解析出 `active_instance_id`。
    4.  CLI 实例化 `Coder` 服务（传入 `Thinker` 实例）。
    5.  CLI 读取 `response.txt` 文件内容。
    6.  CLI 调用 `Coder.apply_task(active_instance_id, response_content)`。
    7.  `Coder` 内部调用 `Thinker.ai_manager.parse_ai_response(response_content)` (需要实现) 来解析 AI 响应，提取出文件变更指令（`ChangeSet`）。
    8.  `Coder` 遍历 `ChangeSet` 中的变更（如创建 `auth.py`，修改 `README.md`）。
    9.  `Coder` 根据指令（`create`, `modify`）将内容写入到项目文件系统中。
    10. `Coder` 打印应用过程中的信息和最终结果（成功/失败）。
*   **流程 (使用 `task apply`)**:
    1.  用户运行 `chatcoder task apply --feature feat_user_authentication response.txt`。
    2.  CLI 内部的 `_resolve_instance_id` 辅助函数解析 `--feature` 参数得到 `active_instance_id`。
    3.  后续步骤与 `feature task apply` 相同。
*   **结果**: AI 生成的代码或文件变更被实际写入到用户的项目中。

**6. 确认任务并推进 (`feature task confirm`)**
*   **命令**: `chatcoder task confirm --feature feat_user_authentication --summary "已完成用户认证分析"`
*   **目的**: 告知系统当前任务（由 `active_instance_id` 标识）已完成，并根据工作流定义推进到下一个阶段。
*   **流程 (使用 `feature task`)**:
    1.  用户运行 `chatcoder feature task confirm feat_user_authentication --summary "已完成用户认证分析"`。
    2.  CLI 加载 `Thinker` 服务。
    3.  CLI 通过 `Thinker.get_active_instance_for_feature()` 解析出 `active_instance_id`。
    4.  CLI 调用 `Thinker.confirm_task_and_advance(active_instance_id, summary)`。
    5.  `Thinker` 调用 `WorkflowEngine.trigger_next_step(active_instance_id, trigger_data={"summary": summary})`。
    6.  `chatflow` 根据工作流定义 (`schema.yaml`) 检查条件，确定下一个阶段（例如 `design`）。
    7.  `chatflow` 更新 `WorkflowState`，将 `current_phase` 设置为 `design`，并记录历史。
    8.  `chatflow` 持久化更新后的状态。
    9.  `Thinker` 返回下一个阶段的信息。
    10. CLI 打印确认信息和下一个阶段的名称，并建议继续使用 `feature task prompt` 获取新阶段的提示词。
*   **流程 (使用 `task confirm`)**:
    1.  用户运行 `chatcoder task confirm --feature feat_user_authentication --summary "已完成用户认证分析"`。
    2.  CLI 内部的 `_resolve_instance_id` 辅助函数解析 `--feature` 参数得到 `active_instance_id`。
    3.  后续步骤与 `feature task confirm` 相同。
*   **结果**: 工作流实例的状态更新，进入下一个开发阶段（如 `design`）。用户现在可以为新阶段生成提示词。

**7. 循环/结束**
*   **目的**: 重复执行步骤 3 (获取提示词) -> 4 (AI 交互) -> 5 (应用响应) -> 6 (确认推进)，直到特性开发完成。
*   **流程**: 用户持续使用 `feature task prompt`, `feature task apply`, `feature task confirm` (或对应的 `task ... --feature ...` 命令) 来驱动工作流前进。

**8. 状态查询与管理**
*   **命令**:
    *   `chatcoder feature list`: 列出所有已启动的 `feature_id`。
    *   `chatcoder feature status feat_user_authentication`: 查看与 `feat_user_authentication` 关联的所有 `instance` 的概览状态。
    *   `chatcoder feature delete feat_user_authentication`: 删除 `feature` 及其所有关联的 `instance` 数据。
    *   `chatcoder instance status wfi_a1b2c3d4e5f6`: (调试) 查看特定 `instance_id` 的详细状态。
    *   `chatcoder workflow list`: 列出可用的工作流模板。
*   **目的**: 在整个开发过程中，用户可以随时查询任务状态、管理不需要的任务或查看可用的工作流。
*   **流程**: 这些命令通过调用 `Thinker` 的相应方法（如 `list_all_features`, `get_feature_instances`, `delete_feature`）来与 `chatflow` 的状态存储 (`FileStateStore`) 交互，获取并展示信息。

**总结**

`chatcoder/cli.py` 提供了一套结构清晰、以 `feature` 为中心的命令，引导用户完成从初始化项目、启动任务、与 AI 交互、应用代码变更到推进工作流直至任务完成的完整 AI 辅助开发流程。它巧妙地隐藏了底层 `chatflow` 实例 (`instance_id`) 的复杂性，让用户可以更直观地使用 `feature_id` 进行操作，同时保留了直接操作 `instance_id` 的高级命令以供调试。
