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

# --- 强依赖 chatcontext ---
try:
    from chatcontext.core.manager import ContextManager
    from chatcontext.core.models import ContextRequest
    CHATCONTEXT_AVAILABLE = True
except ImportError as e:
    CHATCONTEXT_AVAILABLE = False
    raise RuntimeError(
        "chatcontext library is required for AIInteractionManager but is not available. "
        "Please ensure it is installed correctly. "
        "Error: " + str(e)
    ) from e

# 导入 chatflow 以便访问状态
try:
    from chatflow.core.models import WorkflowInstanceState
    CHATFLOW_AVAILABLE = True
except ImportError:
    CHATFLOW_AVAILABLE = False
    WorkflowInstanceState = Dict # type: ignore

# 📁 模板根目录（相对于当前文件）
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "ai-prompts"

# 从 prompt.py 复制的别名映射
ALIASES = {
    'context': 'common/context.md.j2',
    'analyze': 'workflows/step1-analyze.md.j2',
    'design': 'workflows/step2-design.md.j2',
    'implement': 'workflows/step3-code.md.j2',
    'code': 'workflows/step3-code.md.j2',
    'test': 'workflows/step4-test.md.j2',
    'summary': 'workflows/step5-summary.md.j2',
}

class AIInteractionManager:
    """
    AI 交互管理器。
    """

    def __init__(self):
        """
        初始化 AI 交互管理器。
        """
        if not CHATCONTEXT_AVAILABLE:
            raise RuntimeError("chatcontext is required but not available.")
        self.context_manager = ContextManager()

    def _create_jinja_env(self) -> jinja2.Environment:
        loader = jinja2.FileSystemLoader(str(TEMPLATES_DIR))
        env = jinja2.Environment(
            loader=loader,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        return env

    def _resolve_template_path(self, template: str) -> str:
        if template in ALIASES:
            template = ALIASES[template]
        if not template.endswith(('.j2', '.md')):
             template += '.j2'
        return template

    def render_prompt(
        self,
        template: str,
        description: str,
        feature_id: Optional[str] = None,
        current_task_state: Optional[WorkflowInstanceState] = None, # type: ignore
        phase: Optional[str] = None,
        is_preview: bool = False,
        is_for_current_task: bool = False,
        **kwargs
    ) -> str:
        """
        渲染指定的提示词模板。
        """
        resolved_rel_path = self._resolve_template_path(template)
        template_file = TEMPLATES_DIR / resolved_rel_path

        if not template_file.exists():
            available_templates = self.list_available_templates()
            available_names = [t[0] for t in available_templates if t[0] != "(direct)"]
            available_paths = [t[1] for t in available_templates]
            raise FileNotFoundError(
                f"模板文件不存在: {template_file}\n"
                f"已解析路径: {resolved_rel_path}\n"
                f"模板目录: {TEMPLATES_DIR}\n"
                f"可用别名: {available_names}\n"
                f"可用路径: {available_paths[:5]}..."
            )

        try:
            abs_template = os.path.abspath(template_file)
            abs_templates = os.path.abspath(TEMPLATES_DIR)
            rel_path_for_jinja = os.path.relpath(abs_template, abs_templates).replace("\\", "/")

            env = self._create_jinja_env()
            jinja_template = env.get_template(rel_path_for_jinja)

            context: Dict[str, Any] = {}
            
            if CHATCONTEXT_AVAILABLE and feature_id:
                try:
                    workflow_instance_id = feature_id
                    
                    task_description_from_state = None
                    phase_from_state = None
                    if current_task_state:
                         chatcoder_vars = current_task_state.variables.get("chatcoder_data", {}) # type: ignore
                         task_description_from_state = chatcoder_vars.get("description")
                         phase_from_state = current_task_state.current_phase # type: ignore

                    context_request = ContextRequest(
                        workflow_instance_id=workflow_instance_id,
                        phase_name=phase or phase_from_state or template,
                        task_description=description or task_description_from_state or "未提供描述",
                        is_preview=is_preview,
                        is_for_current_task=is_for_current_task
                        # previous_outputs 和 user_inputs 可以从 kwargs 或 chatcontext 内部逻辑获取
                    )

                    context = self.context_manager.get_context(context_request)
                except Exception as e:
                    raise RuntimeError(f"Failed to get context from chatcontext: {e}") from e
            else:
                raise RuntimeError(
                    "Context-aware prompt generation requires the 'chatcontext' library and a 'feature_id'. "
                )

            context.update(kwargs)  
            context.update({
                 "description": description,
                 # "previous_task": previous_task, # 由 chatcontext 提供或在 kwargs 中
            })

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

    # --- 新增方法：为特性当前任务生成提示词 ---
    def render_prompt_for_feature_current_task(self, feature_id: str, **additional_context_kwargs) -> str:
        return self.render_prompt(
            template="", # 由 chatcontext 决定
            description="", # 由 chatcontext 决定
            feature_id=feature_id,
            is_for_current_task=True,
            **additional_context_kwargs
        )

    # --- 新增方法：预览特性特定阶段的提示词 ---
    def render_prompt_for_feature_phase_preview(self, feature_id: str, phase_name: str, **additional_context_kwargs) -> str:
        return self.render_prompt(
            template=phase_name, # 预览时通常直接使用 phase_name 作为模板
            description=f"Preview task for feature {feature_id} in phase {phase_name}",
            feature_id=feature_id,
            phase=phase_name, # 明确传递 phase
            is_preview=True, # 传递预览标志
            **additional_context_kwargs
        )

    # --- 辅助方法 ---
    def list_available_templates(self) -> List[Tuple[str, str, bool]]:
        templates = []
        for alias, path in ALIASES.items():
            template_file = TEMPLATES_DIR / path
            exists = template_file.exists()
            templates.append((alias, path, exists))

        search_dirs = ["common", "workflows"]
        for dname in search_dirs:
            search_path = TEMPLATES_DIR / dname
            if not search_path.exists():
                continue
            for file in search_path.rglob("*.j2"):
                rel_path = file.relative_to(TEMPLATES_DIR)
                path_str = str(rel_path).replace("\\", "/")
                if path_str not in [t[1] for t in templates]:
                    templates.append(("(direct)", path_str, True))
        return sorted(templates, key=lambda x: (x[0], x[1]))

    # --- debug_render 方法已被移除 ---
    # def debug_render(self, ...): 
    #     ... 
