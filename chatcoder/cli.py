# chatcoder/cli.py
"""
ChatCoder CLI 主入口（重构版：通过服务层调用）
"""
import click
import json
import yaml # 用于加载配置文件
from datetime import datetime
from pathlib import Path

from rich.panel import Panel
from rich.table import Table

# --- 导入新的服务类 ---
from chatcoder.core.chatcoder import ChatCoder

# --- 导入其他必要的模块 ---
from chatcoder.utils.console import (
    console, info, success, warning, error,
    heading, show_welcome, confirm
)

try:
    from chatcoder.init import init_project as perform_init_project, validate_config_content # 假设函数名已调整
except ImportError:
    # 如果移动了，尝试新的路径
    try:
        from chatcoder.init import init_project as perform_init_project, validate_config_content
    except ImportError:
        # 如果都找不到，可以给出更明确的错误或使用占位符
        def perform_init_project(): raise NotImplementedError("init_project not found")
        def validate_config_content(*args, **kwargs): raise NotImplementedError("validate_config_content not found")
        error("Failed to import initialization functions. Please check chatcoder.init module.")

# --- 导入上下文生成函数 (精简后备) ---
from chatcoder.core.context import generate_project_context_from_data

# ------------------------------
# CLI 主入口
# ------------------------------

@click.group(invoke_without_command=True)
@click.version_option("0.1.0", message="ChatCoder CLI v%(version)s")
@click.pass_context
def cli(ctx):
    """🤖 ChatCoder - AI-Native Development Assistant"""
    show_welcome()
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

# ------------------------------
# 命令 1: init
# ------------------------------
@cli.command()
@click.pass_context
def init(ctx):
    """🔧 初始化项目配置"""
    heading("项目初始化")
    state_dir = Path(".chatcoder")
    config_file = state_dir / "config.yaml"
    context_file = state_dir / "context.yaml"

    if state_dir.exists() and context_file.exists():
        if not confirm("配置已存在，重新初始化将覆盖。继续？", default=False):
            info("已取消")
            return
    try:
        # 调用 init 模块的函数进行交互和渲染 (不执行文件写入)
        config_content, context_content = perform_init_project()

        # CLI 层执行文件系统操作
        state_dir.mkdir(exist_ok=True)

        # 写入 config.yaml
        if config_file.exists():
            if confirm(f"{config_file} 已存在。是否覆盖？", default=False):
                config_file.write_text(config_content, encoding="utf-8")
                success(f"已更新: {config_file}")
            else:
                info(f"跳过更新: {config_file}")
        else:
             config_file.write_text(config_content, encoding="utf-8")
             success(f"已生成: {config_file}")

        # 写入 context.yaml
        if context_file.exists():
            if confirm(f"{context_file} 已存在。是否覆盖？", default=False):
                context_file.write_text(context_content, encoding="utf-8")
                success(f"已更新: {context_file}")
            else:
                info(f"跳过更新: {context_file}")
        else:
             context_file.write_text(context_content, encoding="utf-8")
             success(f"已生成: {context_file}")

        success("初始化完成！")
    except Exception as e:
        error(f"初始化失败: {e}")

# ------------------------------
# 辅助函数：加载 ChatCoder 服务
# ------------------------------

def _load_chatcoder_service() -> ChatCoder:
    """
    辅助函数：加载配置文件并实例化 ChatCoder 服务。
    """
    config_file = Path(".chatcoder") / "config.yaml"
    context_file = Path(".chatcoder") / "context.yaml"

    if not config_file.exists() or not context_file.exists():
        error("配置文件缺失。请先运行 `chatcoder init` 初始化项目。")
        raise click.Abort()

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f) or {}
    except Exception as e:
        error(f"读取 config.yaml 失败: {e}")
        raise click.Abort()

    try:
        with open(context_file, 'r', encoding='utf-8') as f:
            context_data = yaml.safe_load(f) or {}
    except Exception as e:
        error(f"读取 context.yaml 失败: {e}")
        raise click.Abort()

    # 实例化新的 ChatCoder 服务
    return ChatCoder(config_data=config_data, context_data=context_data)

# ------------------------------
# 命令 2: context (使用后备上下文生成)
# ------------------------------

