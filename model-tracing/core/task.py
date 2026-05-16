"""
core/task.py

Task 的基础数据结构，三种任务模式都基于这里的定义。
"""

from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum
import time


class TaskMode(Enum):
    PARALLEL = "parallel"        # 多模型并行，结果对比（评测用）
    PIPELINE = "pipeline"        # 按步骤，不同步骤用不同模型
    SMART_ROUTE = "smart_route"  # 自动选最合适的模型


@dataclass
class StepResult:
    """流水线中单个步骤的结果"""
    step_name: str
    model: str
    input: str
    output: str
    tokens: int
    latency_ms: float
    success: bool
    error: Optional[str] = None


@dataclass
class TaskResult:
    """任务最终结果，包含完整执行轨迹"""
    task_id: str
    task_mode: TaskMode
    final_output: Any                      # 最终输出（parallel 时是列表，其他是字符串）
    steps: list[StepResult] = field(default_factory=list)
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def summary(self) -> dict:
        """打印友好的摘要"""
        return {
            "task_id": self.task_id,
            "mode": self.task_mode.value,
            "success": self.success,
            "total_tokens": self.total_tokens,
            "total_latency_ms": self.total_latency_ms,
            "steps": [
                {
                    "step": s.step_name,
                    "model": s.model,
                    "tokens": s.tokens,
                    "latency_ms": s.latency_ms,
                    "success": s.success,
                }
                for s in self.steps
            ],
        }
