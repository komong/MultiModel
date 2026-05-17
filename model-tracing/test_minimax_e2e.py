"""
test_minimax_e2e.py

MiniMax 模型端到端测试：
  LiteLLM Proxy → MiniMax API → Langfuse 追踪写入

运行前确保：
  1. LiteLLM Proxy 已启动：cd model-platform && python start_proxy.py
  2. Langfuse 服务已启动（localhost:3000）
"""

import asyncio
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from core.llm_client import LLMClient
from core.tracer_factory import create_tracer
from tasks.parallel_task import ParallelTask
from tasks.smart_route_task import SmartRouteTask
from tasks.pipeline_task import PipelineTask, PipelineStep


async def test_minimax_basic():
    """测试1：MiniMax M2.5 基本调用"""
    print("\n" + "=" * 60)
    print("测试1：MiniMax M2.5 基本调用 + Langfuse 追踪")
    print("=" * 60)

    client = LLMClient(
        base_url="http://localhost:4800",
        api_key="sk-my-master-key-1234",
    )
    tracer = create_tracer()

    task = ParallelTask(client, tracer)
    result = await task.run(
        prompt="用一句话解释什么是大语言模型",
        models=["minimax-m2-5"],
        source_system="e2e-test",
        task_type="simple_qa",
    )

    if result.success:
        for item in result.final_output:
            status = "OK" if item["success"] else "FAIL"
            print(f"  [{status}] model={item['model']} tokens={item['tokens']} latency={item['latency_ms']:.0f}ms")
            print(f"  输出: {item['output'][:100]}...")
    else:
        print(f"  FAIL: {result.error}")

    tracer.flush()
    return result.success


async def test_minimax_parallel():
    """测试2：MiniMax M2.5 vs M2.7 并行对比"""
    print("\n" + "=" * 60)
    print("测试2：MiniMax M2.5 vs M2.7 并行对比 + Langfuse 追踪")
    print("=" * 60)

    client = LLMClient(
        base_url="http://localhost:4800",
        api_key="sk-my-master-key-1234",
    )
    tracer = create_tracer()

    task = ParallelTask(client, tracer)
    result = await task.run(
        prompt="列举三种常见的机器学习算法并简要说明",
        models=["minimax-m2-5", "minimax-m2-7"],
        source_system="e2e-test",
        task_type="comparison",
    )

    if result.success:
        for item in result.final_output:
            status = "OK" if item["success"] else "FAIL"
            print(f"  [{status}] model={item['model']} tokens={item['tokens']} latency={item['latency_ms']:.0f}ms")
            print(f"  输出: {item['output'][:80]}...")
            print()
    else:
        print(f"  FAIL: {result.error}")

    tracer.flush()
    return result.success


async def test_minimax_pipeline():
    """测试3：MiniMax 流水线任务"""
    print("\n" + "=" * 60)
    print("测试3：MiniMax 流水线（关键词→大纲→正文）+ Langfuse 追踪")
    print("=" * 60)

    client = LLMClient(
        base_url="http://localhost:4800",
        api_key="sk-my-master-key-1234",
    )
    tracer = create_tracer()

    task = PipelineTask(client, tracer)
    steps = [
        PipelineStep(
            name="提取关键词",
            model="minimax-m2-5",
            prompt_template="从以下主题提取5个核心关键词，只输出关键词列表：\n{input}",
        ),
        PipelineStep(
            name="生成大纲",
            model="minimax-m2-5",
            prompt_template="基于以下关键词，生成一个3章节的文章大纲：\n{input}",
        ),
    ]
    result = await task.run(
        initial_input="人工智能在医疗领域的应用",
        steps=steps,
        source_system="e2e-test",
        task_type="pipeline",
    )

    if result.success:
        for s in result.steps:
            status = "OK" if s.success else "FAIL"
            print(f"  [{status}] step={s.step_name} model={s.model} tokens={s.tokens} latency={s.latency_ms:.0f}ms")
        print(f"  最终输出: {str(result.final_output)[:100]}...")
    else:
        print(f"  FAIL: {result.error}")

    tracer.flush()
    return result.success


async def main():
    results = []

    # 测试1
    try:
        r = await test_minimax_basic()
        results.append(("基本调用", r))
    except Exception as e:
        print(f"  异常: {e}")
        results.append(("基本调用", False))

    # 测试2
    try:
        r = await test_minimax_parallel()
        results.append(("并行对比", r))
    except Exception as e:
        print(f"  异常: {e}")
        results.append(("并行对比", False))

    # 测试3
    try:
        r = await test_minimax_pipeline()
        results.append(("流水线", r))
    except Exception as e:
        print(f"  异常: {e}")
        results.append(("流水线", False))

    # 汇总
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    all_ok = True
    for name, ok in results:
        icon = "OK" if ok else "FAIL"
        print(f"  [{icon}] {name}")
        if not ok:
            all_ok = False

    print(f"\n  请在 http://localhost:3000 查看 Langfuse 追踪数据")
    print("=" * 60)

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