@cli.command()
@click.pass_context
def context(ctx):
    """📚 查看项目上下文 (使用后备生成)"""
    click.echo("🔍 正在生成上下文快照 (后备模式)...\n ")

    try:
        # 1. 加载配置和上下文数据 (复用 _load_chatcoder_service 的加载逻辑)
        config_file = Path(".chatcoder") / "config.yaml"
        context_file = Path(".chatcoder") / "context.yaml"
        config_data = {}
        context_data = {}
        if config_file.exists():
             with open(config_file, 'r', encoding='utf-8') as f:
                 config_data = yaml.safe_load(f) or {}
        if context_file.exists():
             with open(context_file, 'r', encoding='utf-8') as f:
                 context_data = yaml.safe_load(f) or {}

        # 2. 使用精简后的后备函数生成上下文
        snapshot = generate_project_context_from_data(config_data=config_data, context_data=context_data)

        # 3. 输出核心字段 (根据 generate_project_context_from_data 的返回结构调整)
        keys_to_show = [
            "project_language",
            "project_type", # 假设 generate_project_context_from_data 会提供
            "test_runner",
            "format_tool",
            # "core_files", # 来自旧 snapshot
            # "context_snapshot" # 来自旧 snapshot
        ]

        # 打印用户定义和探测到的信息
        for key in keys_to_show:
            value = snapshot.get(key)
            if value and value != "unknown":
                click.echo(f"🔹 {key}: {value}")

        # 打印 context.yaml 中的用户自定义部分
        if context_data:
            click.echo(f"\n### 📝 用户定义: ")
            for k, v in context_data.items():
                if v is not None: # 过滤 None 值
                     click.echo(f"- {k}: {v}")
        else:
             click.echo("- 无用户定义上下文信息 ")

        # 打印 core_patterns (如果有的话)
        core_patterns = snapshot.get("core_patterns")
        if core_patterns:
             click.echo(f"\n### 🔍 配置的 Core Patterns: ")
             for pattern in core_patterns:
                 click.echo(f"- {pattern}")

        # (可选) 打印后备生成的完整快照字符串 (如果函数还生成)
        # snapshot_text = snapshot.get("context_snapshot")
        # if snapshot_text:
        #     click.echo(f"\n{snapshot_text}")

    except Exception as e:
        click.echo(click.style(f"❌ 生成上下文失败: {e}", fg="red"))
        raise click.Abort()


# ------------------------------
# feature 命令组
# ------------------------------
@cli.group()
def feature():
    """Manage features (grouped development workflows)"""
    pass

@feature.command(name="start")
@click.option("--description", "-d", required=True, help="Feature description")
@click.option("--workflow", "-w", default="default", help="Workflow schema to use")
@click.pass_context
def feature_start(ctx, description: str, workflow: str):
    """Start a new feature by creating the first task"""
    chatcoder_service = _load_chatcoder_service()
    try:
        result = chatcoder_service.start_new_feature(description, workflow)
        feature_id = result['feature_id']
        success(f"🚀 Started new feature: {feature_id}")
        console.print(f"📝 Description: {description}", style="white")
        console.print(f"\n💡 Suggested next command:")
        console.print(f"[dim]$[/dim] [cyan]chatcoder task prompt {feature_id}[/cyan]")
    except Exception as e:
        error(f"Failed to start feature: {e}")

