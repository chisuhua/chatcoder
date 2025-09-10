# chatcoder/core/manager.py
"""
ChatCoder 核心服务 - AI 交互管理器 (AIInteractionManager)
负责与 AI 交互相关的核心操作，主要是提示词的渲染。
现在更新为优先使用 chatcontext 库获取上下文。
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import jinja2
from ..utils.console import console
try:
    from chatcontext.core.manager import ContextManager
    from chatcontext.core.providers import ProjectInfoProvider, CoreFilesProvider
    from chatcontext.core.models import ContextRequest
    CHATCONTEXT_AVAILABLE = True
    # print("✅ [DEBUG] chatcontext library successfully imported.")
except ImportError:
    # 如果 chatcontext 库不可用，则在需要时直接报错
    print("⚠️  Warning: chatcontext library not found. Using legacy context generation.")
    CHATCONTEXT_AVAILABLE = False
    ContextManager = None
    ProjectInfoProvider = None
    CoreFilesProvider = None
    ContextRequest = None

from .context import generate_context_snapshot as legacy_generate_context_snapshot

# 📁 模板根目录（相对于当前文件）
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "ai-prompts"

# 从 prompt.py 复制的别名映射
ALIASES = {
    'context': 'common/context.md.j2',
    'analyze': 'workflows/step1-analyze.md.j2',
    'design': 'workflows/step2-design.md.j2',
    'implement': 'workflows/step3-code.md.j2', # 注意：模板名是 code
    'code': 'workflows/step3-code.md.j2',
    'test': 'workflows/step4-test.md.j2',
    'summary': 'workflows/step5-summary.md.j2',
}


class AIInteractionManager:
    """
    AI 交互管理器，负责管理 ChatCoder 与 AI 模型交互的各个方面，
    核心是提示词的生成和渲染。
    """

    def __init__(self):
        """
        初始化 AI 交互管理器。
        """
        pass

    def _create_jinja_env(self) -> jinja2.Environment:
        """
        创建支持 include 的 Jinja2 环境。
        支持从 ai-prompts/common/ 和 ai-prompts/workflows/ 中加载模板。

        Returns:
            jinja2.Environment: 配置好的 Jinja2 环境。
        """
        loader = jinja2.FileSystemLoader(str(TEMPLATES_DIR))
        env = jinja2.Environment(
            loader=loader,
            autoescape=False,  # Markdown 不需要 HTML 转义
            trim_blocks=True,  # 去除块后的换行
            lstrip_blocks=True, # 去除块前的空白
        )
        return env

    def _resolve_template_path(self, template: str) -> str:
        """
        解析模板路径：支持别名 + 自动补全 .j2 扩展名。

        Args:
            template (str): 用户提供的模板标识符（可能是别名或路径）。

        Returns:
            str: 解析后的相对模板路径。
        """
        if template in ALIASES:
            template = ALIASES[template]

        # 自动补全 .j2 扩展名 (如果路径中没有 .md 或 .j2)
        if not template.endswith(('.j2', '.md')):
            template += '.j2'

        # 注意：与 prompt.py 不同，这里不强制添加 'ai-prompts/' 前缀，
        # 因为 loader 已经基于 TEMPLATES_DIR 了。
        # 如果传入的 template 是相对路径，它应该相对于 TEMPLATES_DIR。
        return template

    def render_prompt(
        self,
        template: str,
        description: str,
        previous_task: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        渲染指定的提示词模板。
        """

        # 1. 解析模板路径
        resolved_rel_path = self._resolve_template_path(template)
        template_file = TEMPLATES_DIR / resolved_rel_path

        if not template_file.exists():
            # 尝试提供更友好的错误信息
            available_templates = self.list_available_templates()
            available_names = [t[0] for t in available_templates if t[0] != "(direct)"]
            available_paths = [t[1] for t in available_templates]
            raise FileNotFoundError(
                f"模板文件不存在: {template_file}\n"
                f"已解析路径: {resolved_rel_path}\n"
                f"模板目录: {TEMPLATES_DIR}\n"
                f"可用别名: {available_names}\n"
                f"可用路径: {available_paths[:5]}..." # 限制列表长度
            )

        try:
            # 2. 计算相对于模板目录的路径，供 Jinja2 使用
            abs_template = os.path.abspath(template_file)
            abs_templates = os.path.abspath(TEMPLATES_DIR)
            rel_path_for_jinja = os.path.relpath(abs_template, abs_templates)
            # 确保路径分隔符是 /（Jinja2 要求）
            rel_path_forward = rel_path_for_jinja.replace("\\", "/")

            # --- 调试信息 ---
            # print(f"🔍 abs_template = {abs_template}")
            # print(f"🔍 abs_templates = {abs_templates}")
            # print(f"✅ [SUCCESS] rel_path_for_jinja = {rel_path_for_jinja}")

            # 3. 使用统一的 Jinja2 环境（支持 include）
            env = self._create_jinja_env()
            jinja_template = env.get_template(rel_path_forward)

            # 4. 生成核心上下文
            context: Dict[str, Any] = {}
            current_phase = kwargs.get('phase')

            if CHATCONTEXT_AVAILABLE:
                try:
                    # 1. 创建 ContextManager 和 Providers
                    cm = ContextManager()
                    cm.register_provider(ProjectInfoProvider())
                    cm.register_provider(CoreFilesProvider())

                    # 2. 构造 ContextRequest
                    #    从 kwargs 或 previous_task 中获取信息
                    workflow_instance_id_from_kwargs = kwargs.get('feature_id') # 获取 feature_id 的值
                    workflow_instance_id = None
                    feature_id = None # 保留 feature_id 变量用于其他可能需要的地方
                    if previous_task and 'feature_id' in previous_task:
                        workflow_instance_id = previous_task['feature_id'] # 使用 previous_task 的 feature_id
                        feature_id = workflow_instance_id # 同时也赋值给 feature_id
                    elif workflow_instance_id_from_kwargs:
                        workflow_instance_id = workflow_instance_id_from_kwargs
                        feature_id = workflow_instance_id_from_kwargs
                    else:
                        # 如果都没有，可以生成一个临时的或使用占位符
                        workflow_instance_id = "temp_workflow_instance_id_for_prompt"
                        feature_id = workflow_instance_id # 保持一致

                    chatcoder_context_snapshot = legacy_generate_context_snapshot() # 调用旧函数获取完整快照
                    project_info_from_snapshot = {
                        "project_name": chatcoder_context_snapshot.get("project_name", "Unknown Project"),
                        "project_language": chatcoder_context_snapshot.get("project_language", "unknown"),
                        "project_type": chatcoder_context_snapshot.get("project_type", "unknown"),
                    }
                    # 3. 创建请求对象
                    context_request = ContextRequest( # <-- 修正后的参数名
                        workflow_instance_id=workflow_instance_id, # <-- 使用正确的参数名
                        phase_name=current_phase or template,       # <-- 其他参数保持不变
                        task_description=description,
                        previous_outputs=previous_task or {},
                        project_name=project_info_from_snapshot["project_name"],
                        project_language=project_info_from_snapshot["project_language"],
                        project_type=project_info_from_snapshot["project_type"],
                        # user_inputs=... # 从 kwargs 中提取
                    )
                    # print(f"✅ [DEBUG] Constructed ContextRequest: {context_request}")

                    # 4. 调用 chatcontext
                    context = cm.get_context(context_request)
                    # print(f"✅ [DEBUG] Successfully retrieved context from chatcontext.")
                except Exception as e:
                    print(f"⚠️  [DEBUG] Error using chatcontext: {e}")
                    # 根据策略决定是回退还是报错
                    # 如果是核心功能依赖 chatcontext，则报错
                    raise RuntimeError(f"Failed to get context from chatcontext: {e}") from e
            else:
                # --- 核心功能依赖 chatcontext，但其不可用 -> 直接报错 ---
                #raise RuntimeError(
                #   "Context-aware prompt generation requires the 'chatcontext' library, "
                #   "but it is not installed or not found. "
                #   "Please install it to proceed with context-aware features. "
                #   "You can install it using: pip install chatcontext"
                #
                print("⚠️  chatcontext not available, falling back to minimal legacy context generation.")
                context = legacy_generate_context_snapshot(phase=current_phase)

            context.update(kwargs)  # 合并额外参数

            # 5. 注入核心变量
            context.update({
                "description": description,
                "previous_task": previous_task,
            })

            # 6. 渲染模板
            rendered = jinja_template.render(**context)
            return rendered.strip()

        except jinja2.TemplateNotFound as e:
            raise FileNotFoundError(f"模板未找到 (Jinja2): {e.name}")
        except jinja2.TemplateError as e:
            console.print(f"[red]❌ 模板渲染失败 (Jinja2): {e}[/red]")
            raise
        except Exception as e:
            console.print(f"[red]❌ 渲染提示词时发生未知错误: {e}[/red]")
            raise

    # --- 便捷方法 (保持不变) ---
    def render_analyze_prompt(self, description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """便捷方法：渲染 analyze 模板"""
        return self.render_prompt("analyze", description, previous_task, **kwargs)

    def render_design_prompt(self, description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """便捷方法：渲染 design 模板"""
        return self.render_prompt("design", description, previous_task, **kwargs)

    def render_implement_prompt(self, description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """便捷方法：渲染 implement 模板"""
        return self.render_prompt("implement", description, previous_task, **kwargs)

    def render_test_prompt(self, description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """便捷方法：渲染 test 模板"""
        return self.render_prompt("test", description, previous_task, **kwargs)

    def render_summary_prompt(self, description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """便捷方法：渲染 summary 模板"""
        return self.render_prompt("summary", description, previous_task, **kwargs)

    # --- 辅助方法 (保持不变) ---
    def list_available_templates(self) -> List[Tuple[str, str, bool]]:
        """
        扫描 ai-prompts 目录，列出所有可用模板。

        Returns:
            List[Tuple[str, str, bool]]: 每个元素为 (别名/标识, 相对路径, 是否存在) 的元组列表。
        """
        templates = []

        # 1. 添加别名映射
        for alias, path in ALIASES.items():
            template_file = TEMPLATES_DIR / path
            exists = template_file.exists()
            templates.append((alias, path, exists))

        # 2. 扫描 common/ 和 workflows/ 目录下的所有 .j2 文件
        search_dirs = ["common", "workflows"]
        for dname in search_dirs:
            search_path = TEMPLATES_DIR / dname
            if not search_path.exists():
                continue
            for file in search_path.rglob("*.j2"):
                rel_path = file.relative_to(TEMPLATES_DIR)
                path_str = str(rel_path).replace("\\", "/")
                # 避免重复 (检查路径是否已作为别名存在)
                if path_str not in [t[1] for t in templates]:
                    templates.append(("(direct)", path_str, True))

        return sorted(templates, key=lambda x: (x[0], x[1]))

    def debug_render(self, template: str, **extra_context):
        """
        调试渲染：显示模板内容、解析路径、上下文、渲染结果。
        (此方法主要用于开发调试，可考虑移至独立的调试模块)
        """
        from ..utils.console import console # 确保导入
        console.print(f"\n[bold blue]🔍 调试模板: {template}[/bold blue]")
        console.print(f"[dim]正在解析模板标识...[/dim]")

        try:
            # 1. 解析路径
            resolved = self._resolve_template_path(template)
            console.print(f"✅ 解析为: [cyan]{resolved}[/cyan]")

            template_file = TEMPLATES_DIR / resolved
            if not template_file.exists():
                console.print(f"[red]❌ 文件不存在: {template_file}[/red]")
                return

            # 2. 读取模板内容
            content = template_file.read_text(encoding="utf-8")
            console.print(f"\n[bold]📄 模板内容:[/bold]")
            console.print("[dim]" + "-" * 60 + "[/dim]")
            # 限制输出长度以避免刷屏
            preview_content = content[:2000] + ("\n...\n(内容过长已截断)" if len(content) > 2000 else "")
            console.print(preview_content)
            console.print("[dim]" + "-" * 60 + "[/dim]")

            # 3. 生成上下文快照 (修改点：尝试传递 phase 进行调试)
            debug_phase = extra_context.get('phase', 'debug_phase') # 默认值
            
            context: Dict[str, Any] = {}
            if CHATCONTEXT_AVAILABLE:
                try:
                    # 简化调试用的 ContextRequest
                    debug_cm = ContextManager()
                    debug_cm.register_provider(ProjectInfoProvider())
                    debug_cm.register_provider(CoreFilesProvider())
                    # (未来可能需要注册调试用的 Provider)
                    debug_request = ContextRequest(
                        feature_id="debug_feature_id",
                        phase_name=debug_phase,
                        task_description="这是一条调试任务描述",
                        previous_outputs=extra_context.get("has_previous", True) and {"task_id": "task_debug_123", "template": "analyze", "description": "上一个调试任务"} or {},
                        user_inputs={} # 可以从 extra_context 获取
                    )
                    context = debug_cm.get_context(debug_request)
                    # print(f"✅ [DEBUG] Debug context retrieved from chatcontext.")
                except Exception as e:
                    print(f"⚠️  [DEBUG] Debug: Error using chatcontext for debug render: {e}.")
                    # 可以选择回退或报错，这里为了调试继续
                    raise RuntimeError(f"Debug: Failed to get context from chatcontext: {e}") from e
            else:
                # 调试时也需要 chatcontext
                raise RuntimeError(
                    "Debug rendering with context requires the 'chatcontext' library, "
                    "but it is not installed or not found. "
                )
            
            context.update(extra_context)
            context.update({
                "description": "这是一条调试任务描述",
                "previous_task": {
                    "task_id": "task_debug_123",
                    "template": "analyze",
                    "description": "上一个调试任务",
                } if extra_context.get("has_previous", True) else None
            })

            console.print(f"\n[bold]🧠 渲染上下文:[/bold]")
            # 限制显示的上下文项数
            context_items = list(context.items())
            for k, v in context_items[:20]:
                if isinstance(v, str) and len(v) > 100:
                    console.print(f"  {k}: [dim]{v[:100]}...[/dim]")
                else:
                    console.print(f"  {k}: {v}")
            if len(context_items) > 20:
                 console.print(f"  ... (共 {len(context_items)} 项上下文，已显示前 20 项)")

            # 4. 渲染
            console.print(f"\n[bold]✨ 正在渲染...[/bold]")
            # 注意：这里调用自身方法，也会传递 kwargs（包括可能的 phase）
            rendered = self.render_prompt(template, context["description"], context["previous_task"], **extra_context)
            console.print(f"\n[bold green]✅ 渲染成功！结果:[/bold green]")
            console.print("[bold]" + "=" * 60 + "[/bold]")
            # 限制输出长度以避免刷屏
            preview_rendered = rendered[:3000] + ("\n...\n(内容过长已截断)" if len(rendered) > 3000 else "")
            console.print(preview_rendered)
            console.print("[bold]" + "=" * 60 + "[/bold]")

        except Exception as e:
            console.print(f"[red]❌ 调试失败: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
