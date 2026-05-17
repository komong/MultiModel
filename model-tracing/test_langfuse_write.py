"""
test_langfuse_write.py

Langfuse 写入测试：验证当前配置下 API 是否能正常写入 Trace + Generation 数据。
"""

import sys
import time
import traceback
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录 .env
load_dotenv(Path(__file__).parent.parent / ".env")


def test_langfuse_write():
    import os

    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    host = os.environ.get("LANGFUSE_HOST", "http://localhost:3000")

    print("=" * 50)
    print("Langfuse 写入测试")
    print("=" * 50)
    print(f"  HOST:        {host}")
    print(f"  PUBLIC_KEY:  {public_key[:12]}..." if public_key else "  PUBLIC_KEY:  未配置!")
    print(f"  SECRET_KEY:  {secret_key[:12]}..." if secret_key else "  SECRET_KEY:  未配置!")

    if not public_key or not secret_key:
        print("\n❌ 缺少 LANGFUSE_PUBLIC_KEY 或 LANGFUSE_SECRET_KEY，请检查 .env")
        return False

    # 1. 初始化客户端
    try:
        from langfuse import Langfuse
        client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            timeout=10,
        )
        print("\n✅ Langfuse 客户端初始化成功")
    except Exception as e:
        print(f"\n❌ Langfuse 客户端初始化失败: {e}")
        traceback.print_exc()
        return False

    # 2. 认证检查
    try:
        auth_ok = client.auth_check()
        print(f"✅ 认证检查: {'通过' if auth_ok else '失败'}")
        if not auth_ok:
            print("❌ 认证未通过，请检查 API Keys")
            return False
    except Exception as e:
        print(f"❌ 认证检查异常: {e}")
        traceback.print_exc()
        return False

    # 3. 方式一：用低级 API create_event 快速验证写入
    print("\n--- 测试方式一：create_event ---")
    ts = int(time.time())
    try:
        event = client.create_event(
            name="test-event",
            input={"prompt": "Hello"},
            output={"text": "World"},
            metadata={"test": True, "timestamp": ts},
        )
        print(f"✅ create_event 成功, id={event.id}")
    except Exception as e:
        print(f"❌ create_event 失败: {e}")
        traceback.print_exc()

    # 4. 方式二：用 v4 API start_observation
    print("\n--- 测试方式二：start_observation (v4 API) ---")
    trace_id = f"test-trace-{ts}"
    try:
        trace_obs = client.start_observation(
            trace_context={
                "id": trace_id,
                "name": "langfuse-write-test",
                "metadata": {"test": True, "timestamp": ts},
            },
            name="langfuse-write-test",
            input={"prompt": "Hello Langfuse"},
        )
        print(f"✅ Trace 创建成功, id={trace_obs.id}")

        # v4 API: 子 observation 通过父 span 的 start_observation 创建
        gen_obs = trace_obs.start_observation(
            name="test-generation",
            as_type="generation",
            model="test-model",
            input={"prompt": "Hello"},
            output={"text": "World"},
            metadata={"latency_ms": 120, "status": "success"},
        )
        gen_obs.update(usage_details={"input": 10, "output": 5, "total": 15})
        gen_obs.end()
        print(f"✅ Generation 创建成功, id={gen_obs.id}")

        trace_obs.update(output={"result": "ok"})
        trace_obs.end()
        print(f"✅ Trace 已关闭")

    except Exception as e:
        print(f"❌ start_observation 失败: {e}")
        traceback.print_exc()

    # 5. flush
    try:
        client.flush()
        print("\n✅ flush 成功，数据已发送到 Langfuse 服务端")
    except Exception as e:
        print(f"❌ flush 失败: {e}")
        traceback.print_exc()
        return False

    print("\n" + "=" * 50)
    print("🎉 Langfuse 写入测试完成！")
    print(f"   请在 Langfuse UI 查看测试数据:")
    print(f"   {host}")
    print(f"   Trace ID: {trace_id}")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = test_langfuse_write()
    sys.exit(0 if success else 1)
