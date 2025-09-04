# tests/test_state.py
from chatcoder.core.state import generate_feature_id, save_task_state
import json
import pytest


def test_generate_feature_id():
    assert generate_feature_id("Add user auth") == "feat_add_user_auth"


def test_save_task_state(tasks_dir):
    save_task_state("task_123", "analyze", "desc", {}, phase="analyze")
    file = tasks_dir / "task_123.json"
    assert file.exists()
    data = json.loads(file.read_text())
    assert data["phase"] == "analyze"
