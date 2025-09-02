# chatcoder/core/init.py
"""
项目初始化模块
"""
from pathlib import Path
import jinja2
import click
import yaml

# ------------------------------
# 常量定义
# ------------------------------

# 模板目录：chatcoder/ai-prompts/templates/context/*.yaml
TEMPLATE_DIR = Path(__file__).parent.parent / "ai-prompts" / "templates" / "context"

# 输出文件路径
CONTEXT_FILE = Path(".chatcoder") / "context.yaml"


def load_template(lang: str) -> str:
    """
    加载指定语言的上下文模板

    Args:
        lang: 语言标识，如 "python", "c++", "rust"

    Returns:
        模板字符串

    Raises:
        FileNotFoundError: 若模板文件不存在
    """
    template_path = TEMPLATE_DIR / f"{lang}.yaml"
    if not template_path.exists():
        raise FileNotFoundError(f"未找到语言模板: {template_path}")
    return template_path.read_text(encoding="utf-8")


def render_context_template(lang: str, **values) -> str:
    """
    使用 Jinja2 渲染上下文模板

    Args:
        lang: 语言类型
        **values: 模板变量

    Returns:
        渲染后的 YAML 字符串
    """
    template_str = load_template(lang)

    # 使用字符串加载器，避免文件系统路径问题
    env = jinja2.Environment(
        loader=jinja2.DictLoader({"template": template_str}),
        autoescape=False
    )
    template = env.get_template("template")
    return template.render(**values)


def init_project():
    """
    交互式初始化项目

    创建 .chatcoder 目录，并根据用户输入生成 context.yaml
    """
    # 创建 .chatcoder 目录
    state_dir = Path(".chatcoder")
    state_dir.mkdir(exist_ok=True)

    # 交互式输入
    project_name = Path(".").resolve().name
    lang = click.prompt(
        "选择项目语言",
        type=click.Choice(["python", "c++", "rust"]),
        default="python"
    )

    project_type = click.prompt(
        "项目类型 (cli/web/library)",
        type=click.Choice(["cli", "web", "library"]),
        default="cli"
    )

    framework = click.prompt(f"使用的框架 (可选)", default="")

    if lang == "python":
        ui_library = click.prompt("UI 库 (如 rich/click)", default="")
    else:
        ui_library = ""

    # 渲染模板
    try:
        rendered = render_context_template(
            lang=lang,
            project_name=project_name,
            project_type=project_type,
            framework=framework,
            ui_library=ui_library
        )
    except Exception as e:
        click.echo(f"❌ 模板渲染失败: {e}")
        raise

    # 写入文件
    context_file = state_dir / "context.yaml"
    
    # 检查是否已存在
    if context_file.exists():
        if not click.confirm(f"{context_file} 已存在。是否覆盖？", default=False):
            click.echo("初始化已取消。")
            return

    try:
        context_file.write_text(rendered, encoding="utf-8")
        click.echo(f"✅ 已生成: {context_file}")
        click.echo(f"🔧 项目语言: {lang}")
        click.echo("📌 可使用 `chatcoder prompt` 开始第一个任务")
    except Exception as e:
        click.echo(f"❌ 写入文件失败: {e}")
        raise


# ------------------------------
# 附加功能（可选，未来扩展）
# ------------------------------

def list_available_templates() -> list:
    """
    列出所有可用的语言模板

    Returns:
        语言标识列表
    """
    if not TEMPLATE_DIR.exists():
        return []
    return [f.stem for f in TEMPLATE_DIR.glob("*.yaml")]


def validate_context_file() -> bool:
    """
    验证 context.yaml 是否存在且语法正确

    Returns:
        是否有效
    """
    if not CONTEXT_FILE.exists():
        return False
    try:
        with open(CONTEXT_FILE, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        return True
    except Exception:
        return False
