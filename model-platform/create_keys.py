"""
虚拟 Key 管理工具 — LiteLLM Proxy

用法:
  py create_keys.py generate                     # 预定义模板批量生成
  py create_keys.py generate --name my-app --models minimax-m2-5 --budget 5
  py create_keys.py list                         # 列出所有 Key
  py create_keys.py info <key_or_id>             # 查看 Key 详情
  py create_keys.py delete <key_or_id>           # 吊销 Key
  py create_keys.py update <key_or_id> --budget 30  # 更新预算
  py create_keys.py update <key_or_id> --models minimax-m2-5 deepseek-v4-flash

前置条件:
  - LiteLLM Proxy 运行中（py start_proxy.py）
  - PostgreSQL 运行中（Key 持久化依赖数据库）
"""

import argparse
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录 .env
load_dotenv(Path(__file__).parent.parent / '.env')

MASTER_KEY = os.getenv('LITELLM_MASTER_KEY', 'sk-my-master-key-1234')
PROXY_URL = os.getenv('LITELLM_BASE_URL', 'http://localhost:4800')


# ── 公共工具 ──────────────────────────────────────────────


def _headers():
    """构造认证请求头"""
    return {
        "Authorization": f"Bearer {MASTER_KEY}",
        "Content-Type": "application/json",
    }


def check_proxy():
    """检查 Proxy 是否可达，不可达则退出"""
    try:
        resp = requests.get(f"{PROXY_URL}/health", timeout=5)
        if resp.status_code in (200, 401):
            return True
        print(f"[WARN] Proxy 健康检查返回 {resp.status_code}")
        return True
    except Exception as e:
        print(f"[ERROR] 无法连接 LiteLLM Proxy: {PROXY_URL}")
        print(f"  详情: {e}")
        print("  请先启动: cd model-platform; py start_proxy.py")
        sys.exit(1)


# ── 预定义模板 ────────────────────────────────────────────

PRESET_TEMPLATES = [
    {
        "name": "system-a",
        "description": "MiniMax 专用",
        "models": ["minimax-m2-5", "minimax-m2-7"],
        "budget": 10,
    },
    {
        "name": "system-b",
        "description": "DeepSeek 专用",
        "models": ["deepseek-v4-flash", "deepseek-v4-pro"],
        "budget": 20,
    },
    {
        "name": "system-c",
        "description": "全部模型",
        "models": [
            "minimax-m2-5", "minimax-m2-7",
            "deepseek-v4-flash", "deepseek-v4-pro",
            "glm-5-1",
        ],
        "budget": None,
    },
]


# ── 子命令实现 ────────────────────────────────────────────


def cmd_generate(args):
    """生成虚拟 Key"""
    if args.name or args.models:
        # 自定义生成模式
        name = args.name or "custom"
        models = args.models
        budget = args.budget
        data = _do_generate(name, models, budget)
        if data:
            _print_key_result(name, data)
    else:
        # 预定义模板批量生成
        print(f"Proxy: {PROXY_URL}")
        print(f"Master Key: {MASTER_KEY[:10]}...")
        print()

        results = {}
        for tpl in PRESET_TEMPLATES:
            data = _do_generate(tpl["name"], tpl["models"], tpl["budget"])
            if data:
                _print_key_result(tpl["name"], data, tpl["description"])
                key = data.get("key") or data.get("token", "N/A")
                results[tpl["name"]] = key

        if results:
            print("─" * 60)
            print("生成完毕，使用方式:")
            print(f'  client = OpenAI(api_key="<key>", base_url="{PROXY_URL}/v1")')

        return results


def _do_generate(name, models, budget=None):
    """调用 API 生成单个 Key"""
    payload = {
        "models": models,
        "metadata": {"system": name},
    }
    if budget:
        payload["max_budget"] = budget

    try:
        resp = requests.post(
            f"{PROXY_URL}/key/generate",
            headers=_headers(),
            json=payload,
            timeout=30,
        )
        data = resp.json()
        if not resp.ok:
            print(f"[{name}] 生成失败: {data}")
            return None
        return data
    except Exception as e:
        print(f"[{name}] 请求异常: {e}")
        return None


def _print_key_result(name, data, description=""):
    """打印单个 Key 生成结果"""
    key = data.get("key") or data.get("token", "N/A")
    key_id = data.get("key_id", "")
    models = data.get("models", [])
    budget = data.get("max_budget", "")

    desc_str = f" ({description})" if description else ""
    print(f"[{name}]{desc_str}")
    print(f"  Key:     {key}")
    if key_id:
        print(f"  Key ID:  {key_id}")
    if models:
        print(f"  Models:  {models}")
    if budget:
        print(f"  Budget:  ${budget}")
    print()


def cmd_list(args):
    """列出所有虚拟 Key"""
    try:
        resp = requests.get(
            f"{PROXY_URL}/key/list",
            headers=_headers(),
            timeout=30,
        )
        data = resp.json()

        keys = data if isinstance(data, list) else data.get("keys", data.get("data", []))

        if not keys:
            print("当前没有任何虚拟 Key")
            return

        print(f"\n{'='*80}")
        print(f"{'虚拟 Key 列表':^80}")
        print(f"{'='*80}")

        for k in keys:
            # 兼容不同的响应结构
            key_name = (k.get("metadata") or {}).get("system", "")
            models = k.get("models", [])
            status = k.get("status", "active")
            budget = k.get("max_budget", "")
            key_id = k.get("key_id", k.get("token", ""))
            spend = k.get("spend", 0)

            if key_name:
                print(f"  名称:    {key_name}")
            if key_id:
                # 只显示部分 Key，避免泄露
                display = key_id[:8] + "..." if len(key_id) > 12 else key_id
                print(f"  Key ID:  {display}")
            if models:
                print(f"  模型:    {', '.join(models) if isinstance(models, list) else models}")
            if budget:
                print(f"  预算:    ${budget}")
            if spend:
                print(f"  已用:    ${spend}")
            print(f"  状态:    {status}")
            print()

        print(f"共 {len(keys)} 个 Key")
        print(f"{'='*80}\n")

    except Exception as e:
        print(f"[ERROR] 查询失败: {e}")
        sys.exit(1)


