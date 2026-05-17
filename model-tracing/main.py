"""
main.py

演示三种任务模式 + 追踪层集成。

运行前：
1. 复制 .env.example 为 .env，填入对应的 Key
2. 启动 LiteLLM Proxy：litellm --config config/config.yaml --port 4000
3. （可选）WSL 里启动 Langfuse：docker-compose -f langfuse-docker-compose.yml up -d
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

from core.llm_client import LLMClient
from core.tracer_factory import create_tracer
from tasks.parallel_task import ParallelTask
from tasks.pipeline_task import PipelineTask, PipelineStep
from tasks.smart_route_task import SmartRouteTask

# 追踪后端由 .env 里的 TRACER_BACKEND 控制
# TRACER_BACKEND=console   → 打印到终端（默认）
# TRACER_BACKEND=langfuse  → 写入 Langfuse
# TRACER_BACKEND=noop      → 不追踪

client = LLMClient(
    base_url=os.getenv("LITELLM_BASE_URL", "http://localhost:4000"),
    api_key=os.getenv("LITELLM_MASTER_KEY", "sk-my-master-key-1234"),
)
tracer = create_tracer()


async def demo_parallel():
    print("\n【场景一：并行评测】")
    task = ParallelTask(client, tracer)
    result = await task.run(
        prompt="用三句话解释什么是机器学习",
                models=["minimax-m2-5"],
        source_system="demo",
        task_type="summarization",
    )
    task.print_comparison(result)


async def demo_pipeline():
    print("\n【场景二：流水线任务】")
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
            prompt_template=(
                "原始主题：{original_input}\n"
                "关键词：{input}\n\n"
                "基于以上信息，生成一个文章大纲（3个章节）："
            ),
        ),
        PipelineStep(
            name="扩写正文",
            model="minimax-m2-5",
            prompt_template="根据以下大纲，写一篇500字左右的完整文章：\n{input}",
            temperature=0.8,
        ),
    ]
    result = await task.run(
        initial_input="人工智能对教育行业的影响",
        steps=steps,
        source_system="demo",
        task_type="long_generation",
    )
    if result.success:
        print(f"最终输出（前200字）：\n{str(result.final_output)[:200]}...")
    for s in result.steps:
        print(f"  [{s.step_name}] 模型={s.model} tokens={s.tokens}")


async def demo_smart_route_classify():
    print("\n【场景三：智能路由 - 路由逻辑验证】")
    task = SmartRouteTask(client, tracer)
    prompts = [
        "写一个 Python 函数计算斐波那契数列",
        "为什么人工智能会产生幻觉？从技术角度分析",
        "把这句话翻译成英文：今天天气真好",
        "你好，今天怎么样",
    ]
    for prompt in prompts:
        task_type, model, rule = task.classify(prompt)
        print(f"  输入: {prompt[:25]}...")
        print(f"  → 类型: {task_type.value} | 模型: {model}")
        print(f"  → 规则: {rule}\n")


async def main():
    # 路由验证：不需要启动 LiteLLM Proxy
    await demo_smart_route_classify()

    # 以下需要 LiteLLM Proxy 运行
    await demo_parallel()
    await demo_pipeline()

    tracer.flush()


if __name__ == "__main__":
    asyncio.run(main())
