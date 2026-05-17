"""
tasks/smart_route_task.py

场景三：智能路由，根据任务特征自动选最合适的模型。
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional
from core.llm_client import LLMClient
from core.task import TaskMode, TaskResult, StepResult
from core.tracer import BaseTracer, TraceData, SpanData, SpanStatus, NoopTracer


class TaskType(Enum):
    SIMPLE_QA = "simple_qa"
    LONG_GENERATION = "long_gen"
    CODE = "code"
    ANALYSIS = "analysis"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    DEFAULT = "default"


@dataclass
class RoutingRule:
    task_type: TaskType
    model: str
    matcher: Callable[[str], bool]
    priority: int = 0
    description: str = ""


class SmartRouteTask:
    DEFAULT_RULES = [
        # ── 国产模型路由 ──
        RoutingRule(
            task_type=TaskType.CODE,
            model="deepseek-v4-pro",
            matcher=lambda p: any(
                kw in p.lower() for kw in
                ["代码", "函数", "python", "javascript", "bug", "debug",
                 "code", "program", "script", "api", "sql"]
            ),
            priority=10,
            description="代码相关任务 → deepseek-v4-pro",
        ),
        RoutingRule(
            task_type=TaskType.ANALYSIS,
            model="glm-5-1",
            matcher=lambda p: any(
                kw in p.lower() for kw in
                ["分析", "为什么", "原因", "对比", "比较", "评估",
                 "analyze", "compare", "evaluate", "reason"]
            ),
            priority=8,
            description="分析推理任务 → glm-5-1",
        ),
        RoutingRule(
            task_type=TaskType.TRANSLATION,
            model="minimax-m2-5",
            matcher=lambda p: any(
                kw in p.lower() for kw in ["翻译", "translate", "英文", "中文", "日文"]
            ),
            priority=7,
            description="翻译任务 → minimax-m2-5",
        ),
        RoutingRule(
            task_type=TaskType.SUMMARIZATION,
            model="minimax-m2-5",
            matcher=lambda p: any(
                kw in p.lower() for kw in ["总结", "摘要", "归纳", "summarize", "summary"]
            ),
            priority=7,
            description="摘要任务 → minimax-m2-5",
        ),
        RoutingRule(
            task_type=TaskType.LONG_GENERATION,
            model="deepseek-v4-pro",
            matcher=lambda p: len(p) > 300,
            priority=3,
            description="长输入任务 → deepseek-v4-pro",
        ),
        RoutingRule(
            task_type=TaskType.SIMPLE_QA,
            model="deepseek-v4-flash",
            matcher=lambda p: any(
                kw in p.lower() for kw in ["你好", "什么是", "介绍", "解释", "hello", "what is"]
            ),
            priority=2,
            description="简单问答 → deepseek-v4-flash",
        ),
        RoutingRule(
            task_type=TaskType.DEFAULT,
            model="deepseek-v4-flash",
            matcher=lambda p: True,
            priority=0,
            description="默认 → deepseek-v4-flash",
        ),
        # ── 国外模型路由（接入后启用，优先级可按需调整） ──
        # RoutingRule(
        #     task_type=TaskType.CODE,
        #     model="gpt-4o",
        #     matcher=lambda p: any(kw in p.lower() for kw in [...]),
        #     priority=9,
        #     description="代码相关任务 → GPT-4o",
        # ),
        # RoutingRule(
        #     task_type=TaskType.ANALYSIS,
        #     model="claude-sonnet",
        #     matcher=lambda p: any(kw in p.lower() for kw in [...]),
        #     priority=7,
        #     description="分析推理任务 → Claude Sonnet",
        # ),
    ]

    def __init__(self, client: LLMClient, tracer: BaseTracer = None, rules=None):
        self.client = client
        self.tracer = tracer or NoopTracer()
        self.rules = sorted(
            rules or self.DEFAULT_RULES,
            key=lambda r: r.priority,
            reverse=True,
        )

    def classify(self, prompt: str) -> tuple[TaskType, str, str]:
        for rule in self.rules:
            if rule.matcher(prompt):
                return rule.task_type, rule.model, rule.description
        return TaskType.DEFAULT, "deepseek-v4-flash", "fallback"

    async def run(
        self,
        prompt: str,
        system_prompt: str = "",
        task_id: str = None,
        source_system: str = "",
        task_type: str = "",
    ) -> TaskResult:

        task_id = task_id or str(uuid.uuid4())[:8]
        routed_type, model, rule_desc = self.classify(prompt)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        resp = await self.client.call(model=model, messages=messages)

        step = StepResult(
            step_name="smart_route",
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

        result = TaskResult(
            task_id=task_id,
            task_mode=TaskMode.SMART_ROUTE,
            final_output=resp.content if resp.success else None,
            steps=[step],
            total_tokens=resp.total_tokens,
            total_latency_ms=resp.latency_ms,
            success=resp.success,
            error=resp.error,
            metadata={
                "routed_task_type": routed_type.value,
                "model_selected": model,
                "routing_rule": rule_desc,
            },
        )

        # 追踪
        span = SpanData(
            name="smart_route",
            model=model,
            input=prompt,
            output=resp.content if resp.success else "",
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
            total_tokens=resp.total_tokens,
            latency_ms=resp.latency_ms,
            status=SpanStatus.SUCCESS if resp.success else SpanStatus.ERROR,
            error=resp.error,
            metadata={"routing_rule": rule_desc, "routed_type": routed_type.value},
        )
        trace = TraceData(
            trace_id=task_id,
            name=f"smart_route:{task_type or routed_type.value}",
            input=prompt,
            output=resp.content if resp.success else None,
            task_mode=TaskMode.SMART_ROUTE.value,
            source_system=source_system,
            task_type=task_type or routed_type.value,
            total_tokens=resp.total_tokens,
            total_latency_ms=resp.latency_ms,
            status=SpanStatus.SUCCESS if resp.success else SpanStatus.ERROR,
            error=resp.error,
            spans=[span],
        )
        self.tracer.record(trace)

        return result
