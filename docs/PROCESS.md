# ChatCoder AI 文件修改功能处理流程 (PROCESS.md)

**版本**: 1.0
**状态**: 阶段 0 - 准备与规划
**作者**: [您的姓名或团队名称]
**日期**: 2023-10-27

## 1. 概述

本文档详细描述了 ChatCoder 中 AI 文件修改建议与应用功能的核心处理流程，包括 AI 响应解析、变更集生成、变更应用以及相关的数据存储和配置。

## 2. AI 响应解析与变更集生成 (`ResponseProcessor`)

### 2.1. 目标

从 AI 生成的文本响应 (`rendered_output`) 中识别出符合约定格式的代码块，并将其转换为结构化的 `ChangeSet` 对象。

### 2.2. 流程图 (伪代码)

```python
# chatcoder/core/processor.py (伪代码)

from chatcoder.core.models import Change, ChangeSet
import re # 用于正则表达式匹配

def parse_ai_response(rendered_output: str, source_task_id: str) -> ChangeSet:
    """
    解析 AI 的文本输出，生成 ChangeSet。
    
    Args:
        rendered_output (str): AI 生成的完整文本，通常包含 Markdown。
        source_task_id (str): 生成此响应的任务 ID。
        
    Returns:
        ChangeSet: 包含所有识别出的文件变更的集合。
    """
    change_set: ChangeSet = {
        "changes": [],
        "source_task_id": source_task_id
    }
    
    # 1. 使用正则表达式查找所有 Markdown 代码块
    #    匹配模式: ```<info_string>\n<code_content>\n```
    #    例如: ```python:src/my_module.py\nprint('hello')\n```
    code_block_pattern = re.compile(
        r"```([\w\-\+/#]+):([^\n]+)\n(.*?)```",
        re.DOTALL # 使 . 匹配换行符
    )
    
    matches = code_block_pattern.findall(rendered_output)
    
    # 2. 遍历所有匹配到的代码块
    for match in matches:
        info_string, file_path, new_content = match
        
        # 3. 提取语言标识符和文件路径
        #    info_string 格式: <language>:<relative_file_path>
        #    例如: "python:src/my_module.py"
        parts = info_string.split(':', 1) # 最多分割一次
        if len(parts) != 2:
            # 如果格式不匹配，则跳过此代码块
            continue # 或记录警告日志
            
        language, relative_file_path = parts[0].strip(), parts[1].strip()
        
        # 4. 确定操作类型 (简化版)
        import os
        if os.path.exists(relative_file_path):
            operation = "modify"
        else:
            operation = "create"
            
        # 5. (可选) 提取描述 - 可以从代码块前后文或特定注释中提取
        description = _extract_description_around_block(rendered_output, match) # 需要实现
        
        # 6. 创建 Change 对象
        change: Change = {
            "file_path": relative_file_path,
            "operation": operation,
            "new_content": new_content.rstrip('\n'), # 移除末尾可能的换行符
            "description": description
        }
        
        # 7. 添加到 ChangeSet
        change_set["changes"].append(change)
        
    # 8. 返回最终的 ChangeSet
    return change_set

def _extract_description_around_block(full_text: str, match) -> str:
    """
    (辅助函数) 从完整文本中提取代码块附近的描述性文本。
    这是一个简化的示例，可以根据需要增强。
    """
    # 这里可以实现更复杂的逻辑，例如：
    # - 查找代码块前最近的标题 (## ...)
    # - 查找特定的注释行 (// Description: ...)
    # - 提取代码块前后的几行文本
    # 当前实现返回一个空字符串或简单提示
    return "Description extracted from AI response context (to be implemented)."

# --- 使用示例 (在 prompt_cmd 函数中) ---
# rendered_output = render_prompt(...)
# change_set = parse_ai_response(rendered_output, task_id)
# context_to_save = { "rendered": rendered_output, "change_set": change_set } 
# save_task_state(..., context=context_to_save)
```

### 2.3. 关键点

*   **正则表达式**: 用于精确匹配 ` ```<language>:<file_path>\n<content>\n``` ` 格式的代码块。
*   **操作类型推断**: 通过检查本地文件系统 (`os.path.exists`) 来判断是 `create` 还是 `modify`。
*   **数据结构**: 输出是预定义的 `ChangeSet` 模型。
*   **集成**: 此函数应在 `chatcoder/core/prompt.py` 的 `render_prompt` 之后被调用，其结果应作为 `context` 的一部分传递给 `save_task_state`。

## 3. 变更应用 (`ChangeApplier`)

### 3.1. 目标

将 `ChangeSet` 中定义的文件变更安全、可靠地应用到用户的本地文件系统中。

### 3.2. 流程图 (伪代码)

```python
# chatcoder/core/applier.py (伪代码)

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
from chatcoder.core.models import ChangeSet
from chatcoder.utils.console import success, warning, error # 假设使用现有工具

def apply_changes(
    change_set: ChangeSet, 
    dry_run: bool = False, 
    backup: bool = True, 
    backup_dir: str = ".chatcoder/backups"
) -> bool:
    """
    应用 ChangeSet 中的变更。
    
    Args:
        change_set (ChangeSet): 要应用的变更集。
        dry_run (bool): 如果为 True，则只打印操作而不执行。
        backup (bool): 如果为 True 且 backup_dir 有效，则在修改前备份文件。
        backup_dir (str): 备份文件的存储目录。
        
    Returns:
        bool: 应用是否成功。
    """
    try:
        if not dry_run and backup:
            _ensure_backup_dir(backup_dir)
        
        changes = change_set.get("changes", [])
        
        if not changes:
            if not dry_run:
                print("No changes to apply.")
            return True
            
        for change in changes:
            file_path = change["file_path"]
            operation = change["operation"]
            new_content = change["new_content"]
            
            target_path = Path(file_path)
            
            if dry_run:
                print(f"[DRY RUN] Would {operation} file: {file_path}")
                # 可以打印更多细节，如新内容的前几行
                continue
                
            # --- 执行实际操作 ---
            if operation == "create":
                # 确保父目录存在
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(new_content, encoding='utf-8')
                success(f"Created file: {file_path}")
                
            elif operation == "modify":
                # --- 安全措施 ---
                if backup:
                    _backup_file(target_path, backup_dir)
                    
                # (可选增强) 检查文件是否自 AI 生成后被修改
                # if _is_file_modified_since_ai_response(target_path, ...):
                #     warning(f"File {file_path} has been modified since AI response. Overwriting...")
                
                target_path.write_text(new_content, encoding='utf-8')
                success(f"Modified file: {file_path}")
                
            elif operation == "delete":
                # 初期版本禁用或需要特殊处理
                warning(f"Delete operation is not supported or requires special handling: {file_path}")
                # 可以选择跳过或报错
                # raise NotImplementedError("Delete operation is not yet implemented.")
                
        return True
        
    except Exception as e:
        error(f"Failed to apply changes: {e}")
        return False

def _ensure_backup_dir(backup_dir: str):
    """确保备份目录存在"""
    Path(backup_dir).mkdir(parents=True, exist_ok=True)

def _backup_file(file_path: Path, backup_dir: str):
    """备份单个文件"""
    if file_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = Path(backup_dir) / f"{file_path.name}.bak_{timestamp}"
        shutil.copy2(file_path, backup_path) # copy2 保留元数据
        success(f"Backed up {file_path} to {backup_path}")

# --- 使用示例 (在 state_confirm 函数中) ---
# task_data = load_task_state(task_id)
# change_set_data = task_data.get("context", {}).get("change_set")
# if change_set_data:
#     # 可能需要从字典反序列化为 ChangeSet 模型
#     # change_set = ChangeSet(**change_set_data) 
#     
#     # 预览 (可选)
#     _preview_changes(change_set_data) # 需要实现
#     
#     # 询问用户确认
#     if click.confirm("Apply these changes to your files?"):
#         success = apply_changes(change_set_data, dry_run=False, backup=True)
#         if success:
#             # 更新任务状态
#             task_data["status"] = "confirmed"
#             task_data["confirmed_at"] = datetime.now().isoformat()
#             save_task_state(...) # 保存更新后的状态
#             success("Changes applied and task confirmed.")
#         else:
#             error("Failed to apply changes.")
#     else:
#         print("Changes not applied.")
# else:
#     # 原有逻辑：仅更新状态
#     task_data["status"] = "confirmed"
#     save_task_state(...)
#     success("Task confirmed (no file changes).")
```

### 3.3. 关键点

*   **`dry_run` 模式**: 在实际修改前，让用户预览所有将要执行的操作。
*   **备份机制**: 在修改文件前，将其复制到指定的备份目录，文件名加上时间戳以避免冲突。
*   **操作实现**: `create` 需要创建目录；`modify` 需要备份；`delete` 初期禁用。
*   **错误处理**: 包裹在 `try...except` 中，确保单个文件操作失败不影响整体流程，并提供清晰的错误信息。
*   **集成**: 此逻辑应在 `chatcoder/cli.py` 的 `state-confirm` 命令中被调用。

## 4. 状态存储扩展

### 4.1. 目标

确保 `ChangeSet` 能够与任务的其他元数据一起被持久化存储，并在后续步骤（如 `state-confirm`）中能够被正确加载和使用。

### 4.2. 实现方式

*   **存储位置**: `ChangeSet` 作为 `context` 字典的一个子字段，存储在每个任务的 JSON 状态文件中。
*   **数据格式**: 存储为 JSON 序列化的字典，结构与 `chatcoder/core/models.py` 中定义的 `ChangeSet` 一致。
*   **存储时机**: 在 `chatcoder/core/prompt.py` 的 `prompt_cmd` 函数中，`render_prompt` 生成内容并由 `parse_ai_response` 生成 `ChangeSet` 后，将 `ChangeSet` 作为 `context` 的一个键值对传入 `save_task_state`。

**示例 (在 `chatcoder/cli.py` 的 `prompt_cmd` 中)**:

```python
# ... (在 prompt_cmd 函数内)
try:
    # 4. 渲染提示词 (原有逻辑)
    rendered = render_prompt(
        template=template,
        description=description or " ",
        previous_task=previous_task
    )
    
    # 5. 新增：解析 AI 响应，生成 ChangeSet
    from chatcoder.core.processor import parse_ai_response # 需要实现
    change_set = parse_ai_response(rendered, task_id) # task_id 是当前生成的任务ID
    
    # 6. 准备上下文，包含渲染后的内容和 ChangeSet
    task_context = {
        "rendered": rendered,
        "change_set": change_set # <-- 新增字段
    }

    # 7. 保存任务状态 (修改传入的 context)
    save_task_state(
        task_id=task_id,
        feature_id=feature,
        phase=phase or template,
        template=template,
        description=description or " ",
        context=task_context # <-- 传入更新后的 context
    )
    # ... (后续输出逻辑)
```

*   **加载时机**: 在 `chatcoder/cli.py` 的 `state_confirm` 命令中，调用 `load_task_state` 加载任务数据后，从返回的字典中提取 `context` 字段，并进一步获取其中的 `change_set` 子字段。

**示例 (在 `chatcoder/cli.py` 的 `state_confirm` 中)**:

```python
# ... (在 state_confirm 函数内)
try:
    # 加载任务状态 (原有逻辑)
    with open(task_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 获取当前状态 (原有逻辑)
    current_status = data.get("status", "pending")

    # 如果已经是 confirmed，提示用户 (原有逻辑)
    if current_status == "confirmed":
        # ... (原有逻辑)
        return

    # --- 新增逻辑：检查并应用文件变更 ---
    task_context = data.get("context", {})
    change_set_data = task_context.get("change_set")
    
    if change_set_data and isinstance(change_set_data, dict) and change_set_data.get("changes"):
        # 存在变更集，需要处理
        
        # 1. (可选) 预览变更
        # _preview_changes(change_set_data) # 需要实现此函数
        
        # 2. 询问用户确认
        if click.confirm("AI suggested file changes found. Apply them to your project?"):
            # 3. 调用 ChangeApplier 应用变更
            from chatcoder.core.applier import apply_changes # 需要实现
            success_applied = apply_changes(
                change_set_data, 
                dry_run=False, 
                backup=True # 可配置
            )
            
            if success_applied:
                success("File changes applied successfully.")
            else:
                error("Failed to apply file changes. Task confirmation aborted.")
                return # 停止确认流程
        else:
            print("File changes not applied.")
    else:
        print("No AI-suggested file changes found for this task.")
    
    # --- 更新状态 (原有逻辑 + 可能的增强) ---
    data["status"] = "confirmed"
    from datetime import datetime
    data["confirmed_at"] = datetime.now().isoformat()
    data["confirmed_at_str"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 保存更新后的状态 (原有逻辑)
    with open(task_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    success(f"✅ Task {task_id} has been marked as confirmed.")

except Exception as e:
    error(f"Confirmation failed: {e}")

```

## 5. 配置选项规划

为了使工具更灵活和用户友好，计划添加以下可配置选项。这些选项将存储在 `.chatcoder/config.yaml` 文件中。

### 5.1. 配置项

*   `auto_backup` (boolean, default: `true`)
    *   **描述**: 在应用 AI 建议的文件更改之前，是否自动创建文件备份。
    *   **影响**: 控制 `ChangeApplier` 中的备份行为。
*   `backup_dir` (string, default: `.chatcoder/backups`)
    *   **描述**: 存储备份文件的目录路径。
    *   **影响**: `ChangeApplier` 将使用此路径来存储备份文件。
*   `dry_run_default` (boolean, default: `false`)
    *   **描述**: `state-confirm` 命令在应用更改前是否默认以 `dry-run` 模式运行（即只预览不执行）。
    *   **影响**: 修改 `state-confirm` 命令的默认行为。

### 5.2. 配置加载与使用 (伪代码)

```python
# chatcoder/core/config.py (新文件，用于处理配置)

import yaml
from pathlib import Path
from typing import Dict, Any

CONFIG_FILE = Path(".chatcoder") / "config.yaml"

def load_config() -> Dict[str, Any]:
    """加载 .chatcoder/config.yaml 文件"""
    config = {
        "auto_backup": True,
        "backup_dir": ".chatcoder/backups",
        "dry_run_default": False
    }
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f) or {}
            config.update(user_config)
        except Exception as e:
            # 可以记录警告日志
            print(f"Warning: Failed to load config file {CONFIG_FILE}: {e}. Using defaults.")
    return config

# --- 在 cli.py 的 state_confirm 中使用 ---
# from chatcoder.core.config import load_config
# config = load_config()
# dry_run_flag = config.get("dry_run_default", False) # 或通过 click 选项覆盖
# backup_flag = config.get("auto_backup", True)
# backup_dir = config.get("backup_dir", ".chatcoder/backups")
# ...
# success_applied = apply_changes(
#     change_set_data, 
#     dry_run=dry_run_flag, # 可由命令行参数覆盖
#     backup=backup_flag,
#     backup_dir=backup_dir
# )
```

### 5.3. 用户配置文件示例 (`.chatcoder/config.yaml`)

```yaml
# .chatcoder/config.yaml
project:
  name: "My Awesome Project"
  language: "python"
  type: "cli"

# --- 新增的配置项 ---
auto_backup: true
backup_dir: ".chatcoder/backups"
dry_run_default: false # 设为 true 可增加安全性，每次都需要手动确认执行

# core_patterns: [...] # 已有配置
# exclude_patterns: [...] # 已有配置
```

