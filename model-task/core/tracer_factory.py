"""
core/tracer_factory.py

追踪器工厂：根据配置创建对应的追踪后端。
切换追踪后端只需要改环境变量，代码不用动。

TRACER_BACKEND=console     → 打印到终端（默认，本地调试用）
TRACER_BACKEND=langfuse    → 写入 Langfuse
TRACER_BACKEND=noop        → 不追踪
"""

import os
from core.tracer import BaseTracer, NoopTracer, ConsoleTracer


def create_tracer(backend: str = None) -> BaseTracer:
    """
    根据 backend 参数创建追踪器。
    不传则读环境变量 TRACER_BACKEND，默认 console。
    """
    backend = backend or os.environ.get("TRACER_BACKEND", "console")

    if backend == "langfuse":
        from core.langfuse_tracer import LangfuseTracer
        return LangfuseTracer()

    elif backend == "console":
        return ConsoleTracer()

    elif backend == "noop":
        return NoopTracer()

    else:
        print(f"[TracerFactory] 未知 backend: {backend}，使用 console")
        return ConsoleTracer()
