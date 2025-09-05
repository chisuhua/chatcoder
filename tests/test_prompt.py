# tests/test_prompt.py
import pytest
from unittest.mock import patch, MagicMock
# 导入新的服务管理器
from chatcoder.core.manager import AIInteractionManager
# 导入可能需要的模型
# from chatcoder.core.models import ... 

def test_ai_manager_resolve_template_path_alias(ai_manager):
    """测试 AIInteractionManager 模板路径解析 - 别名"""
    resolved = ai_manager._resolve_template_path("analyze") # _resolve_template_path 是私有方法，测试时可以直接调用
    assert resolved == "workflows/step1-analyze.md.j2"

def test_ai_manager_resolve_template_path_direct(ai_manager):
    """测试 AIInteractionManager 模板路径解析 - 直接路径"""
    resolved = ai_manager._resolve_template_path("workflows/step2-design.md.j2")
    assert resolved == "workflows/step2-design.md.j2"

def test_ai_manager_list_available_templates(ai_manager):
    """测试 AIInteractionManager 列出可用模板"""
    templates = ai_manager.list_available_templates()
    assert isinstance(templates, list)
    # 检查是否包含已知的别名和路径
    found_analyze_alias = any(t[0] == 'analyze' and t[1] == 'workflows/step1-analyze.md.j2' for t in templates)
    found_direct_template = any(t[0] == '(direct)' and 'feature.md.j2' in t[1] for t in templates)
    assert found_analyze_alias, "Alias 'analyze' not found in listed templates"
    assert found_direct_template, "Direct template path not found in listed templates"

# 注意：render_prompt 依赖于 Jinja2 模板文件和上下文，测试起来比较复杂。
# 使用 unittest.mock 来模拟 generate_context_snapshot 或文件系统。
def test_ai_manager_render_prompt_basic(temp_project_dir, ai_manager):
    """测试 AIInteractionManager 渲染提示词 - 基础流程 (使用 mock)"""
    description = "Test feature description"
    
    # Mock generate_context_snapshot (from context module, as manager uses it)
    # 注意：AIInteractionManager 直接调用 chatcoder.core.context.generate_context_snapshot
    # 我们需要 mock 这个模块级别的函数
    mock_context = {
        "project_name": "Mocked Project",
        "project_language": "python",
        "context_snapshot": "## Mocked Context Snapshot\n- Key: Value"
    }
    
    with patch('chatcoder.core.manager.generate_context_snapshot', return_value=mock_context): # Mock the function where it's used
        # Mock Jinja2 environment and template to avoid file system dependency
        with patch.object(ai_manager, '_create_jinja_env') as mock_env_factory: # Mock the instance method
            mock_env = MagicMock()
            mock_template = MagicMock()
            mock_template.render.return_value = f"Rendered prompt for: {description}"
            mock_env.get_template.return_value = mock_template
            mock_env_factory.return_value = mock_env
            
            # Call the function under test
            result = ai_manager.render_prompt("analyze", description)
            
            # Assert the result
            assert result == f"Rendered prompt for: {description}"
            
            # Assert that mocks were called correctly
            mock_env_factory.assert_called_once()
            # Check if the correct relative path was used to get the template
            # This requires knowing the internal logic of _resolve_template_path
            expected_rel_path = "workflows/step1-analyze.md.j2" 
            mock_env.get_template.assert_called_once_with(expected_rel_path)
            mock_template.render.assert_called_once()
            
            # Check if the context passed to render contains expected keys
            call_kwargs = mock_template.render.call_args[1] # Get kwargs passed to render
            assert "description" in call_kwargs
            assert call_kwargs["description"] == description
            assert "project_name" in call_kwargs # From mocked context
            assert call_kwargs["project_name"] == "Mocked Project"
