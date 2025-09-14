# chatflow/utils/id_generator.py
import uuid
import time

def generate_id() -> str:
    """生成短唯一ID"""
    return uuid.uuid4().hex[:12]

def generate_timestamp() -> float:
    """获取时间戳"""
    return time.time()

