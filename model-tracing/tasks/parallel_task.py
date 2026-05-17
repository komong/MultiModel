"""
tasks/parallel_task.py

场景一：多模型并行执行同一任务，结果对比。
主要用于评测：同一个输入，看哪个模型输出更好。
"""

import asyncio
import uuid
from core.llm_client import LLMClient
from core.task import TaskMode, TaskResult, StepResult
from core.tracer import BaseTracer, TraceData, SpanData, SpanStatus, NoopTracer


class ParallelTask:
    def __init__(self, client: LLMClient, tracer: BaseTracer = None):
        self.client = client
        self.tracer = tracer or NoopTracer()

    async def run(
        self,
        prompt: str,
        models: list[str],
        system_prompt: str = "",
        task_id: str = None,
        source_system: str = "",
        task_type: str = "",
    ) -> TaskResult:

        task_id = task_id or str(uuid.uuid4())[:8]

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        coroutines = [self.client.call(model=m, messages=messages) for m in models]
        responses = await asyncio.gather(*coroutines)

        steps = []
        total_tokens = 0

        for model, resp in zip(models, responses):
            step = StepResult(
                step_name=f"model_{model}",
                model=model,
                input=prompt,
                output=resp.content if resp.success else "",
                tokens=resp.total_tokens,
                latency_ms=resp.latency_ms,
                success=resp.success,
                error=resp.error,
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
            )
            steps.append(step)
            total_tokens += resp.total_tokens

        final_output = [
            {
                "model": s.model,
                "output": s.output,
                "tokens": s.tokens,
                "latency_ms": s.latency_ms,
                "success": s.success,
            }
            for s in steps
        ]

        result = TaskResult(
            task_id=task_id,
            task_mode=TaskMode.PARALLEL,
            final_output=final_output,
            steps=steps,
            total_tokens=total_tokens,
            total_latency_ms=max(s.latency_ms for s in steps),
            success=any(s.success for s in steps),
        )

        self._record(result, prompt, source_system, task_type)
        return result

    def _record(self, result, original_input, source_system, task_type):
        spans = [
            SpanData(
                name=s.step_name,
                model=s.model,
                input=s.input,
                output=s.output,
                input_tokens=s.input_tokens,
                output_tokens=s.output_tokens,
                total_tokens=s.tokens,
                latency_ms=s.latency_ms,
                status=SpanStatus.SUCCESS if s.success else SpanStatus.ERROR,
                error=s.error,
            )
            for s in result.steps
        ]
        trace = TraceData(
            trace_id=result.task_id,
            name=f"parallel:{task_type or 'task'}",
            input=original_input,
            output=result.final_output,
            task_mode=result.task_mode.value,
            source_system=source_system,
            task_type=task_type,
            total_tokens=result.total_tokens,
            total_latency_ms=result.total_latency_ms,
            status=SpanStatus.SUCCESS if result.success else SpanStatus.ERROR,
            error=result.error,
            spans=spans,
        )
        self.tracer.record(trace)

    def print_comparison(self, result: TaskResult):
        print(f"\n{'='*60}")
        print(f"任务 ID: {result.task_id} | 总 Token: {result.total_tokens}")
        print(f"{'='*60}")
        for item in result.final_output:
            status = "✅" if item["success"] else "❌"
            print(f"\n{status} [{item['model']}] "
                  f"tokens={item['tokens']} latency={item['latency_ms']}ms")
            print(f"{'-'*40}")
            print(item["output"] if item["success"] else f"错误")
        print(f"\n{'='*60}\n")
