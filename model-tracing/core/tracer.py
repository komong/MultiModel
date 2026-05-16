"""
core/tracer.py

追踪层的抽象接口。
上层代码只依赖这个接口，不直接依赖任何具体的追踪工具。
后续换追踪后端（或同时接多个），上层代码不用动。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum


class SpanStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class SpanData:
    """单个步骤的追踪数据"""
    name: str                          # 步骤名称
    model: str                         # 使用的模型
    input: Any                         # 输入内容
    output: Any                        # 输出内容
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    status: SpanStatus = SpanStatus.SUCCESS
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class TraceData:
    """一次完整任务的追踪数据"""
    trace_id: str                      # 任务 ID
    name: str                          # 任务名称（可读）
    input: Any                         # 最初的输入
    output: Any                        # 最终的输出
    task_mode: str = ""                # 任务模式：parallel / pipeline / smart_route
    source_system: str = ""            # 来源业务系统
    task_type: str = ""                # 任务类型
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    status: SpanStatus = SpanStatus.SUCCESS
    error: Optional[str] = None
    spans: list[SpanData] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class BaseTracer(ABC):
    """
    追踪后端的抽象基类。
    所有具体实现（Langfuse、控制台、文件等）都继承这个类。
    """

    @abstractmethod
    def record(self, trace: TraceData) -> None:
        """记录一条完整的 Trace（含所有 Span）"""
        pass

    @abstractmethod
    def flush(self) -> None:
        """确保所有数据已发送（程序退出前调用）"""
        pass


class NoopTracer(BaseTracer):
    """
    空追踪器：什么都不做。
    用于测试、或者不需要追踪的场景。
    """

    def record(self, trace: TraceData) -> None:
        pass

    def flush(self) -> None:
        pass


class ConsoleTracer(BaseTracer):
    """
    控制台追踪器：把 Trace 打印到终端。
    用于本地调试，不依赖任何外部服务。
    """

    def record(self, trace: TraceData) -> None:
        status_icon = "✅" if trace.status == SpanStatus.SUCCESS else "❌"
        print(f"\n{'─'*50}")
        print(f"{status_icon} Trace [{trace.trace_id}] {trace.name}")
        print(f"   来源: {trace.source_system or '未指定'} | "
              f"模式: {trace.task_mode} | "
              f"类型: {trace.task_type or '未指定'}")
        print(f"   Token: {trace.total_tokens} | "
              f"耗时: {trace.total_latency_ms:.0f}ms")
        if trace.error:
            print(f"   错误: {trace.error}")
        for span in trace.spans:
            s_icon = "✅" if span.status == SpanStatus.SUCCESS else "❌"
            print(f"   {s_icon} [{span.name}] 模型={span.model} "
                  f"tokens={span.total_tokens} "
                  f"latency={span.latency_ms:.0f}ms")
        print(f"{'─'*50}\n")

    def flush(self) -> None:
        pass
