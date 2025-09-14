import hashlib
from typing import Union

def calculate_checksum(content: Union[str, bytes]) -> str:
    """计算内容的 SHA256 校验和"""
    if isinstance(content, str):
        content = content.encode('utf-8')
    return hashlib.sha256(content).hexdigest()
