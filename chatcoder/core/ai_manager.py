# chatcoder/core/ai_manager.py
import os
from pathlib import Path
from typing import Dict, Any, Optional
import jinja2

try:
    from chatflow.core.models import WorkflowState
    CHATFLOW_AVAILABLE = True
except ImportError:
    CHATFLOW_AVAILABLE = False
    raise RuntimeError("chatflow library is required.")

from .context_manager import ContextManagerAdapter
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
    def __init__(self):
        self.context_adapter = ContextManagerAdapter()
        self.env = self._create_jinja_env()

    def _create_jinja_env(self) -> jinja2.Environment:
        loader = jinja2.FileSystemLoader(str(TEMPLATES_DIR))
        env = jinja2.Environment( loader=loader, autoescape=False, trim_blocks=True, lstrip_blocks=True)
        return env

    def _resolve_template_path(self, template: str) -> str:
        if template in ALIASES:
            template = ALIASES[template]
        if not template.endswith(('.j2', '.md')):
             template += '.j2'
        return template

    def render_prompt_for_feature_current_task(
        self, 
        instance_id: str, 
        workflow_state: WorkflowState,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        context_data = self.context_adapter.get_context_for_feature(instance_id, workflow_state)
        
        template_path = self._resolve_template_path(workflow_state.current_phase)
        try:
            template = self.env.get_template(template_path)
        except jinja2.TemplateNotFound:
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        full_context = {**context_data}
        if additional_context:
            full_context.update(additional_context)
        
        return template.render(**full_context).strip()
    
    def preview_prompt_for_phase(
        self, 
        instance_id: str, 
        phase_name: str, 
        task_description: str,
    ) -> str:
        mock_state = WorkflowState(
            instance_id=instance_id,
            feature_id="preview_feature",
            workflow_name="preview-workflow",
            current_phase=phase_name,
            variables={"user_request": task_description},
            status="created"
        )
        return self.render_prompt_for_feature_current_task(instance_id, mock_state)
