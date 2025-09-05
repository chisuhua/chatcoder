# ChatCoder AI 文件修改功能设计文档 (DESIGN.md)

**版本**: 1.0
**状态**: 阶段 0 - 准备与规划
**作者**: [您的姓名或团队名称]
**日期**: 2023-10-27

## 1. 概述

本文档旨在详细规划 ChatCoder 中新增的 AI 文件修改建议与应用功能。该功能允许 ChatCoder 在 `implement` 或 `test` 等阶段，根据 AI 的文本输出，识别出需要新增或修改的文件内容，并在用户确认后，将这些更改安全地应用到本地项目文件中。此功能将极大地提升个人开发效率，使 ChatCoder 成为一个更强大的 AI 辅助开发工具。

## 2. 功能范围

*   **核心功能**: 从 AI 生成的文本响应中解析出文件修改建议，并将其应用于本地文件系统。
*   **支持的操作**:
    *   `create`: 创建新文件。
    *   `modify`: 修改现有文件的内容（通常为替换整个文件内容）。
    *   `delete`: 删除文件（*此操作风险极高，初期版本将禁用或需要特殊且显式的标记和确认*）。
*   **适用项目类型**: 主要支持 Python 和 C++ 项目，设计上应易于扩展到其他语言。
*   **安全机制**: 实现 `dry-run` 预览模式和文件备份机制，确保用户在应用更改前能完全了解其影响，并能在出错时回滚。

## 3. AI 输出格式约定

为了使 ChatCoder 能够可靠地解析 AI 的输出，需要定义一套明确的约定。AI 在生成代码时，必须遵循以下格式来标识文件修改建议：

### 3.1. 代码块标记

AI 必须将需要创建或修改的文件内容放置在特定的 Markdown 代码块中。代码块的 **信息字符串 (info string)** 必须包含目标文件的路径。

*   **格式**: ```` ```<language_identifier>:<relative_file_path> ``
*   **`<language_identifier>`**: 建议使用标准语言标识符，如 `python`, `cpp`, `c`, `yaml`, `json` 等。这主要用于语法高亮，但也可作为辅助判断依据。
*   **`<relative_file_path>`**: 目标文件相对于项目根目录的路径。路径分隔符统一使用 `/`。

**示例 (Python)**:

````markdown
为了实现这个功能，我们需要创建一个核心模块和一个配置文件。

```python:src/my_project/core.py
# src/my_project/core.py
def process_data(data):
    # 核心处理逻辑
    return data.upper()

def validate_input(input_data):
    # 输入验证逻辑
    if not input_data:
        raise ValueError("Input data cannot be empty")
    return True
```

```yaml:config/settings.yaml
# config/settings.yaml
processing:
  enabled: true
  mode: "strict"
```
````

**示例 (C++)**:

````markdown
根据设计，我们需要实现 `Calculator` 类。

```cpp:src/calculator.cpp
// src/calculator.cpp
#include "calculator.h"

int Calculator::add(int a, int b) {
    return a + b;
}

int Calculator::subtract(int a, int b) {
    return a - b;
}
```

```cpp:src/calculator.h
// src/calculator.h
#ifndef CALCULATOR_H
#define CALCULATOR_H

class Calculator {
public:
    int add(int a, int b);
    int subtract(int a, int b);
};

#endif // CALCULATOR_H
```
````

### 3.2. 解析规则

1.  **识别**: ChatCoder 的 `ResponseParser` 将扫描 AI 输出中的所有 Markdown 代码块 (```` ``` ... ``` ````)。
2.  **匹配**: 检查代码块的 info string 是否符合 `<language>:<file_path>` 的模式。
3.  **提取**:
    *   提取 `file_path`。
    *   提取代码块的完整内容作为 `new_content`。
4.  **推断操作**:
    *   如果 `file_path` 指向的文件在本地 **已存在**，则推断操作为 `modify`。
    *   如果 `file_path` 指向的文件在本地 **不存在**，则推断操作为 `create`。
5.  **生成 `Change` 对象**: 将提取和推断的信息封装成一个 `Change` 数据结构。

## 4. 数据结构定义 (ChangeSet)

为了在系统内部传递和存储文件修改信息，定义以下核心数据结构。

### 4.1. `Change`

代表对单个文件的一次操作。

```python
# chatcoder/core/types.py 或 chatcoder/core/models.py

from typing import TypedDict, Optional

class Change(TypedDict):
    """
    描述对单个文件的一次变更操作。
    """
    file_path: str          # 目标文件的相对路径 (e.g., "src/my_module.py")
    operation: str          # 操作类型: "create", "modify"
    new_content: str        # 新的文件内容 (用于 create 和 modify)
    description: Optional[str] # (可选) 对此变更的简短描述 (来自AI输出或上下文)

# 注意：初期不包含 "delete" 操作
```

### 4.2. `ChangeSet`

代表一次 AI 响应中包含的所有文件变更集合。

```python
# chatcoder/core/types.py 或 chatcoder/core/models.py

from typing import List

class ChangeSet(TypedDict):
    """
    描述一次 AI 响应中包含的所有文件变更。
    """
    changes: List[Change]       # 变更列表
    source_task_id: Optional[str] # 生成此变更集的 ChatCoder 任务 ID
