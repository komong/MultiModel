"""
test_minimax_trace.py

调用 MiniMax-M2.5 模型（通过 LiteLLM Proxy），将调用过程写入 Langfuse Trace。
目的：在 Langfuse UI 的 Traces 表中看到一条完整的真实调用记录。
"""

import sys
import time
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 加载项目根目录 .env
load_dotenv(Path(__file__).parent.parent / ".env")


def test_minimax_trace():
    # ===== 1. 初始化 Langfuse =====
    from langfuse import Langfuse

    host = os.environ.get("LANGFUSE_HOST", "http://localhost:3000")
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")

    lf = Langfuse(public_key=public_key, secret_key=secret_key, host=host, timeout=10)

    auth_ok = lf.auth_check()
    print(f"Langfuse 认证: {'✅' if auth_ok else '❌'}")
    if not auth_ok:
        return False

    # ===== 2. 创建一个 Trace =====
    trace_id = f"minimax-test-{int(time.time())}"
    trace = lf.start_observation(
        trace_context={
            "id": trace_id,
            "name": "minimax-chat-test",
            "metadata": {"source": "manual-test", "model": "minimax-m2-5"},
            "tags": ["test", "minimax", "manual"],
        },
        name="minimax-chat-test",
        input={"messages": [{"role": "user", "content": "用一句话介绍广州"}]},
    )
    print(f"Trace 创建成功: {trace_id}")

    # ===== 3. 通过 LiteLLM Proxy 调用 MiniMax 模型 =====
    mm_client = OpenAI(
        api_key=os.getenv("LITELLM_MASTER_KEY", "sk-my-master-key-1234"),
        base_url=os.getenv("LITELLM_BASE_URL", "http://localhost:4800") + "/v1",
    )

    prompt = "用一句话介绍广州"
    start = time.time()

    gen = trace.start_observation(
        name="llm-call",
        as_type="generation",
        model="minimax-m2-5",
        input={"messages": [{"role": "user", "content": prompt}]},
    )

    try:
        resp = mm_client.chat.completions.create(
            model="minimax-m2-5",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200,
        )
        latency_ms = round((time.time() - start) * 1000, 2)

        content = resp.choices[0].message.content
        input_tokens = resp.usage.prompt_tokens
        output_tokens = resp.usage.completion_tokens

        gen.update(
            output={"content": content},
            usage_details={"input": input_tokens, "output": output_tokens, "total": input_tokens + output_tokens},
        )
        gen.end()
        trace.update(output={"content": content})
        trace.end()

        print(f"✅ MiniMax 调用成功")
        print(f"   Content: {content}")
        print(f"   Tokens: {input_tokens} in / {output_tokens} out")
        print(f"   Latency: {latency_ms}ms")

        # ===== 4. 添加一个 Score（评分）=====
        lf.create_score(
            name="response_length",
            value=len(content),
            trace_id=trace_id,
            data_type="NUMERIC",
            comment=f"回复字数: {len(content)}",
        )
        print(f"✅ Score 添加成功: response_length = {len(content)}")

    except Exception as e:
        gen.end()
        trace.update(output={"error": str(e)})
        trace.end()
        print(f"❌ MiniMax 调用失败: {e}")
        return False

    # ===== 5. Flush 确保数据发送 =====
    lf.flush()
    print(f"\n🎉 测试完成！请在 Langfuse UI 查看:")
    print(f"   {host}")
    print(f"   Trace ID: {trace_id}")
    return True


if __name__ == "__main__":
    success = test_minimax_trace()
    sys.exit(0 if success else 1)
