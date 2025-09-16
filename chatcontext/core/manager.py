# chatcontext/core/manager.py
"""ChatContext 核心管理器"""

import time
from typing import List, Dict, Any
from .models import ContextRequest, ProvidedContext, FinalContext
from .provider import IContextProvider

class ContextManager:
    """上下文管理器，负责协调 Providers 并生成最终上下文"""

    def __init__(self):
        self._providers: List[IContextProvider] = []
        # 可在此初始化缓存、安全策略等

    def register_provider(self, provider: IContextProvider):
        """注册一个 ContextProvider"""
        # 可添加去重逻辑
        self._providers.append(provider)

    def get_context(self, request: ContextRequest) -> FinalContext:
        """
        核心方法：根据 ContextRequest 生成 FinalContext。
        """
        start_time = time.time()
        all_provided_contexts: List[ProvidedContext] = []
        diagnostics: List[Dict[str, Any]] = []

        try:
            # 1. Provider 筛选与排序 (v1.1)
            # 筛选: can_provide
            filtered_providers = [p for p in self._providers if p.can_provide(request)]
            # 排序: get_priority (降序)
            sorted_providers = sorted(filtered_providers, key=lambda p: p.get_priority(request), reverse=True)

            # 2. 调用 Providers
            for provider in sorted_providers:
                provider_start = time.time()
                try:
                    provided_contexts = provider.provide(request)
                    all_provided_contexts.extend(provided_contexts)
                    diagnostics.append({
                        "provider": provider.name,
                        "status": "success",
                        "time_taken": time.time() - provider_start,
                        "contexts_provided": len(provided_contexts)
                    })
                except Exception as e:
                    # 3. 错误隔离 (v1.0)
                    diagnostics.append({
                        "provider": provider.name,
                        "status": "error",
                        "time_taken": time.time() - provider_start,
                        "error": str(e)
                    })
                    # 记录日志，但不中断主流程
                    print(f"Warning: Provider {provider.name} failed: {e}")

            # 4. 合并上下文 (v1.0/v1.1)
            merged_data, total_size = self._merge_contexts(all_provided_contexts, request)

            # 5. 生成增强建议 (v1.1 - 示例)
            suggestions = self._suggest_context_enhancement(request, sorted_providers)

            generation_time = time.time() - start_time

            return FinalContext(
                merged_data=merged_data,
                provider_diagnostics=diagnostics,
                generation_time=generation_time,
                total_size=total_size,
                suggestions=suggestions
            )

        except Exception as e:
            # 处理主流程中的意外错误
            error_time = time.time() - start_time
            return FinalContext(
                merged_data={}, # 返回空上下文
                provider_diagnostics=[{"manager": "error", "error": str(e), "time_taken": error_time}],
                generation_time=error_time,
                total_size=0,
                suggestions=[f"Context generation failed: {e}"]
            )

    def _merge_contexts(self, provided_contexts: List[ProvidedContext], request: ContextRequest) -> tuple[Dict[str, Any], int]:
        """
        (内部) 合并所有 Provider 提供的上下文片段。
        返回 (merged_dict, total_estimated_size)
        """
        merged: Dict[str, Any] = {}
        total_size = 0

        # 简单合并示例：按 key 覆盖
        # 实际实现可更复杂：类型感知、相关性加权、大小控制等 (v1.1)
        for ctx in provided_contexts:
            merged.update(ctx.content)
            if ctx.size_estimate is not None:
                total_size += ctx.size_estimate
            # 可在此应用安全脱敏策略 (v1.1)

        return merged, total_size

    def _suggest_context_enhancement(self, request: ContextRequest, sorted_providers: List[IContextProvider]) -> List[str]:
        """
        (内部) 根据请求和可用 Providers 生成增强建议 (v1.1)。
        """
        suggestions = []
        # 示例逻辑：检查是否有 Provider 本可以参与但被 can_provide 拒绝
        # for provider in self._providers:
        #     if provider not in sorted_providers and provider.can_provide(request):
        #         suggestions.append(f"Consider enabling provider '{provider.name}' for more context.")
        # ... 更多建议逻辑 ...
        return suggestions

    # --- v1.1 新增方法 ---
    def suggest_context_enhancement(self, request: ContextRequest) -> List[str]:
        """
        公开方法：为给定请求提供上下文增强建议。
        """
        # 可以复用内部逻辑或提供更详细的建议
        # 例如，分析 request.task_description 中的关键词
        return self._suggest_context_enhancement(request, self._providers) # 简化示例
