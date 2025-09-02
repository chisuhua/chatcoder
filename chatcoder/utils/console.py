"""
统一的控制台输出工具，基于 rich 实现美观、结构化的 CLI 交互。
"""
from rich.console import Console as RichConsole
from rich.theme import Theme
from rich.highlighter import ReprHighlighter
from typing import Any, Optional

# 自定义主题
CUSTOM_THEME = Theme({
    "info": "cyan bold",
    "success": "green bold",
    "warning": "yellow bold",
    "error": "red bold",
    "heading": "bold underline",
    "path": "magenta",
    "code": "bold white on black",
    "task": "blue",
    "prompt": "green",
})

# 全局控制台实例（单例）
console = RichConsole(theme=CUSTOM_THEME, soft_wrap=True)


# --- 便捷输出函数 ---

def info(message: str):
    """蓝色信息提示"""
    console.print(f"💡 [info]INFO[/info]: {message}")


def success(message: str):
    """绿色成功提示"""
    console.print(f"✅ [success]SUCCESS[/success]: {message}")


def warning(message: str):
    """黄色警告提示"""
    console.print(f"⚠️  [warning]WARNING[/warning]: {message}")


def error(message: str):
    """红色错误提示"""
    console.print(f"❌ [error]ERROR[/error]: {message}")


def heading(title: str):
    """标题输出"""
    console.print(f"\n🎯 [heading]{title}[/heading]\n")


def code_block(code: str, language: str = "text", title: Optional[str] = None):
    """格式化输出代码块"""
    console.print(f"\n[bold]{title}[/bold]" if title else "")
    console.print(f"[code]{code}[/code]")


def print_json(data: Any):
    """美化输出 JSON/字典数据"""
    console.print_json(data)


def debug(obj: Any, title: str = "Debug Output"):
    """调试输出，高亮显示对象结构"""
    highlighter = ReprHighlighter()
    console.print(f"[bold yellow]🐞 {title}:[/bold yellow]")
    console.print(highlighter(str(obj)))


# --- 交互式输入 ---

def prompt_input(prompt: str, default: str = None) -> str:
    """带样式的输入提示"""
    default_str = f" ({default})" if default else ""
    full_prompt = f"📝 [prompt]{prompt}{default_str}:[/prompt] "
    value = console.input(full_prompt)
    return value if value else default


def confirm(prompt: str, default: bool = True) -> bool:
    """确认对话（Y/N）"""
    yes_no = "[Y/n]" if default else "[y/N]"
    full_prompt = f"❓ {prompt} {yes_no}: "
    response = console.input(full_prompt).strip().lower()
    
    if not response:
        return default
    return response in ("y", "yes", "是")


# --- 表格与结构化输出 ---

def print_table(data: list, headers: list = None):
    """打印简单表格"""
    from rich.table import Table
    
    table = Table(
        title="📋 结果列表",
        show_header=True,
        header_style="bold magenta"
    )
    
    if headers:
        for h in headers:
            table.add_column(h)
    else:
        table.add_column("字段")
        table.add_column("值")

    for row in data:
        table.add_row(*[str(cell) for cell in row])
    
    console.print(table)


# --- 任务进度模拟（可替换为 rich.progress） ---

def start_task(name: str):
    """开始任务"""
    console.print(f"🚀 [task]开始任务: {name}[/task]")


def complete_task(name: str):
    """完成任务"""
    console.print(f"🎉 [success]任务完成: {name}[/success]")


# --- 样式化字符串生成（不立即输出） ---

def styled(text: str, style: str) -> str:
    """返回带样式的字符串（用于拼接）"""
    return f"[{style}]{text}[/]"


# --- 兼容性封装 ---

def print(*args, **kwargs):
    """兼容内置 print，使用 rich 输出"""
    console.print(*args, **kwargs)


# --- 初始化欢迎信息 ---

def show_welcome():
    """显示欢迎横幅"""
    console.print("\n" + "═" * 50, style="bold blue")
    console.print("🚀 [bold green]ChatCoder CLI[/bold green] - AI 辅助编程工作流", end="")
    console.print(" 🤖", emoji=True)
    console.print("═" * 50 + "\n", style="bold blue")


# --- 错误上下文输出 ---

def show_error_context(context: dict, message: str):
    """在错误时输出上下文信息"""
    error(message)
    console.print("[bold]上下文信息:[/bold]")
    print_json(context)
