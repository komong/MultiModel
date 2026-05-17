"""
core/schema.py

代码生成评测的数据结构定义。
"""

from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class EvalInput:
    """评测输入"""
    instruction: str                    # 任务描述
    language: str                       # python / javascript / sql
    granularity: str = "function"       # function / class / feature
    context: str = ""                   # 可选：已有代码上下文


@dataclass
class ExpectedOutput:
    """期望输出（用于自动评测）"""
    test_cases: list[dict] = field(default_factory=list)       # [{"input": "...", "expected": "..."}]
    must_contain: list[str] = field(default_factory=list)      # 关键实现要素
    reference_solution: str = ""                                # 参考答案（可选）


@dataclass
class EvalItem:
    """单条评测样本"""
    id: str
    input: EvalInput
    expected_output: ExpectedOutput
    metadata: dict = field(default_factory=dict)               # difficulty, tags, source


@dataclass
class EvalScore:
    """单条评测评分"""
    syntax_valid: float = 0.0          # L1: 0.0 或 1.0
    test_pass_rate: float = 0.0        # L2: 0.0 ~ 1.0


@dataclass
class EvalResult:
    """单条评测结果"""
    item_id: str
    item: EvalItem
    generated_code: str
    scores: EvalScore
    model: str = ""
    trace_id: str = ""
    error: Optional[str] = None
