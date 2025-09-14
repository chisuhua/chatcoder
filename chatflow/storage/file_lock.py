# chatflow/storage/file_lock.py
"""
轻量级文件锁实现，用于跨进程同步对共享资源（如工作流状态文件）的访问。

特性：
- 基于 fcntl (Unix) 和 msvcrt (Windows) 的原子操作
- 支持上下文管理器语法（with 语句）
- 自动创建锁文件目录
- 异常安全：确保锁在退出时被释放
"""

import os
import sys
from pathlib import Path

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


class FileLock:
    """
    跨平台文件锁。
    
    使用 fcntl.flock (Linux/macOS) 或 msvcrt.locking (Windows) 实现。
    通过文件系统提供进程间互斥。
    """

    def __init__(self, lock_file_path: str):
        """
        初始化文件锁。
        
        :param lock_file_path: 锁文件的路径
        """
        self.lock_file_path = Path(lock_file_path)
        self._lock_file = None  # 用于保存打开的文件对象
        
    def __enter__(self):
        """
        进入上下文，获取独占锁。
        
        此方法会阻塞直到成功获得锁。
        """
        # 确保锁文件的父目录存在
        self.lock_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # 打开或创建锁文件
            # 使用 'w' 模式，如果文件不存在则创建
            self._lock_file = open(self.lock_file_path, "w")
            
            # 根据操作系统选择加锁方式
            if sys.platform == "win32":
                # Windows 平台使用 msvcrt.locking
                # _LK_LOCK 表示阻塞式独占锁
                msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_LOCK, 1)
            else:
                # Unix/Linux/macOS 平台使用 fcntl.flock
                # LOCK_EX 表示独占锁，LOCK_NB 不使用非阻塞模式（即阻塞等待）
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX)
                
        except (IOError, OSError) as e:
            # 如果加锁失败，关闭文件并抛出异常
            if self._lock_file:
                self._lock_file.close()
                self._lock_file = None
            raise RuntimeError(f"无法获取文件锁 {self.lock_file_path}: {e}")
            
        return self  # 返回自身，但通常不需要接收
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        退出上下文，释放锁。
        
        此方法确保无论是否发生异常，锁都会被正确释放。
        """
        if self._lock_file:
            try:
                if sys.platform == "win32":
                    # Windows: 解锁
                    msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    # Unix: 释放 flock
                    fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
            except (IOError, OSError) as e:
                # 记录解锁错误，但不中断主流程
                print(f"警告: 释放文件锁时出错 {self.lock_file_path}: {e}")
            finally:
                # 关闭文件描述符
                self._lock_file.close()
                self._lock_file = None
