# chatcoder/init.py
# (从 chatcoder/core/init.py 移动而来)
"""
项目初始化模块 (CLI 层交互与渲染)
此模块负责通过 CLI 交互收集信息并渲染配置文件内容。
文件的实际创建操作由 CLI 层 (chatcoder/cli.py) 执行。
"""

from pathlib import Path
import jinja2
import click
import yaml

# ------------------------------
# 常量定义 (相对于新位置)
# ------------------------------

# 注意：TEMPLATE_DIR 现在相对于 chatcoder/init.py
TEMPLATE_DIR = Path(__file__).parent / "templates" / "ai-prompts" 
# CONTEXT_FILE 和 CONFIG_FILE 不再在此模块中直接使用，因为文件操作移至 cli.py
# CONTEXT_FILE = Path(".chatcoder") / "context.yaml"
# CONFIG_FILE = Path(".chatcoder") / "config.yaml"

def load_template(template_type: str, lang: str) -> str:
    """加载指定类型的模板（config / context）"""
    template_path = TEMPLATE_DIR / template_type / f"{lang}.yaml"
    if not template_path.exists():
        raise FileNotFoundError(f"未找到模板: {template_path}")
    return template_path.read_text(encoding="utf-8")


def render_template(template_type: str, lang: str, **values) -> str:
    """渲染模板"""
    template_str = load_template(template_type, lang)
    env = jinja2.Environment(loader=jinja2.DictLoader({"t": template_str}))
    return env.get_template("t").render(**values)

# --- 修改点：init_project 不再执行文件 I/O ---
def init_project() -> tuple[str, str]:
    """
    交互式初始化项目，返回渲染好的 config 和 context 内容字符串。
    文件创建操作由调用者 (cli.py) 负责。
    """
    # 交互输入
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

    # 渲染模板内容
    config_content = ""
    context_content = ""
    try:
        config_content = render_template(
            template_type="config",
            lang=lang,
            project_name=project_name,
            project_type=project_type,
            framework=framework,
            ui_library=ui_library
        )
    except Exception as e:
        click.echo(f"❌ config 模板渲染失败: {e}")
        raise

    try:
        context_content = render_template(
            template_type="context",
            lang=lang,
            project_name=project_name,
            project_type=project_type,
            framework=framework,
            ui_library=ui_library
        )
    except Exception as e:
        click.echo(f"❌ context 模板渲染失败: {e}")
        raise
    
    return config_content, context_content

# --- 保留验证函数 ---
def validate_config_content(content: str):
    """验证配置内容字符串的合法性"""
    click.echo(f"🔍 正在验证配置内容... ")
    try:
        data = yaml.safe_load(content)
    except Exception as e:
        click.echo(click.style("❌ YAML 语法错误！", fg="red"))
        click.echo(f"   {e}")
        raise click.Abort()

    if data is None:
        click.echo(click.style("⚠️ 警告：配置内容为空。", fg="yellow"))
        return

    if not isinstance(data, dict):
        click.echo(click.style("❌ 错误：配置内容必须是一个 YAML 对象。", fg="red"))
        raise click.Abort()

    if "core_patterns" in data:
        if not isinstance(data["core_patterns"], list):
            click.echo(click.style("❌ 错误：core_patterns 必须是一个列表。", fg="red"))
            click.echo(f"   当前类型: {type(data['core_patterns']).__name__}")
            raise click.Abort()
        else:
            click.echo(click.style(f"✅ core_patterns: 找到 {len(data['core_patterns'])} 个模式", fg="green"))

    if "exclude_patterns" in data:
        if not isinstance(data["exclude_patterns"], list):
            click.echo(click.style("❌ 错误：exclude_patterns 必须是一个列表。", fg="red"))
            click.echo(f"   当前类型: {type(data['exclude_patterns']).__name__}")
            raise click.Abort()
        else:
            click.echo(click.style(f"✅ exclude_patterns: 找到 {len(data['exclude_patterns'])} 个排除模式", fg="green"))

    if "project" in data:
        if isinstance(data["project"], dict):
            lang = data["project"].get("language")
            ptype = data["project"].get("type")
            click.echo(f"📦 项目类型: {lang} / {ptype}")
        else:
            click.echo(click.style("⚠️ 警告：project 字段应为对象", fg="yellow"))

    click.echo(click.style("🎉 配置内容验证通过！", fg="green"))

# --- 保留其他辅助函数 ---
def list_available_templates() -> list:
    """列出所有可用的语言模板"""
    if not TEMPLATE_DIR.exists():
        return []
    return [f.stem for f in TEMPLATE_DIR.glob("*.yaml")]

# validate_context_file 不再需要，因为内容由 cli.py 传递