def cmd_info(args):
    """查询单个 Key 详情"""
    key_or_id = args.key

    try:
        resp = requests.post(
            f"{PROXY_URL}/key/info",
            headers=_headers(),
            json={"key": key_or_id},
            timeout=30,
        )
        data = resp.json()

        if not resp.ok:
            print(f"[ERROR] 查询失败: {data.get('error', data)}")
            sys.exit(1)

        info = data.get("info", data.get("key", data))

        print(f"\n{'='*60}")
        print(f"Key 详情")
        print(f"{'='*60}")

        # 基本信息
        key_name = (info.get("metadata") or {}).get("system", "")
        if key_name:
            print(f"  名称:      {key_name}")

        key_id = info.get("key_id", info.get("token", ""))
        if key_id:
            display = key_id[:8] + "..." if len(key_id) > 12 else key_id
            print(f"  Key ID:    {display}")

        models = info.get("models", [])
        if models:
            print(f"  可用模型:  {', '.join(models) if isinstance(models, list) else models}")

        budget = info.get("max_budget", "")
        if budget:
            print(f"  预算上限:  ${budget}")

        spend = info.get("spend", 0)
        if spend:
            print(f"  已使用:    ${spend}")

        status = info.get("status", info.get("active", ""))
        if status:
            print(f"  状态:      {status}")

        expires = info.get("expires", "")
        if expires:
            print(f"  过期时间:  {expires}")

        # 元数据
        metadata = info.get("metadata", {})
        if metadata and key_name not in str(metadata):
            print(f"  元数据:    {metadata}")

        print(f"{'='*60}\n")

    except Exception as e:
        print(f"[ERROR] 查询失败: {e}")
        sys.exit(1)


def cmd_delete(args):
    """吊销虚拟 Key"""
    key_or_id = args.key

    # 确认提示
    if not args.yes:
        confirm = input(f"确认吊销 Key [{key_or_id[:12]}...]? (y/N): ").strip().lower()
        if confirm != 'y':
            print("已取消")
            return

    try:
        resp = requests.post(
            f"{PROXY_URL}/key/delete",
            headers=_headers(),
            json={"keys": [key_or_id]},
            timeout=30,
        )
        data = resp.json()

        if not resp.ok:
            print(f"[ERROR] 吊销失败: {data.get('error', data)}")
            sys.exit(1)

        print(f"[OK] Key 已吊销: {key_or_id[:12]}...")

    except Exception as e:
        print(f"[ERROR] 吊销失败: {e}")
        sys.exit(1)


def cmd_update(args):
    """更新虚拟 Key 配置"""
    key_or_id = args.key

    payload = {"key": key_or_id}

    if args.models is not None:
        payload["models"] = args.models
    if args.budget is not None:
        payload["max_budget"] = args.budget

    if len(payload) <= 1:
        print("[ERROR] 请指定要更新的内容: --models 和/或 --budget")
        sys.exit(1)

    try:
        resp = requests.post(
            f"{PROXY_URL}/key/update",
            headers=_headers(),
            json=payload,
            timeout=30,
        )
        data = resp.json()

        if not resp.ok:
            print(f"[ERROR] 更新失败: {data.get('error', data)}")
            sys.exit(1)

        print(f"[OK] Key 已更新: {key_or_id[:12]}...")
        if args.models is not None:
            print(f"  模型范围: {args.models}")
        if args.budget is not None:
            print(f"  预算上限: ${args.budget}")

    except Exception as e:
        print(f"[ERROR] 更新失败: {e}")
        sys.exit(1)


# ── 入口 ──────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="LiteLLM Proxy 虚拟 Key 管理工具",
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # generate
    gen_parser = subparsers.add_parser("generate", help="生成虚拟 Key")
    gen_parser.add_argument("--name", help="Key 名称（不填则使用预定义模板批量生成）")
    gen_parser.add_argument("--models", nargs="+", help="可用模型列表")
    gen_parser.add_argument("--budget", type=float, help="月预算上限（美元）")

    # list
    subparsers.add_parser("list", help="列出所有虚拟 Key")

    # info
    info_parser = subparsers.add_parser("info", help="查看 Key 详情")
    info_parser.add_argument("key", help="Key 或 Key ID")

    # delete
    del_parser = subparsers.add_parser("delete", help="吊销虚拟 Key")
    del_parser.add_argument("key", help="Key 或 Key ID")
    del_parser.add_argument("--yes", "-y", action="store_true", help="跳过确认提示")

    # update
    upd_parser = subparsers.add_parser("update", help="更新 Key 配置")
    upd_parser.add_argument("key", help="Key 或 Key ID")
    upd_parser.add_argument("--models", nargs="+", help="新的模型范围")
    upd_parser.add_argument("--budget", type=float, help="新的预算上限")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # 前置检查
    check_proxy()

    # 分发子命令
    cmd_map = {
        "generate": cmd_generate,
        "list": cmd_list,
        "info": cmd_info,
        "delete": cmd_delete,
        "update": cmd_update,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
