# chatcontext/core/providers.py
"""
ChatContext 核心实现 - 具体上下文提供者
提供 ProjectInfoProvider 和 CoreFilesProvider 的具体实现。
"""

import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from .provider import IContextProvider
from .models import ContextRequest, ProvidedContext, ContextType

# --- 导入或定义必要的辅助函数 ---
# 假设这些辅助函数存在于 chatcontext 内部或需要重新实现
# 为了独立性，我们在这里重新定义简化版本
# 或者，如果 chatcontext 有自己的 utils 模块，则导入它们

def _read_file_safely(file_path: Path, max_size_mb: int = 1) -> Optional[str]:
    """安全地读取文件内容，防止读取过大的文件。"""
    try:
        if not file_path.exists() or not file_path.is_file():
            return None
        if file_path.stat().st_size > max_size_mb * 1024 * 1024:
            print(f"⚠️  File {file_path} is larger than {max_size_mb}MB, skipping.")
            return None
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        print(f"⚠️  Error reading file {file_path}: {e}")
        return None

def _detect_project_type(project_root: Path = Path(".")) -> str:
    """简化版项目类型探测。"""
    rules = {
        "python-django": [project_root / "manage.py"],
        "python-fastapi": [project_root / "main.py"],
        "python": [project_root / "requirements.txt", project_root / "setup.py", project_root / "pyproject.toml"],
        "cpp-bazel": [project_root / "WORKSPACE"],
        "cpp": [project_root / "CMakeLists.txt"],
    }
    
    for project_type, indicators in rules.items():
        if any(indicator.exists() for indicator in indicators):
            return project_type
            
    # Fallback check for any .py or .cpp files
    if any(project_root.glob("**/*.py")):
        return "python"
    if any(project_root.glob("**/*.cpp")) or any(project_root.glob("**/*.cc")):
        return "cpp"
        
    return "unknown"

def _load_yaml_safely(yaml_path: Path) -> Dict[str, Any]:
    """安全地加载 YAML 文件。"""
    import yaml
    try:
        if yaml_path.exists():
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data if isinstance(data, dict) else {}
    except (yaml.YAMLError, IOError) as e:
        print(f"⚠️  Error loading YAML {yaml_path}: {e}")
    return {}

# --- 默认配置 ---
DEFAULT_CONTEXT = {
    "project_language": "unknown",
    "test_runner": "unknown",
    "format_tool": "unknown",
    "project_description": "未提供项目描述"
}

PHASE_SPECIFIC_PATTERNS = {
    "analyze": ["**/models.py", "**/schemas.py", "**/interfaces.py", "**/types.py", "**/config.py", "**/settings.py"],
    "design": ["**/interfaces.py", "**/abstract*.py", "**/base*.py", "**/models.py", "**/schemas.py", "**/api/*.py"],
    "implement": ["**/utils.py", "**/helpers.py", "**/common/*.py", "**/lib/*.py", "**/services/*.py", "**/core/*.py"],
    "test": ["**/tests/**/*", "**/*test*.py", "**/test_*.py"],
    "summary": ["**/docs/**/*", "**/README.md", "**/CHANGELOG.md"],
    # "default": [...] # 可以定义，但下面的逻辑会回退到 CORE_PATTERNS
}

CORE_PATTERNS = {
    "python": ["**/*.py"],
    "python-django": ["**/models.py", "**/views.py", "**/apps.py"],
    "python-fastapi": ["**/main.py", "**/routers/*.py", "**/models/*.py"],
    "cpp": ["**/*.cpp", "**/*.h", "**/*.hpp", "**/*.cc"],
    "cpp-bazel": ["BUILD", "WORKSPACE", "**/*.cpp"],
    "unknown": []
}

CONTEXT_DIR = Path(".chatcoder")
CONTEXT_FILE = CONTEXT_DIR / "context.yaml"
CONFIG_FILE = CONTEXT_DIR / "config.yaml"


class ProjectInfoProvider(IContextProvider):
    """
    提供项目基本信息的上下文提供者。
    包括从 context.yaml 加载的用户定义信息和探测到的项目类型。
    """

    @property
    def name(self) -> str:
        """获取提供者的唯一名称。"""
        return "project_info"

    def provide(self, request: ContextRequest) -> List[ProvidedContext]:
        """
        根据请求生成项目基本信息上下文。
        """
        context_data: Dict[str, Any] = DEFAULT_CONTEXT.copy()
        
        # 1. 从 .chatcoder/context.yaml 加载用户定义的上下文
        user_context = _load_yaml_safely(CONTEXT_FILE)
        context_data.update({k: v for k, v in user_context.items() if v}) # 过滤空值

        # 2. 探测项目类型
        detected_type = _detect_project_type()
        context_data["detected_type"] = detected_type

        # 3. (可选) 从 .chatcoder/config.yaml 加载额外配置
        config_data = _load_yaml_safely(CONFIG_FILE)
        if config_data:
            # 例如，config.yaml 中可能有 project_name
            context_data["project_name"] = config_data.get("project_name", context_data.get("project_name", "Unknown Project"))

        # 4. 确定项目语言 (基于类型或文件)
        project_language = "unknown"
        if "python" in detected_type:
            project_language = "python"
        elif "cpp" in detected_type:
            project_language = "cpp"
        context_data["project_language"] = project_language


        final_project_type_for_framework = context_data.get("project_type")
        if not final_project_type_for_framework or final_project_type_for_framework == "unknown":
            final_project_type_for_framework = detected_type

        framework = "unknown"
        if "django" in final_project_type_for_framework.lower():
            framework = "Django"
        elif "fastapi" in final_project_type_for_framework.lower():
            framework = "FastAPI"

        context_data["framework"] = framework

        provided_context = ProvidedContext(
            content=context_data,
            context_type=ContextType.GUIDING, # 项目信息通常是指导性的
            provider_name=self.name,
            metadata={"source": "context_file_and_detection"}
        )
        
        return [provided_context]


