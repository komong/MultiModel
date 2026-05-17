"""
tasks/pipeline_task.py

场景二：流水线任务，按步骤拆分，不同步骤用不同模型。
每一步的输出作为下一步的输入。
"""

import uuid
from dataclasses import dataclass
from core.llm_client import LLMClient
from core.task import TaskMode, TaskResult, StepResult
from core.tracer import BaseTracer, TraceData, SpanData, SpanStatus, NoopTracer


@dataclass
class PipelineStep:
    """
    流水线中的单个步骤定义。
    prompt_template 中用 {input} 引用上一步的输出，
    也可以用 {original_input} 引用最初的用户输入。
    """
    name: str
    model: str
    prompt_template: str
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048


class PipelineTask:
    def __init__(self, client: LLMClient, tracer: BaseTracer = None):
        self.client = client
        self.tracer = tracer or NoopTracer()

    async def run(
        self,
        initial_input: str,
        steps: list[PipelineStep],
        task_id: str = None,
        source_system: str = "",
        task_type: str = "",
    ) -> TaskResult:

        task_id = task_id or str(uuid.uuid4())[:8]
        context = {"input": initial_input, "original_input": initial_input}
        step_results = []
        total_tokens = 0
        total_latency = 0.0

        for step in steps:
            try:
                prompt = step.prompt_template.format(**context)
            except KeyError as e:
                result = TaskResult(
                    task_id=task_id,
                    task_mode=TaskMode.PIPELINE,
                    final_output=None,
                    steps=step_results,
                    success=False,
                    error=f"步骤 [{step.name}] prompt 模板变量错误: {e}",
                )
                self._record(result, initial_input, source_system, task_type)
                return result

            messages = []
            if step.system_prompt:
                messages.append({"role": "system", "content": step.system_prompt})
            messages.append({"role": "user", "content": prompt})

            resp = await self.client.call(
                model=step.model,
                messages=messages,
                temperature=step.temperature,
                max_tokens=step.max_tokens,
            )

            step_result = StepResult(
                step_name=step.name,
                model=step.model,
                input=prompt,
                output=resp.content if resp.success else "",
                tokens=resp.total_tokens,
                latency_ms=resp.latency_ms,
                success=resp.success,
                error=resp.error,
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
            )
            step_results.append(step_result)
            total_tokens += resp.total_tokens
            total_latency += resp.latency_ms

            if not resp.success:
                result = TaskResult(
                    task_id=task_id,
                    task_mode=TaskMode.PIPELINE,
                    final_output=None,
                    steps=step_results,
                    total_tokens=total_tokens,
                    total_latency_ms=total_latency,
                    success=False,
                    error=f"步骤 [{step.name}] 失败: {resp.error}",
                )
                self._record(result, initial_input, source_system, task_type)
                return result

            context["input"] = resp.content
            context[f"step_{step.name}"] = resp.content

        result = TaskResult(
            task_id=task_id,
            task_mode=TaskMode.PIPELINE,
            final_output=context["input"],
            steps=step_results,
            total_tokens=total_tokens,
            total_latency_ms=total_latency,
            success=True,
        )
        self._record(result, initial_input, source_system, task_type)
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
            name=f"pipeline:{task_type or 'task'}",
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
