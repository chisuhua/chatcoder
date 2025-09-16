# chatcoder/core/coder.py
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
# from dataclasses import asdict # 如果需要打印状态等，可以导入

from .thinker import Thinker # 导入 Thinker 以可能需要其状态或上下文
from .ai_manager import AIInteractionManager # 需要解析 AI 响应
from .models import Change, ChangeSet # 需要 ChangeSet 模型
from ..utils.console import console, success, error, warning, info, confirm

class Coder:
    """
    Coder 类，负责代码生成、应用、版本控制等与代码库直接交互的操作。
    """
    def __init__(self, thinker: Thinker): # <--- 依赖 Thinker 实例
        """
        初始化 Coder。

        Args:
            thinker (Thinker): 已初始化的 Thinker 实例，用于获取上下文等。
        """
        self.thinker = thinker # 保存对 Thinker 的引用
        # 如果 Coder 需要自己的 AI 管理器实例（例如专门用于解析）
        # self.ai_manager = AIInteractionManager()
        # 或者复用 Thinker 的
        # self.ai_manager = thinker.ai_manager

    def apply_task(self, instance_id: str, ai_response: str) -> bool: # <--- apply_task 实现
        """
        将 AI 响应应用到项目文件系统。

        Args:
            instance_id (str): 工作流实例 ID。
            ai_response (str): AI 生成的原始文本响应。

        Returns:
            bool: 应用是否成功（至少启动了应用过程）。
        """
        try:
            info(f"Coder attempting to apply AI response to instance '{instance_id}'...")

            # 1. 调用 AIInteractionManager (可能复用 Thinker 的，或创建新的) 解析响应
            # 假设 AIInteractionManager 有这个方法
            change_set: Optional[ChangeSet] = self.thinker.ai_manager.parse_ai_response(ai_response)
            # 或者如果 Coder 有自己的 ai_manager 实例:
            # change_set: Optional[ChangeSet] = self.ai_manager.parse_ai_response(ai_response)

            if not change_set or not change_set.get("changes"):
                warning("AI response parsed but contains no applicable changes or failed to parse.")
                return False # 认为没有可应用的变更或解析失败

            changes: List[Change] = change_set["changes"]
            applied_count = 0
            success_count = 0

            # 2. 遍历并应用变更
            for i, change in enumerate(changes):
                applied_count += 1
                op = change["operation"]
                file_path_str = change["file_path"]
                new_content = change["new_content"]
                description = change.get("description", "No description provided")

                file_path = Path(file_path_str)
                info(f"  [{i+1}/{len(changes)}] Applying '{op}' to '{file_path}' ({description})")

                try:
                    # 3. 根据操作类型处理文件
                    if op in ("create", "modify"):
                        # 确保父目录存在
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        # 写入文件内容
                        file_path.write_text(new_content, encoding='utf-8')
                        success(f"    -> Successfully wrote to '{file_path}'.")
                        success_count += 1

                    # elif op == "delete":
                    #     if file_path.exists():
                    #         file_path.unlink()
                    #         success(f"    -> Successfully deleted '{file_path}'.")
                    #         success_count += 1
                    #     else:
                    #         warning(f"    -> File '{file_path}' not found for deletion.")

                    else:
                        warning(f"    -> Unsupported operation '{op}' for file '{file_path}'. Skipped.")

                except Exception as e:
                    error(f"    -> Failed to apply change to '{file_path}': {e}")

            # 4. 总结应用结果
            if success_count == applied_count and applied_count > 0:
                success(f"✅ All {success_count} changes applied successfully for instance '{instance_id}' by Coder.")
                return True
            elif success_count > 0:
                warning(f"⚠️  Partially applied: {success_count}/{applied_count} changes were successful for instance '{instance_id}' by Coder.")
                return True # 至少部分成功
            else:
                error(f"❌ Failed to apply any of the {applied_count} changes for instance '{instance_id}' by Coder.")
                return False # 全部失败

        except Exception as e:
            error(f"❌ Unexpected error during Coder.apply_task for instance '{instance_id}': {e}")
            return False

    # ==================== 未来扩展：Git 相关方法 ====================
    # def git_commit(self, instance_id: str, message: str) -> bool:
    #     """提交应用的更改到 Git"""
    #     # ... 实现 ...
    #     pass

    # def git_push(self, remote: str = "origin", branch: str = None) -> bool:
    #     """推送更改到远程仓库"""
    #     # ... 实现 ...
    #     pass

    # def git_diff(self, instance_id: str) -> str:
    #     """显示应用更改前后的差异"""
    #     # ... 实现 ...
    #     pass

    # ==================== 其他代码操作方法 ====================
    # def format_code(self, file_path: str) -> bool:
    #     """格式化指定文件"""
    #     # ... 实现 ...
    #     pass

    # def run_linter(self, file_path: str) -> List[str]:
    #     """对指定文件运行 Linter"""
    #     # ... 实现 ...
    #     pass
