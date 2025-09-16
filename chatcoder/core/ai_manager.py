# chatcoder/core/ai_manager.py
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional
from .models import ChangeSet
import jinja2

try:
    from chatflow.core.models import WorkflowState
    CHATFLOW_AVAILABLE = True
except ImportError:
    CHATFLOW_AVAILABLE = False
    raise RuntimeError("chatflow library is required.")

from .context_manager import ContextManager
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
        self.context_adapter = ContextManager()
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

    def parse_ai_response(self, ai_response: str) -> Optional[ChangeSet]:
        """
        [简化示例] 尝试从 AI 响应中解析出 ChangeSet。
        这需要与你的 AI 提示词模板输出格式严格匹配。
        示例格式假设:
        ## Changes
        ### File: path/to/file1.py
        ```python
        <file1_content>
        ```
        Description: <desc1>

        ### File: path/to/file2.py
        ```python
        <file2_content>
        ```
        Description: <desc2>
        """
        changes = []
        # 查找 "## Changes" 部分
        changes_section_match = re.search(r"## Changes\s*(.*)", ai_response, re.DOTALL | re.IGNORECASE)
        if not changes_section_match:
            # warning("No '## Changes' section found in AI response.")
            # 尝试解析整个响应，或者返回 None
            # 这里简单返回 None
            return None 
            
        changes_text = changes_section_match.group(1)

        # 使用正则表达式查找各个文件块
        # 匹配 ### File: ... ```...``` Description: ...
        file_pattern = re.compile(
            r"###\s*File:\s*(?P<file_path>\S+)\s*\n\s*```.*?\n(?P<content>.*?)\n\s*```\s*\n(?:Description:\s*(?P<description>.*?)\n)?",
            re.DOTALL | re.IGNORECASE
        )

        for match in file_pattern.finditer(changes_text):
            file_path = match.group("file_path").strip()
            content = match.group("content")
            description = (match.group("description") or "").strip()

            if file_path and content is not None: # content 可能是空字符串
                 # 简单判断操作类型：如果文件已存在则 modify，否则 create
                 # 注意：这只是一个简化的逻辑，实际可能需要更复杂的判断或由 AI 明确指定
                 import os
                 op = "modify" if os.path.exists(file_path) else "create"
                 
                 change: Change = {
                     "file_path": file_path,
                     "operation": op, # 或者从 AI 响应中解析
                     "new_content": content,
                     "description": description
                 }
                 changes.append(change)
            # else: 可能是格式不匹配，跳过或记录警告

        if changes:
            return {
                "changes": changes,
                "source_task_id": None # 或从上下文获取
            }
        else:
            # warning("Parsed '## Changes' section but found no valid file changes.")
            return None

