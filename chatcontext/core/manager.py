# chatcontext/core/manager.py
"""
ChatContext 核心服务 - 上下文管理器 (ContextManager)
负责协调和管理所有已注册的 ContextProvider，聚合它们生成的上下文，
并向调用方提供最终的、结构化的上下文字典。
"""

from typing import List, Dict, Any, Optional
from .provider import IContextProvider
from .models import ContextRequest, ProvidedContext, ContextType

class IContextManager:
    """
    抽象基类，用于定义上下文管理器的接口。
    """

    def get_context(self, request: ContextRequest) -> Dict[str, Any]:
        """
        根据请求协调 Providers 生成并合并最终的上下文。

        Args:
            request (ContextRequest): 包含生成上下文所需信息的请求对象。

        Returns:
            Dict[str, Any]: 一个字典，包含所有合并后的上下文信息，
                            可以直接用于提示词模板渲染。
        """
        raise NotImplementedError

     # --- Future Extension ---
     # def get_context_by_pipeline(self, request: ContextRequest, pipeline_config: 'ContextPipelineConfig') -> Dict[str, Any]:
     #     """
     #     (Future) 根据指定的管道配置来获取上下文。
     #     允许更细粒度地控制上下文生成过程。
     #     """
     #     raise NotImplementedError
     # --- Future Extension End ---

