"""
手动更新 LiteLLM 模型定价映射文件。

从 GitHub 下载最新 model_prices_and_context_window.json，
覆盖 LiteLLM 包内置的本地备份，配合 LITELLM_LOCAL_MODEL_COST_MAP=True
彻底消除启动时的 getaddrinfo failed 警告。

用法:
  python scripts/update_cost_map.py                      # 自动检测代理下载并更新
  python scripts/update_cost_map.py --proxy 127.0.0.1:10808  # 指定代理
  python scripts/update_cost_map.py --dry-run            # 仅下载校验，不写入
  python scripts/update_cost_map.py --restore            # 从 .bak 恢复原文件
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

# GitHub 上的最新 cost map URL
REMOTE_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "model_prices_and_context_window.json"
)

# 本地代理端口（按优先级排列）
PROXY_PORTS = [7897, 10808]


def _find_backup_file() -> Optional[Path]:
    """定位 litellm 包的本地备份文件路径。"""
    try:
        # 优先使用 importlib.resources（与 litellm 源码一致）
        from importlib.resources import files

        return Path(str(files("litellm").joinpath("model_prices_and_context_window_backup.json")))
    except Exception:
        pass

    # 回退：直接搜索 site-packages
    try:
        import litellm

        pkg = Path(litellm.__file__).parent
        candidate = pkg / "model_prices_and_context_window_backup.json"
        if candidate.exists():
            return candidate
    except Exception:
        pass

    return None


def _detect_proxy() -> Optional[str]:
    """自动检测可用的 HTTP 代理。

    依次检查环境变量 HTTPS_PROXY / HTTP_PROXY / ALL_PROXY，
    如均未设则按 PROXY_PORTS 顺序探测本地代理。
    """
    for env_key in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY"):
        val = os.environ.get(env_key) or os.environ.get(env_key.lower())
        if val:
            return val

    import urllib.request

    for port in PROXY_PORTS:
        proxy_url = f"http://127.0.0.1:{port}"
        try:
            req = urllib.request.Request(
                "https://raw.githubusercontent.com",
                method="HEAD",
            )
            req.set_proxy(proxy_url, "https")
            urllib.request.urlopen(req, timeout=5)
            return proxy_url
        except Exception:
            continue

    return None


def download_json(url: str, proxy: Optional[str]) -> bytes:
    """通过代理下载 JSON 内容，返回原始字节。"""
    import urllib.request

    req = urllib.request.Request(url)
    if proxy:
        req.set_proxy(proxy, "https")

    print(f"[INFO] 正在下载: {url}")
    if proxy:
        print(f"[INFO] 使用代理: {proxy}")

    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def validate_json(raw: bytes) -> dict:
    """校验下载内容为合法非空 JSON dict。"""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析失败: {e}")

    if not isinstance(data, dict):
        raise ValueError(f"期望 JSON dict，收到: {type(data).__name__}")
    if len(data) == 0:
        raise ValueError("JSON dict 为空")

    # 基本合理性：至少有 100 个模型
    if len(data) < 100:
        raise ValueError(f"模型数量过少 ({len(data)})，可能下载不完整")

    return data


def do_update(dry_run: bool = False, proxy_override: Optional[str] = None) -> bool:
    """执行更新流程。返回 True 表示成功。"""
    # 1. 定位目标文件
    backup_path = _find_backup_file()
    if backup_path is None:
        print("[ERROR] 无法定位 litellm 包的 model_prices_and_context_window_backup.json")
        return False
    print(f"[INFO] 目标文件: {backup_path}")

    # 2. 检测代理
    proxy = proxy_override or _detect_proxy()

    # 3. 下载
    try:
        raw = download_json(REMOTE_URL, proxy)
    except Exception as e:
        print(f"[ERROR] 下载失败: {e}")
        return False

    print(f"[INFO] 下载完成，{len(raw)} 字节")

    # 4. 校验
    try:
        data = validate_json(raw)
    except ValueError as e:
        print(f"[ERROR] 校验失败: {e}")
        return False

    print(f"[INFO] 校验通过，包含 {len(data)} 个模型")

    if dry_run:
        print("[DRY-RUN] 校验通过，未写入文件（--dry-run）")
        return True

    # 5. 备份原文件（如存在）
    bak_path = Path(str(backup_path) + ".bak")
    if backup_path.exists():
        try:
            shutil.copy2(backup_path, bak_path)
            print(f"[INFO] 已备份原文件到: {bak_path}")
        except Exception as e:
            print(f"[WARN] 备份原文件失败: {e}")

    # 6. 写入
    try:
        backup_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[OK] 更新成功！{backup_path}")
    except Exception as e:
        print(f"[ERROR] 写入失败: {e}")
        return False

    return True


def do_restore() -> bool:
    """从 .bak 恢复原文件。"""
    backup_path = _find_backup_file()
    if backup_path is None:
        print("[ERROR] 无法定位 litellm 包路径")
        return False

    bak_path = Path(str(backup_path) + ".bak")
    if not bak_path.exists():
        print(f"[ERROR] 备份文件不存在: {bak_path}")
        return False

    try:
        shutil.copy2(bak_path, backup_path)
        print(f"[OK] 已从 {bak_path} 恢复")
    except Exception as e:
        print(f"[ERROR] 恢复失败: {e}")
        return False

    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="手动更新 LiteLLM 模型 cost map 本地备份",
    )
    parser.add_argument("--proxy", metavar="HOST:PORT", help="显式指定代理，如 127.0.0.1:10808")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="仅下载校验，不写入文件")
    group.add_argument("--restore", action="store_true", help="从 .bak 恢复原备份文件")
    args = parser.parse_args()

    if args.restore:
        return 0 if do_restore() else 1

    # 规范化 proxy 参数
    proxy_override = None
    if args.proxy:
        proxy_override = f"http://{args.proxy}" if not args.proxy.startswith("http") else args.proxy

    return 0 if do_update(dry_run=args.dry_run, proxy_override=proxy_override) else 1


if __name__ == "__main__":
    sys.exit(main())