@feature.command(name="list")
@click.pass_context
def feature_list(ctx):
    """List all features (grouped by feature_id)"""
    chatcoder_service = _load_chatcoder_service()
    heading("Features List")
    try:
        features_status = chatcoder_service.get_all_features_status()
        if not features_status:
            console.print("No features found.", style="yellow")
            return

        table = Table(title="Features")
        table.add_column("Feature ID", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Status", style="green")
        table.add_column("Progress", style="magenta")

        for feature_info in features_status:
             table.add_row(
                 feature_info.get("feature_id", "N/A"),
                 feature_info.get("description", "N/A"),
                 feature_info.get("status", "unknown"),
                 feature_info.get("progress", "N/A")
             )
        console.print(table)
    except Exception as e:
        error(f"Failed to list features: {e}")

@feature.command(name="status")
@click.argument("feature_id")
@click.pass_context
def feature_status(ctx, feature_id: str):
    """Show detailed status of a specific feature"""
    heading(f"Feature Status: {feature_id}")
    chatcoder_service = _load_chatcoder_service()
    try:
        detail_status = chatcoder_service.get_feature_detail_status(feature_id)
        console.print_json(data=detail_status)
    except Exception as e:
        error(f"Failed to get status for feature {feature_id}: {e}")

# @feature.command(name="delete") ... (如果需要实现)

# ----------------------------
# task 命令组
# ----------------------------
@cli.group()
def task():
    """Manage tasks within a feature"""
    pass

@task.command(name="prompt")
@click.argument("feature_id")
@click.pass_context
def task_prompt(ctx, feature_id: str):
    """Generate prompt for the current active task of a feature"""
    heading(f"Generating prompt for feature: {feature_id}")
    chatcoder_service = _load_chatcoder_service()
    
    try:
        prompt_content = chatcoder_service.generate_prompt_for_current_task(feature_id)
        console.print(Panel(prompt_content, title=f"📋 Prompt for {feature_id}", border_style="blue"))
    except Exception as e:
        error(f"Failed to generate prompt for feature {feature_id}: {e}")

@task.command(name="confirm")
@click.argument("feature_id")
@click.option("--summary", help="Summary of the AI response or work done")
@click.pass_context
def task_confirm(ctx, feature_id: str, summary: str):
    """Confirm the current task for a feature and advance the workflow"""
    chatcoder_service = _load_chatcoder_service()
    
    try:
        result = chatcoder_service.confirm_task_and_advance(feature_id, summary)
        success(f"✅ Task for feature {feature_id} has been confirmed.")
        if result:
            next_phase = result.get('next_phase')
            reason = result.get('reason')
            if next_phase:
                info(f"Recommended next phase: {next_phase} (Reason: {reason})")
                console.print(f"\n💡 Suggested next command:")
                console.print(f"[dim]$[/dim] [cyan]chatcoder task prompt {feature_id}[/cyan] (for next phase)")
        else:
             info(f"Feature {feature_id} might be completed.")
    except Exception as e:
        error(f"Failed to confirm task for feature {feature_id}: {e}")

@task.command(name="preview")
@click.argument("phase_name")
@click.argument("feature_id")
@click.pass_context
def task_preview(ctx, phase_name: str, feature_id: str):
    """(Debug) Preview the prompt for a specific phase of a feature"""
    heading(f"Previewing prompt for phase '{phase_name}' of feature: {feature_id}")
    chatcoder_service = _load_chatcoder_service() # 需要服务来加载 schema 路径
    
    try:
        prompt_content = chatcoder_service.preview_prompt_for_phase(phase_name, feature_id)
        console.print(Panel(prompt_content, title=f"🖼️ Preview Prompt: {phase_name} ({feature_id})", border_style="green"))
    except Exception as e:
        error(f"Failed to preview prompt for phase '{phase_name}' of feature {feature_id}: {e}")

@task.command(name="apply")
@click.argument("feature_id")
@click.argument("response_file", type=click.Path(exists=True))
@click.pass_context
def task_apply(ctx, feature_id: str, response_file: str):
    """Apply an AI response file to the current task of a feature.
    
    \b
    Args:
        feature_id: The ID of the feature.
        response_file: Path to the file containing the AI's response.
    """
    heading(f"Applying AI response for feature: {feature_id}")
    chatcoder_service = _load_chatcoder_service()
    
    try:
        # 读取 AI 响应文件内容
        response_content = Path(response_file).read_text(encoding='utf-8')
        
        # 调用 ChatCoder 服务应用响应
        success_applied = chatcoder_service.apply_task(feature_id, response_content)
        
        if success_applied:
            success(f"AI response from '{response_file}' applied to feature '{feature_id}'.")
        else:
             error(f"Failed to apply AI response for feature {feature_id}.")
        
    except FileNotFoundError:
        error(f"AI response file not found: {response_file}")
    except Exception as e:
        error(f"Failed to apply AI response for feature {feature_id}: {e}")

# ----------------------------
# workflow 命令组
# ----------------------------
@cli.group()
def workflow():
    """Manage workflows"""
    pass

@workflow.command(name="list")
@click.pass_context
def workflow_list(ctx):
    """List all available workflow templates"""
    heading("Available Workflows")
    chatcoder_service = _load_chatcoder_service() # 需要服务来加载 schema 路径
    
    try:
        workflow_names = chatcoder_service.list_available_workflows()
        if not workflow_names:
             console.print("No workflows found.", style="yellow")
             return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan")
        for name in workflow_names:
             table.add_row(name)
        console.print(table)
    except Exception as e:
         error(f"Failed to list workflows: {e}")

# ----------------------------
# 其他辅助命令
# ----------------------------
@cli.command(name="validate")
@click.pass_context
def config_validate(ctx):
    """验证 config.yaml 是否合法"""
    heading("Validating Configuration")
    
    try:
        service = _load_chatcoder_service()
        # 为了简化，我们调用 init 模块的函数来验证文件内容
        config_file = Path(".chatcoder") / "config.yaml"
        content = config_file.read_text(encoding="utf-8")
        validate_config_content(content) # 使用 init.py 的验证函数
        success("配置文件验证通过！")
    except Exception as e:
        error(f"Validation failed unexpectedly: {e}")

# ------------------------------
# 主入口
# ------------------------------
if __name__ == '__main__':
    cli(obj={})