class ContextManager(IContextManager):
    """
    上下文管理器的具体实现。
    管理一组 ContextProvider，并根据 ContextRequest 协调它们生成上下文。
    """

    def __init__(self):
        """
        初始化上下文管理器。
        """
        self._providers: List[IContextProvider] = []

    def register_provider(self, provider: IContextProvider) -> None:
        """
        注册一个上下文提供者。

        Args:
            provider (IContextProvider): 要注册的上下文提供者实例。
        """
        if not isinstance(provider, IContextProvider):
            raise TypeError("Provider must be an instance of IContextProvider")
        # print(f"[DEBUG] ContextManager: Registering provider '{provider.name}'")
        self._providers.append(provider)

    def unregister_provider(self, provider_name: str) -> bool:
        """
        注销一个上下文提供者。

        Args:
            provider_name (str): 要注销的提供者名称。

        Returns:
            bool: 如果成功注销则返回 True，否则返回 False。
        """
        for i, provider in enumerate(self._providers):
            if provider.name == provider_name:
                # print(f"[DEBUG] ContextManager: Unregistering provider '{provider_name}'")
                del self._providers[i]
                return True
        # print(f"[DEBUG] ContextManager: Provider '{provider_name}' not found for unregistration.")
        return False

    def list_providers(self) -> List[str]:
        """
        获取所有已注册提供者的名称列表。

        Returns:
            List[str]: 提供者名称列表。
        """
        return [p.name for p in self._providers]

    def get_context(self, request: ContextRequest) -> Dict[str, Any]:
        """
        根据请求协调所有已注册的 Providers 生成并合并最终的上下文。

        Args:
            request (ContextRequest): 包含生成上下文所需信息的请求对象。

        Returns:
            Dict[str, Any]: 一个字典，包含所有合并后的上下文信息。
        """
        all_provided_contexts: List[ProvidedContext] = []

        # print(f"[DEBUG] ContextManager: Starting context generation for feature '{request.feature_id}', phase '{request.phase_name}'")

        # 1. 遍历所有已注册的 Provider
        for provider in self._providers:
            try:
                # print(f"[DEBUG] ContextManager: Calling provider '{provider.name}'")
                # 2. 调用每个 Provider 的 provide 方法
                provided_contexts: List[ProvidedContext] = provider.provide(request)
                
                # 3. 收集 Provider 返回的 ProvidedContext 列表
                if provided_contexts:
                    # print(f"[DEBUG] ContextManager: Provider '{provider.name}' returned {len(provided_contexts)} context(s).")
                    all_provided_contexts.extend(provided_contexts)
                # else:
                #     print(f"[DEBUG] ContextManager: Provider '{provider.name}' returned no contexts.")
                    
            except Exception as e:
                # 捕获单个 Provider 的错误，避免中断整个流程
                print(f"⚠️  ContextManager: Error calling provider '{provider.name}': {e}")
                # 可以选择记录日志或采取其他措施
                continue

        # 4. 合并所有收集到的 ProvidedContext
        final_context: Dict[str, Any] = self._merge_contexts(all_provided_contexts, request)
        
        # print(f"[DEBUG] ContextManager: Final context generation complete. Keys: {list(final_context.keys())}")
        return final_context

    def _merge_contexts(self, provided_contexts: List[ProvidedContext], request: ContextRequest) -> Dict[str, Any]:
        """
        (内部方法) 合并多个 ProvidedContext 对象为一个最终的上下文字典。

        Args:
            provided_contexts (List[ProvidedContext]): 由各个 Provider 生成的 ProvidedContext 列表。
            request (ContextRequest): 原始的上下文请求。

        Returns:
            Dict[str, Any]: 合并后的最终上下文字典。
        """
        merged_context: Dict[str, Any] = {}

        if not provided_contexts:
            # print("[DEBUG] ContextManager._merge_contexts: No contexts to merge.")
            return merged_context

        # --- 简单合并策略 ---
        # 按顺序遍历所有 ProvidedContext
        for pc in provided_contexts:
            context_content: Dict[str, Any] = pc.content
            if not isinstance(context_content, dict):
                print(f"⚠️  ContextManager._merge_contexts: Provided context from '{pc.provider_name}' is not a dict, skipping.")
                continue

            # 将 content 字典的内容合并到最终上下文中
            # 如果有同名键，后面的会覆盖前面的
            # print(f"[DEBUG] ContextManager._merge_contexts: Merging context from '{pc.provider_name}' (keys: {list(context_content.keys())})")
            merged_context.update(context_content)
            
            # 可选：将元数据也加入最终上下文，供调试或高级用法
            # merged_context[f"_meta_{pc.provider_name}"] = pc.meta

        # --- 可扩展的合并策略 ---
        # 未来可以实现更复杂的合并逻辑，例如：
        # 1. 基于 ContextType 的合并：
        #    - GUIDING 类型的信息可能具有高优先级。
        #    - INFORMATIONAL 类型的信息可能需要结构化处理。
        # 2. 基于 Provider 优先级的合并。
        # 3. 基于 key 名称空间的合并 (e.g., `project_info.name`, `core_files.src/main.py.snippet`)。
        # 4. 使用特定的合并函数处理特定 key (例如，合并列表而不是覆盖)。

        # --- 添加请求本身的信息 ---
        # 将请求中的一些关键信息也加入最终上下文，供模板使用
        merged_context["feature_id"] = request.feature_id
        merged_context["phase_name"] = request.phase_name
        merged_context["task_description"] = request.task_description
        # previous_outputs 可能很大，可以选择性地加入或处理
        # merged_context["previous_outputs_summary"] = {k: type(v).__name__ for k, v in request.previous_outputs.items()}
        
        # print(f"[DEBUG] ContextManager._merge_contexts: Merged context keys: {list(merged_context.keys())}")
        return merged_context

    # --- Future Extension ---
    # def get_context_by_pipeline(self, request: ContextRequest, pipeline_config: 'ContextPipelineConfig') -> Dict[str, Any]:
    #     """
    #     (Future) 根据指定的管道配置来获取上下文。
    #     """
    #     raise NotImplementedError("get_context_by_pipeline is not yet implemented.")
    # --- Future Extension End ---

# --- 为了兼容旧代码或提供便捷访问，可以保留模块级函数 (可选) ---
# def get_context(request: ContextRequest) -> Dict[str, Any]:
#     """
#     (模块级函数) 便捷方法：使用默认配置的 ContextManager 获取上下文。
#     """
#     # 注意：这种方式需要确保在调用时，所需的 Providers (如 ProjectInfoProvider, CoreFilesProvider)
#     # 已经被正确地导入和实例化并注册到这个默认的 manager 实例中。
#     # 这通常在库的初始化或应用的启动脚本中完成。
#     # 一个更稳健的方式是在需要时显式创建和配置 ContextManager 实例。
#     
#     # 示例 (需要根据实际 Provider 实现调整):
#     # from .providers import ProjectInfoProvider, CoreFilesProvider
#     # manager = ContextManager()
#     # manager.register_provider(ProjectInfoProvider())
#     # manager.register_provider(CoreFilesProvider())
#     # return manager.get_context(request)
#     raise NotImplementedError("Use ContextManager instance method get_context instead.")
