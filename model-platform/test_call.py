"""
LiteLLM Proxy 虚拟 Key 自动化测试

测试流程:
  1. 连通性检查（Master Key）
  2. 动态生成 3 个不同权限的 Key
  3. 权限隔离测试（正向 + 反向）
  4. Key 查询验证
  5. Key 更新验证（权限变更）
  6. Key 吊销验证（吊销后不可用）
  7. 清理（删除所有测试 Key）

前置条件:
  - LiteLLM Proxy 运行中（py start_proxy.py）
  - PostgreSQL 运行中

用法:
  py test_call.py
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import requests

# 加载项目根目录 .env
load_dotenv(Path(__file__).parent.parent / '.env')

PROXY_URL = os.getenv("LITELLM_BASE_URL", "http://localhost:4800")
PROXY_V1 = f"{PROXY_URL}/v1"
MASTER_KEY = os.getenv("LITELLM_MASTER_KEY", "sk-my-master-key-1234")

# 测试用的 Key 配置
TEST_KEY_CONFIGS = [
    {
        "name": "test-minimax",
        "models": ["minimax-m2-5", "minimax-m2-7"],
        "budget": 5,
    },
    {
        "name": "test-deepseek",
        "models": ["deepseek-v4-flash", "deepseek-v4-pro"],
        "budget": 5,
    },
    {
        "name": "test-all",
        "models": [
            "minimax-m2-5", "minimax-m2-7",
            "deepseek-v4-flash", "deepseek-v4-pro",
            "glm-5-1",
        ],
        "budget": None,
    },
]


# ── 工具函数 ──────────────────────────────────────────────


def _headers():
    return {
        "Authorization": f"Bearer {MASTER_KEY}",
        "Content-Type": "application/json",
    }


def _call_model(api_key, model, prompt="1+1=?"):
    """用指定 Key 调用模型，返回 (success, detail)"""
    try:
        client = OpenAI(api_key=api_key, base_url=PROXY_V1)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
        )
        return True, response.choices[0].message.content.strip()[:30]
    except Exception as e:
        return False, str(e)[:80]


def _generate_key(name, models, budget=None):
    """调用 API 生成 Key"""
    payload = {
        "models": models,
        "metadata": {"system": name},
    }
    if budget:
        payload["max_budget"] = budget

    resp = requests.post(
        f"{PROXY_URL}/key/generate",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    data = resp.json()
    if not resp.ok:
        print(f"  [ERROR] 生成失败: {data}")
        return None
    key = data.get("key") or data.get("token")
    return key


def _delete_key(key):
    """吊销 Key"""
    try:
        requests.post(
            f"{PROXY_URL}/key/delete",
            headers=_headers(),
            json={"keys": [key]},
            timeout=30,
        )
    except Exception:
        pass


def _update_key(key, **kwargs):
    """更新 Key"""
    payload = {"key": key}
    payload.update(kwargs)
    resp = requests.post(
        f"{PROXY_URL}/key/update",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    return resp.ok, resp.json()


# ── 测试统计 ──────────────────────────────────────────────


class TestStats:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, label):
        self.passed += 1
        print(f"  [PASS] {label}")

    def fail(self, label, detail=""):
        self.failed += 1
        msg = f"  [FAIL] {label}"
        if detail:
            msg += f" — {detail}"
        print(msg)
        self.errors.append(label)

    def check(self, condition, label, detail=""):
        if condition:
            self.ok(label)
        else:
            self.fail(label, detail)

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*70}")
        print(f"测试结果: {self.passed} 通过, {self.failed} 失败, {total} 总计")
        if self.errors:
            print(f"失败项:")
            for e in self.errors:
                print(f"  - {e}")
        print(f"{'='*70}\n")
        return self.failed == 0


# ── 测试步骤 ──────────────────────────────────────────────


def test_connectivity(stats):
    """步骤 1: Master Key 连通性"""
    print("\n[步骤 1] 连通性检查 (Master Key)")
    print("-" * 50)

    success, detail = _call_model(MASTER_KEY, "deepseek-v4-flash")
    stats.check(success, "Master Key 调用 deepseek-v4-flash", detail)


def test_generate_keys(stats):
    """步骤 2: 动态生成 Key"""
    print("\n[步骤 2] 动态生成测试 Key")
    print("-" * 50)

    keys = {}
    for cfg in TEST_KEY_CONFIGS:
        key = _generate_key(cfg["name"], cfg["models"], cfg["budget"])
        stats.check(key is not None, f"生成 {cfg['name']}")
        if key:
            keys[cfg["name"]] = key
            print(f"    {cfg['name']}: {key[:12]}...")
    return keys


def test_permission_isolation(stats, keys):
    """步骤 3: 权限隔离测试"""
    print("\n[步骤 3] 权限隔离测试")
    print("-" * 50)

    cases = [
        ("test-minimax", "minimax-m2-5", True),
        ("test-minimax", "deepseek-v4-flash", False),
        ("test-deepseek", "deepseek-v4-flash", True),
        ("test-deepseek", "minimax-m2-5", False),
        ("test-all", "minimax-m2-5", True),
        ("test-all", "deepseek-v4-flash", True),
        ("test-all", "glm-5-1", True),
    ]

    for key_name, model, expected_success in cases:
        if key_name not in keys:
            stats.fail(f"{key_name} -> {model}", "Key 未生成")
            continue

        success, detail = _call_model(keys[key_name], model)
        label = f"{key_name} -> {model} ({'允许' if expected_success else '拦截'})"
        stats.check(success == expected_success, label, detail)


def test_query_key(stats, keys):
    """步骤 4: Key 查询验证"""
    print("\n[步骤 4] Key 查询验证")
    print("-" * 50)

    test_key = keys.get("test-minimax")
    if not test_key:
        stats.fail("查询 test-minimax 详情", "Key 不存在")
        return

    try:
        resp = requests.post(
            f"{PROXY_URL}/v2/key/info",
            headers=_headers(),
            json={"keys": [test_key]},
            timeout=30,
        )
        data = resp.json()
        # LiteLLM 1.87+ 响应格式: {"key": [...], "info": [{...}]}
        info_list = data.get("info", [])
        if isinstance(info_list, list) and info_list:
            info = info_list[0]
        else:
            info = data.get("key", data) if isinstance(data.get("key"), dict) else data

        # 验证返回的信息包含模型列表
        models = info.get("models", [])
        has_models = "minimax-m2-5" in str(models)
        stats.check(has_models, "查询返回正确的模型范围", f"models={models}")
    except Exception as e:
        stats.fail("查询 test-minimax 详情", str(e))


def test_update_key(stats, keys):
    """步骤 5: Key 更新验证"""
    print("\n[步骤 5] Key 更新验证（权限变更）")
    print("-" * 50)

    # 使用 test-deepseek，先更新为只有 minimax 权限
    test_key = keys.get("test-deepseek")
    if not test_key:
        stats.fail("更新 test-deepseek 权限", "Key 不存在")
        return

    # 更新模型范围
    ok, data = _update_key(test_key, models=["minimax-m2-5"])
    stats.check(ok, "更新模型范围为 minimax-m2-5", str(data) if not ok else "")

    if ok:
        # 等待生效
        time.sleep(1)

        # 验证：原本可用的 deepseek 现在应该被拦截
        success, detail = _call_model(test_key, "deepseek-v4-flash")
        stats.check(not success, "更新后 deepseek-v4-flash 被拦截", detail)

        # 验证：新授权的 minimax 应该可用
        success, detail = _call_model(test_key, "minimax-m2-5")
        stats.check(success, "更新后 minimax-m2-5 可用", detail)

    # 恢复原始权限
    ok_restore, _ = _update_key(test_key, models=["deepseek-v4-flash", "deepseek-v4-pro"])
    stats.check(ok_restore, "恢复 test-deepseek 原始权限")


def test_delete_key(stats, keys):
    """步骤 6: Key 吊销验证"""
    print("\n[步骤 6] Key 吊销验证")
    print("-" * 50)

    test_key = keys.get("test-minimax")
    if not test_key:
        stats.fail("吊销 test-minimax", "Key 不存在")
        return

    # 吊销
    try:
        resp = requests.post(
            f"{PROXY_URL}/key/delete",
            headers=_headers(),
            json={"keys": [test_key]},
            timeout=30,
        )
        stats.check(resp.ok, "吊销 Key 请求成功", resp.text if not resp.ok else "")
    except Exception as e:
        stats.fail("吊销 Key 请求", str(e))
        return

    # 等待生效
    time.sleep(1)

    # 验证：吊销后的 Key 无法调用
    success, detail = _call_model(test_key, "minimax-m2-5")
    stats.check(not success, "吊销后 Key 无法调用", detail)

    # 从待清理列表中移除（已吊销）
    if "test-minimax" in keys:
        del keys["test-minimax"]


def cleanup_keys(keys):
    """步骤 7: 清理测试 Key"""
    print("\n[步骤 7] 清理测试 Key")
    print("-" * 50)

    for name, key in keys.items():
        _delete_key(key)
        print(f"  [清理] {name}: {key[:12]}...")

    print("  清理完毕")


# ── 主入口 ────────────────────────────────────────────────


def main():
    stats = TestStats()

    print("=" * 70)
    print(f"{'LiteLLM Proxy 虚拟 Key 自动化测试':^70}")
    print(f"{'='*70}")
    print(f"Proxy:  {PROXY_URL}")
    print(f"Master: {MASTER_KEY[:10]}...")

    # 连通性检查
    try:
        resp = requests.get(f"{PROXY_URL}/health", timeout=5)
        if resp.status_code not in (200, 401):
            print(f"\n[ERROR] Proxy 健康检查异常: {resp.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 无法连接 Proxy: {e}")
        print("请先启动: cd model-platform; py start_proxy.py")
        sys.exit(1)

    # 执行测试
    test_connectivity(stats)

    keys = test_generate_keys(stats)
    if not keys:
        print("\n[ERROR] Key 生成失败，无法继续测试")
        sys.exit(1)

    test_permission_isolation(stats, keys)
    test_query_key(stats, keys)
    test_update_key(stats, keys)
    test_delete_key(stats, keys)

    # 清理
    cleanup_keys(keys)

    # 汇总
    all_passed = stats.summary()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