```

## 5. 核心模块设计

### 5.1. `ResponseProcessor` (响应处理器)

*   **职责**: 解析 AI 的原始文本输出，识别并提取文件修改建议，生成 `ChangeSet`。
*   **输入**: AI 的原始文本响应 (`str`)。
*   **输出**: 结构化的 `ChangeSet` 对象。
*   **关键逻辑**:
    1.  使用正则表达式或 Markdown 解析库遍历所有代码块。
    2.  对每个代码块，检查其 info string 是否匹配 `<language>:<file_path>` 模式。
    3.  如果匹配，提取 `file_path` 和 `new_content`。
    4.  根据 `file_path` 是否存在，确定 `operation` (`create` 或 `modify`)。
    5.  创建 `Change` 对象并加入列表。
    6.  将列表包装成 `ChangeSet` 并返回。

### 5.2. `ChangeApplier` (变更应用器)

*   **职责**: 将 `ChangeSet` 安全地应用到本地文件系统。
*   **输入**: `ChangeSet` 对象, 应用选项 (如 `dry_run: bool`, `backup: bool`)。
*   **输出**: 应用结果 (成功/失败信息, 日志)。
*   **关键逻辑**:
    1.  **(安全) 备份**: 如果 `backup=True` 且操作是 `modify`:
        *   为每个将被修改的文件创建备份 (例如，复制到 `.chatcoder/backups/` 目录，文件名可加时间戳)。
    2.  **遍历 `changes`**:
        *   **`dry_run=True`**: 打印将要执行的操作 (例如，“Would create file: src/new_file.py”，“Would modify file: src/existing_file.py”)。
        *   **`dry_run=False`**:
            *   **`operation == "create"`**:
                *   确保父目录存在 (`os.makedirs(..., exist_ok=True)`)。
                *   将 `new_content` 写入 `file_path`。
                *   记录成功信息。
            *   **`operation == "modify"`**:
                *   (可选增强：检查文件自 AI 生成后是否被手动修改过，若修改则警告)。
                *   将 `new_content` 写入 `file_path`。
                *   记录成功信息。
            *   **`operation == "delete"`**: (初期禁用或需要特殊处理)。
    3.  **(可选) 日志**: 记录应用了哪些任务的变更集。

## 6. 状态存储扩展

为了在 `state-confirm` 阶段能够访问和应用之前生成的 `ChangeSet`，需要将其存储在任务状态中。

*   **位置**: 在 `Task` 状态 JSON 的顶层或 `context` 字段下增加一个 `change_set` 字段。
*   **格式**: 存储完整的 `ChangeSet` 对象 (序列化为 JSON)。

**示例任务状态 JSON 扩展**:

```json
{
  "task_id": "tsk_1234567890_abcdef",
  "template": "implement",
  "feature_id": "feat_user_login",
  "description": "Implement user authentication logic",
  "phase": "implement",
  "phase_order": 3,
  "workflow": "default",
  "created_at": "2023-10-27T10:00:00Z",
  "created_at_str": "2023-10-27 10:00:00",
  "status": "ai_response_received", 
  "context": {
    "rendered": "... AI生成的完整提示词和响应内容 ..."
  },
  // --- 新增字段 ---
  "change_set": {
    "changes": [
      {
        "file_path": "src/auth.py",
        "operation": "create",
        "new_content": "# src/auth.py\n\ndef login(username, password):\n    # TODO: Implement login logic\n    pass\n",
        "description": "Created authentication module"
      }
    ],
    "source_task_id": "tsk_1234567890_abcdef"
  }
  // --- 新增字段结束 ---
}
```

## 7. 人机交互流程

1.  **生成**: 用户执行 `chatcoder prompt implement ...`，AI 生成响应，`ResponseProcessor` 解析并生成 `ChangeSet`，随任务状态一起保存。
2.  **预览**: 用户执行 `chatcoder state-confirm <task_id>`。
    *   系统加载任务状态，检查是否存在 `change_set`。
    *   如果存在，调用 `ChangePreviewer` (待实现，可简单打印 diff 或文件列表) 展示即将进行的更改。
3.  **确认**: 系统询问用户是否应用更改。
    *   用户确认后，调用 `ChangeApplier` 应用更改 (默认 `dry_run=False`)。
    *   用户可以选择 `dry-run` 模式再次预览。
4.  **应用**: `ChangeApplier` 执行文件操作（可能先备份），更新任务状态为 `confirmed`。

## 8. 安全与配置

*   **备份**: 默认启用。备份目录可配置 (默认 `.chatcoder/backups`)。
*   **Dry-run**: `state-confirm` 命令应支持 `--dry-run` 选项，或全局配置默认为 dry-run 预览。
*   **配置项规划** (将在后续阶段实现):
    *   `auto_backup` (bool, default: `true`)
    *   `backup_dir` (str, default: `.chatcoder/backups`)
    *   `dry_run_default` (bool, default: `false`)

## 9. 后续阶段规划指引

完成此设计文档后，可以开始进行后续的编码阶段：

*   **阶段 1**: 架构重构与模块解耦 (同之前)。
*   **阶段 2**: 实现 `ResponseProcessor` 模块，完成 AI 响应解析和 `ChangeSet` 生成逻辑，并将其集成到 `prompt` 命令的流程中，保存到任务状态。
*   **阶段 3**: 实现 `ChangeApplier` 模块，增强 `state-confirm` 命令以支持预览和应用 `ChangeSet`。
*   **阶段 4**: 配置、优化与扩展 (完善)。


