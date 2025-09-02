from pathlib import Path
import json
import time
from typing import Dict, Any, Optional
import uuid

STATE_DIR = Path(".chatcoder") / "state"

def ensure_state_dir():
    STATE_DIR.mkdir(parents=True, exist_ok=True)

def generate_task_id() -> str:
    return f"task_{int(time.time())}_{uuid.uuid4().hex[:8]}"

def save_task_state(task_id: str, template: str, description: str, context: Dict[str, Any]):
    ensure_state_dir()
    state_file = STATE_DIR / f"{task_id}.json"
    state = {
        "task_id": task_id,
        "template": template,
        "description": description,
        "context_snapshot": context,
        "created_at": time.time(),
        "created_at_str": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def load_task_state(task_id: str) -> Optional[Dict[str, Any]]:
    state_file = STATE_DIR / f"{task_id}.json"
    if not state_file.exists():
        return None
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        return None

def list_task_states() -> list:
    if not STATE_DIR.exists():
        return []
    tasks = []
    for f in STATE_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            tasks.append(data)
        except:
            continue
    return sorted(tasks, key=lambda x: x["created_at"], reverse=True)
