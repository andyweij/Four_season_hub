from pydantic import BaseModel
from typing import List, Optional
import psutil


class ProcessInfo(BaseModel):
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_percent: float


def get_system_processes(filter_name: Optional[str] = None) -> List[dict]:
    """同步阻塞函式：負責實際撈取系統 Process"""
    processes = []
    # 只抓取必要的 attributes 提升效能
    attrs = ['pid', 'name', 'status', 'cpu_percent', 'memory_percent']

    for proc in psutil.process_iter(attrs):
        try:
            info = proc.info
            if filter_name and filter_name.lower() not in info['name'].lower():
                continue
            processes.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return processes
