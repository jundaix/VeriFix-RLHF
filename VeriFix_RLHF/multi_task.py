from __future__ import annotations

import random
import threading
import time
from typing import Any, Callable, Dict, List

from colorama import Fore, Style


class Task:
    def __init__(self, task_name: str, task_id: int, dependencies: List[Task], extra_info: Any = None):
        self.task_name = task_name
        self.task_id = task_id
        self.extra_info = extra_info
        self.dependencies = dependencies
        self.status = 0  # 任务状态：0未开始，1正在进行，2已经完成，3出错了


class TaskManager:
    def __init__(self):
        """
        初始化一个 MultiTaskDispatch 对象。

        设置必要的属性以管理任务调度与同步。具体属性如下：
        
        属性：
        - task_dict (Dict[int, Task]): 存储任务 ID 与 Task 对象的映射关系。
        - name_id_dict (Dict[str, int]): 存储任务名称与 ID 的映射。
        - task_lock (threading.Lock): 用于确保访问 task_dict 时的线程安全。
        - now_id (int): 当前正在处理的任务 ID。
        - query_id (int): 当前查询的 ID。
        """
        self.task_dict: Dict[int, Task] = {}
        self.name_id_dict: Dict[str, int] = {}
        self.task_lock = threading.Lock()
        self.now_id = 0
        self.query_id = 0

    @property
    def all_success(self) -> bool:
        return len(self.task_dict) == 0

    def add_task(self, task_name, dependency_task_id: List[int], extra=None) -> int:
        """
        向任务字典中添加一个新任务。
        
        Args:
            dependency_task_id (List[int]): 新任务依赖的任务ID列表。
            extra (Any, optional): 与任务相关联的额外信息。默认为None。
        
        Returns:
            int: 新添加任务的ID。
        """
        with self.task_lock:
            #通过依赖任务的ID获取依赖的任务对象
            depend_tasks = [self.task_dict[task_id] for task_id in dependency_task_id]
            #为当前的任务ID创建对象并添加到任务字典中
            self.task_dict[self.now_id] = Task(
                task_name=task_name ,task_id=self.now_id, dependencies=depend_tasks, extra_info=extra
            )
            self.name_id_dict[task_name] = self.now_id
            self.now_id += 1
            return self.now_id - 1
    def get_task_id(self,task_name) -> int:
        return self.name_id_dict[task_name]

    def get_next_task(self, process_id: int):
        """
        获取给定进程ID的下一个任务。
        
        Args:
            process_id (int): 进程ID。
        
        Returns:
            tuple: 包含下一个任务对象和其ID的元组。
                 如果没有可用任务，返回(None, -1)。
        
        """
        with self.task_lock:
            self.query_id += 1
            for task_id in self.task_dict.keys():
                ready = (
                    len(self.task_dict[task_id].dependencies) == 0
                ) and self.task_dict[task_id].status == 0
                if ready:
                    self.task_dict[task_id].status = 1
                    print(
                        f"{Fore.RED}[process {process_id}]{Style.RESET_ALL}: get task({task_id}), remain({len(self.task_dict)})"
                    )
                    return self.task_dict[task_id], task_id
            return None, -1

    def mark_completed(self, task_id: int):
        """
        将指定任务标记为已完成并从任务字典中移除。
        
        Args:
            task_id (int): 要标记为已完成的任务的ID。
        
        """
        with self.task_lock:
            target_task = self.task_dict[task_id]
            for task in self.task_dict.values():
                if target_task in task.dependencies:
                    task.dependencies.remove(target_task)
            self.task_dict.pop(task_id)  # 从任务字典中移除


def worker(task_manager, process_id: int, handler: Callable):
    """
    Worker function that performs tasks assigned by the task manager.

    Args:
        task_manager: The task manager object that assigns tasks to workers.
        process_id (int): The ID of the current worker process.
        handler (Callable): The function that handles the tasks.

    Returns:
        None
    """
    while True:
        #所有任务都已经完成
        if task_manager.all_success:
            return
        task, task_id = task_manager.get_next_task(process_id)
        #此时没有需要进行添加的任务，都在进行中
        if task is None:
            time.sleep(0.5)
            continue
        # print(f"will perform task: {task_id}")
        handler(task.extra_info)
        task_manager.mark_completed(task.task_id)
        # print(f"task complete: {task_id}")

def add_task(task_name:str, dependency_task_id: List[int], extra=None) -> int:
    """
    向任务管理器添加一个新的任务。
    
    Args:
        dependency_task_id (List[int]): 新任务依赖的任务ID列表。
        extra (Any, optional): 与任务相关联的额外信息。默认为None。
    
    Returns:
        int: 新添加任务的ID。
    """
    #获取名称为task_manager的对象
    task_manager = globals().get('task_manager')
    
    return task_manager.add_task(task_name, dependency_task_id, extra)
    

task_manager = TaskManager()
