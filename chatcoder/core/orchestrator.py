# chatcoder/core/orchestrator.py
import re
import uuid
from datetime import datetime

class TaskOrchestrator:
    def generate_feature_id(self, description: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", description.lower())
        words = cleaned.split()
        short_words = "_".join(words[:4])
        prefix = "feat"
        return f"{prefix}_{short_words}" if short_words else f"{prefix}_default"
    
    def generate_automation_level(self) -> int:
        return 60
