# chatcoder/core/orchestrator.py
"""
ChatCoder 核心服务 - 任务编排器 (TaskOrchestrator) [简化版]
负责任务 ID 和特性 ID 的生成。
[注意] 任务状态的持久化和管理已完全委托给 chatflow。
"""

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

class TaskOrchestrator:
    """
    任务编排器（简化版）。
    职责：
    1. 生成唯一的 feature_id 和 task_id。
    """

    def __init__(self):
        """
        初始化任务编排器。
        """
        pass

    def generate_feature_id(self, description: str) -> str:
        """
        根据描述生成简洁的 feature_id。
        """
        cleaned = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff\s]", " ", description.lower())
        words = cleaned.split()
        short_words = "_".join(words[:4])
        prefix = "feat"
        if not short_words:
            return f"{prefix}_"
        return f"{prefix}_{short_words}"

    def generate_task_id(self) -> str:
        """
        生成任务唯一 ID。
        格式: tsk_{unix_timestamp}_{random}
        示例: tsk_1725293840_5a3b8c
        """
        timestamp = int(datetime.now().timestamp())
        random_suffix = uuid.uuid4().hex[:6]
        return f"tsk_{timestamp}_{random_suffix}"

