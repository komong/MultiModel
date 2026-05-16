"""
core/langfuse_tracer.py

Langfuse 追踪后端实现。
继承 BaseTracer，把 TraceData 写入 Langfuse。

依赖：
    pip install langfuse

环境变量（在 .env 里配置）：
    LANGFUSE_PUBLIC_KEY=pk-lf-...
    LANGFUSE_SECRET_KEY=sk-lf-...
    LANGFUSE_HOST=http://localhost:3000   # 本地 Docker
"""

import os
from core.tracer import BaseTracer, TraceData, SpanData, SpanStatus


class LangfuseTracer(BaseTracer):
    """
    Langfuse 追踪后端。
    把每一条 TraceData 写成 Langfuse 的 Trace + Generation 结构。
    """

    def __init__(
        self,
        public_key: str = None,
        secret_key: str = None,
        host: str = None,
    ):
        try:
            from langfuse import Langfuse
        except ImportError:
            raise ImportError(
                "请先安装 langfuse：pip install langfuse"
            )

        self.client = Langfuse(
            public_key=public_key or os.environ.get("LANGFUSE_PUBLIC_KEY"),
            secret_key=secret_key or os.environ.get("LANGFUSE_SECRET_KEY"),
            host=host or os.environ.get("LANGFUSE_HOST", "http://localhost:3000"),
        )

    def record(self, trace: TraceData) -> None:
        """
        写入 Langfuse：
        - 一个 Trace 对应一次任务
        - 每个 Span 对应任务里的一个步骤，写成 Generation
        """
        try:
            # 创建 Trace
            lf_trace = self.client.trace(
                id=trace.trace_id,
                name=trace.name,
                input=trace.input,
                output=trace.output,
                metadata={
                    "task_mode": trace.task_mode,
                    "source_system": trace.source_system,
                    "task_type": trace.task_type,
                    "total_tokens": trace.total_tokens,
                    "total_latency_ms": trace.total_latency_ms,
                    **trace.metadata,
                },
                tags=[
                    trace.task_mode,
                    trace.source_system,
                    trace.task_type,
                    trace.status.value,
                ],
            )

            # 每个 Span 写成一个 Generation
            for span in trace.spans:
                lf_trace.generation(
                    name=span.name,
                    model=span.model,
                    input=span.input,
                    output=span.output,
                    usage={
                        "input": span.input_tokens,
                        "output": span.output_tokens,
                        "total": span.total_tokens,
                    },
                    metadata={
                        "latency_ms": span.latency_ms,
                        "status": span.status.value,
                        "error": span.error,
                        **span.metadata,
                    },
                    level="ERROR" if span.status == SpanStatus.ERROR else "DEFAULT",
                )

        except Exception as e:
            # 追踪失败不应该影响主流程，只打印警告
            print(f"[LangfuseTracer] 写入失败: {e}")

    def flush(self) -> None:
        """确保所有数据已发送到 Langfuse"""
        try:
            self.client.flush()
        except Exception as e:
            print(f"[LangfuseTracer] flush 失败: {e}")
