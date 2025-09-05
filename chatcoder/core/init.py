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

TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "ai-prompts" 
CONTEXT_FILE = Path(".chatcoder") / "context.yaml"
CONFIG_FILE = Path(".chatcoder") / "config.yaml"  # 新增

def load_template(template_type: str, lang: str) -> str:
    """
    加载指定类型的模板（config / context）
    """
    template_path = TEMPLATE_DIR /  template_type / f"{lang}.yaml"
    if not template_path.exists():
        raise FileNotFoundError(f"未找到模板: {template_path}")
    return template_path.read_text(encoding="utf-8")


def render_template(template_type: str, lang: str, **values) -> str:
    """渲染模板"""
    template_str = load_template(template_type, lang)
    env = jinja2.Environment(loader=jinja2.DictLoader({"t": template_str}))
    return env.get_template("t").render(**values)

def init_project():
    """
    交互式初始化项目
    """
    state_dir = Path(".chatcoder")
    state_dir.mkdir(exist_ok=True)

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

    # 渲染模板
    try:
        config_rendered = render_template(
            template_type="config",
            lang=lang,
            project_name=project_name,
            project_type=project_type,
            framework=framework,
            ui_library=ui_library
        )
    except Exception as e:
        click.echo(f"❌ 模板渲染失败: {e}")
        raise

    # 写入 config.yaml
    if CONFIG_FILE.exists():
        if not click.confirm(f"{CONFIG_FILE} 已存在。是否覆盖？", default=False):
            click.echo("跳过 config.yaml 生成。")
        else:
            CONFIG_FILE.write_text(config_rendered, encoding="utf-8")
            click.echo(f"✅ 已更新: {CONFIG_FILE}")
    else:
        CONFIG_FILE.write_text(config_rendered, encoding="utf-8")
        click.echo(f"✅ 已生成: {CONFIG_FILE}")

    # 检查是否已存在
    if CONTEXT_FILE.exists():
        if not click.confirm(f"{CONTEXT_FILE} 已存在。是否覆盖？", default=False):
            click.echo("初始化已取消。")
            return

    # 渲染 context.yaml
    try:
        context_rendered = render_template(
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
    
    try:
        CONTEXT_FILE.write_text(context_rendered, encoding="utf-8")
        click.echo(f"✅ 已生成: {CONTEXT_FILE}")
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

def validate_config():
    """
    验证 config.yaml 文件的合法性
    """
    click.echo(f"🔍 正在验证 {CONFIG_FILE}...")

    # 1. 检查文件是否存在
    if not CONFIG_FILE.exists():
        click.echo(click.style("❌ 错误：配置文件不存在。", fg="red"))
        click.echo(f"   请先运行 `chatcoder init` 初始化项目。")
        raise click.Abort()

    # 2. 检查 YAML 语法
    try:
        content = CONFIG_FILE.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
    except Exception as e:
        click.echo(click.style("❌ YAML 语法错误！", fg="red"))
        click.echo(f"   {e}")
        raise click.Abort()

    if data is None:
        click.echo(click.style("⚠️ 警告：config.yaml 为空文件。", fg="yellow"))
        return

    if not isinstance(data, dict):
        click.echo(click.style("❌ 错误：config.yaml 必须是一个 YAML 对象。", fg="red"))
        raise click.Abort()

    # 3. 验证 core_patterns（如果存在）
    if "core_patterns" in data:
        if not isinstance(data["core_patterns"], list):
            click.echo(click.style("❌ 错误：core_patterns 必须是一个列表。", fg="red"))
            click.echo(f"   当前类型: {type(data['core_patterns']).__name__}")
            raise click.Abort()
        else:
            click.echo(click.style(f"✅ core_patterns: 找到 {len(data['core_patterns'])} 个模式", fg="green"))

    # 4. 验证 exclude_patterns（可选）
    if "exclude_patterns" in data:
        if not isinstance(data["exclude_patterns"], list):
            click.echo(click.style("❌ 错误：exclude_patterns 必须是一个列表。", fg="red"))
            click.echo(f"   当前类型: {type(data['exclude_patterns']).__name__}")
            raise click.Abort()
        else:
            click.echo(click.style(f"✅ exclude_patterns: 找到 {len(data['exclude_patterns'])} 个排除模式", fg="green"))

    # 5. 验证 project 字段（可选）
    if "project" in data:
        if isinstance(data["project"], dict):
            lang = data["project"].get("language")
            ptype = data["project"].get("type")
            click.echo(f"📦 项目类型: {lang} / {ptype}")
        else:
            click.echo(click.style("⚠️ 警告：project 字段应为对象", fg="yellow"))

    # ✅ 全部通过
    click.echo(click.style("🎉 配置文件验证通过！", fg="green"))
