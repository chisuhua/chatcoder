# chatcoder/core/context_manager.py
from typing import Dict, Any
try:
    from chatcontext.core.manager import ContextManager as ChatContextManager
    from chatcontext.core.models import ContextRequest
    CHATCONTEXT_AVAILABLE = True
except ImportError:
    CHATCONTEXT_AVAILABLE = False
    raise RuntimeError("chatcontext library is required.")

class ContextManager:
    def __init__(self):
        if not CHATCONTEXT_AVAILABLE:
            raise RuntimeError("chatcontext is required but not available.")
        self.context_manager = ChatContextManager()
    
    def get_context_for_feature(self, instance_id: str, workflow_state: 'WorkflowState') -> Dict[str, Any]:
        request = ContextRequest(
            workflow_instance_id=instance_id,
            phase_name=workflow_state.current_phase,
            task_description=workflow_state.variables.get("user_request", ""),
        )
        final_context = self.context_manager.get_context(request)
        return final_context.merged_data