class CoreFilesProvider(IContextProvider):
    """
    提供核心文件摘要的上下文提供者。
    根据请求的 phase 或配置文件扫描并摘要核心文件。
    """

    @property
    def name(self) -> str:
        """获取提供者的唯一名称。"""
        return "core_files"

    def provide(self, request: ContextRequest) -> List[ProvidedContext]:
        """
        根据请求的 phase 和项目类型扫描并摘要核心文件。
        """
        core_files_data: Dict[str, Any] = {}
        
        # 1. 确定项目类型 (可以复用探测逻辑或从 ProjectInfoProvider 获取的结果)
        #    为了简化，我们在这里重新探测
        project_type = _detect_project_type()
        
        # 2. 确定要扫描的文件模式
        core_patterns = None
        phase = request.phase_name
        
        # 优先从 config.yaml 加载 (未来可以通过 request 获取更复杂的配置)
        config_data = _load_yaml_safely(CONFIG_FILE)
        if config_data and "core_patterns" in config_data:
            core_patterns = config_data["core_patterns"]
            # print(f"[DEBUG] CoreFilesProvider: Using core_patterns from config.yaml")

        # 如果 config 中没有定义，则根据 phase 和 project_type 动态选择
        if not core_patterns:
            # print(f"[DEBUG] CoreFilesProvider: No core_patterns in config, using defaults for phase '{phase}' and type '{project_type}'")
            if phase and phase in PHASE_SPECIFIC_PATTERNS:
                # 1. 首选：使用与当前 phase 相关的预定义模式
                core_patterns = PHASE_SPECIFIC_PATTERNS[phase]
                # print(f"[DEBUG] CoreFilesProvider: Using PHASE_SPECIFIC_PATTERNS for '{phase}'")
            else:
                # 2. 回退：使用基于项目类型的通用模式
                core_patterns = CORE_PATTERNS.get(project_type, ["**/*.py"])
                # print(f"[DEBUG] CoreFilesProvider: Using CORE_PATTERNS for '{project_type}' or default")

        # 3. 扫描文件并生成摘要
        root_path = Path(".")
        for pattern in core_patterns:
            try:
                # print(f"[DEBUG] CoreFilesProvider: Searching for pattern: {pattern}")
                for file_path in root_path.glob(pattern):
                    # print(f"[DEBUG] CoreFilesProvider: Found file: {file_path}")
                    if not file_path.is_file():
                        continue
                    
                    # 安全读取文件内容
                    content = _read_file_safely(file_path)
                    if not content:
                        continue
                    
                    # 计算哈希
                    file_hash = hashlib.md5(content.encode()).hexdigest()[:8]
                    
                    # 提取关键片段 (简化版)
                    lines = content.strip().splitlines()
                    snippet = "\n".join(lines[:10]) # 取前10行
                    if len(lines) > 10:
                        snippet += "\n..."

                    core_files_data[str(file_path)] = {
                        "hash": file_hash,
                        "snippet": snippet
                    }
            except Exception as e:
                # 捕获单个 pattern 的错误，避免中断整个过程
                print(f"⚠️  CoreFilesProvider: Error processing pattern '{pattern}': {e}")

        # 4. 构造并返回 ProvidedContext
        provided_context = ProvidedContext(
            content={"core_files": core_files_data},
            context_type=ContextType.INFORMATIONAL, # 核心文件是信息性的
            provider_name=self.name,
            metadata={
                "source": "file_scanning",
                "patterns_used": core_patterns,
                "files_scanned": len(core_files_data)
            }
        )
        
        return [provided_context]

# --- (可选) 其他 Provider 的占位符 ---
# class TaskAwareFilesProvider(IContextProvider):
#     """
#     (高级) 分析前置任务输出，提取提及的文件/函数，然后读取和摘要。
#     """
#     @property
#     def name(self) -> str:
#         return "task_aware_files"

#     def provide(self, request: ContextRequest) -> List[ProvidedContext]:
#         # 实现逻辑会比较复杂，需要：
#         # 1. 访问 request.previous_outputs 或通过 feature_id 查询历史任务。
#         # 2. 分析 AI 输出内容，提取文件名、函数名等。
#         # 3. 读取这些特定文件/函数的内容。
#         # 4. 生成摘要。
#         # 这可能需要一个更强大的代码分析库或 LLM 来辅助提取。
#         # ...
#         return []
