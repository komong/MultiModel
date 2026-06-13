"""
启动 LiteLLM Proxy（多模型统一接入网关）。

支持三种模式：
  python start_proxy.py                     # 前台运行，Ctrl+C 停止
  python start_proxy.py --background        # 后台运行（独立进程组，终端关闭不中止）
  python start_proxy.py --health-check      # 前台运行 + 自动等待就绪并验证模型列表

跨平台支持：Windows + Linux（Ubuntu 等）

Windows 说明：
  使用 litellm.exe 而非 python -m litellm，因为 venv 环境下 import litellm
  会因 tiktoken 编码下载阻塞而挂起，litellm.exe 不触发此问题。

Linux 说明：
  直接使用 venv 中的 litellm 可执行文件，无上述问题。
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# 跨平台检测
IS_WINDOWS = sys.platform == "win32"

# litellm 可执行文件路径（按平台区分）
if IS_WINDOWS:
    VENV_LITELLM_EXE = r"C:\litellm-env\Scripts\litellm.exe"
    LITELLM_BIN_NAME = "litellm.exe"
else:
    VENV_LITELLM_EXE = os.path.expanduser("~/multimodel-env/bin/litellm")
    LITELLM_BIN_NAME = "litellm"

# 默认端口
DEFAULT_PORT = 4800

# 健康检查最长等待时间（秒）
HEALTH_CHECK_TIMEOUT = 60


def main():
    parser = argparse.ArgumentParser(
        description="启动 LiteLLM Proxy（多模型统一接入网关）",
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help=f"监听端口（默认 {DEFAULT_PORT}）",
    )
    parser.add_argument(
        "--background", action="store_true",
        help="后台运行（独立进程组，输出写入 proxy.out.log / proxy.err.log）",
    )
    parser.add_argument(
        "--health-check", action="store_true",
        help="启动后自动等待服务就绪并打印模型列表",
    )
    args = parser.parse_args()

    # 加载项目根 .env（含 API Keys、DATABASE_URL、LITELLM_MASTER_KEY）
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)

    # UTF-8 模式（Prisma 兼容性需要）
    os.environ['PYTHONUTF8'] = '1'

    # 确保系统中已安装的 Prisma CLI（npm install -g prisma）可被 LiteLLM 发现
    _ensure_prisma_cli()

    # 代理绕过：确保 localhost 和 GitHub 不走系统代理（否则 litellm 启动会挂起）
    _apply_no_proxy()

    port = str(args.port)
    config_path = str(Path(__file__).parent / 'config.yaml')

    # 查找 litellm 可执行文件
    litellm_exe = _find_litellm_exe()
    if litellm_exe is None:
        platform_label = "Windows" if IS_WINDOWS else "Linux"
        print(f"[ERROR] 找不到 litellm 可执行文件（当前平台: {platform_label}）")
        print(f"  尝试路径: {VENV_LITELLM_EXE}")
        print(f"  也尝试了当前 Python 环境中的: {Path(sys.executable).parent / LITELLM_BIN_NAME}")
        print("  请确认已安装: pip install litellm[proxy]>=1.84.0")
        sys.exit(1)

    print(f"[INFO] litellm 路径: {litellm_exe}")
    print(f"[INFO] 配置文件:   {config_path}")
    print(f"[INFO] 监听端口:   {port}")

    if args.background:
        _start_background(litellm_exe, config_path, port)
    else:
        _start_foreground(litellm_exe, config_path, port, args.health_check)


def _find_litellm_exe():
    """定位 litellm 可执行文件（跨平台）."""
    # 1. 尝试预设的 venv 路径
    candidate = Path(VENV_LITELLM_EXE)
    if candidate.exists():
        return str(candidate)

    # 2. 在当前 Python 环境同级目录查找
    sibling = Path(sys.executable).parent / LITELLM_BIN_NAME
    if sibling.exists():
        return str(sibling)

    # 3. Linux 额外回退：通过 which 查找系统 PATH 中的 litellm
    if not IS_WINDOWS:
        import shutil
        found = shutil.which("litellm")
        if found:
            return found

    return None


def _ensure_prisma_cli():
    """确保 Prisma CLI 在 PATH 中可被 LiteLLM 发现。

    LiteLLM Proxy 启动时通过 subprocess.run(['prisma']) 检测 prisma CLI 是否可用。
    - Windows: npm 全局安装在 AppData，需手动加入 PATH；subprocess 找不到 .cmd，需修补源码。
    - Linux: prisma 通常在 /usr/local/bin 或 ~/.npm-global/bin，subprocess 可直接找到。
    """
    import shutil

    if IS_WINDOWS:
        # Windows: 常见的 npm 全局安装路径
        npm_global_candidates = [
            Path('D:/npm-global'),
            Path.home() / 'AppData' / 'Roaming' / 'npm',
        ]
        for candidate in npm_global_candidates:
            prisma_cmd = candidate / 'prisma.cmd'
            if prisma_cmd.exists():
                existing = os.environ.get('PATH', '')
                os.environ['PATH'] = f"{candidate};{existing}"
                print(f"[INFO] 已将 Prisma CLI 加入 PATH: {candidate}")
                break
        # Windows 兼容性修补
        _patch_litellm_prisma_check()
        _patch_proxy_extras_prisma()
    else:
        # Linux: 检查 prisma 是否已在 PATH 中
        if shutil.which('prisma'):
            print("[INFO] Prisma CLI 已在 PATH 中")
        else:
            # 尝试常见路径
            linux_candidates = [
                Path.home() / '.npm-global' / 'bin',
                Path('/usr/local/bin'),
                Path.home() / '.nvm' / 'versions' / 'node',
            ]
            for candidate in linux_candidates:
                prisma_bin = candidate / 'prisma'
                if prisma_bin.exists():
                    existing = os.environ.get('PATH', '')
                    os.environ['PATH'] = f"{candidate}:{existing}"
                    print(f"[INFO] 已将 Prisma CLI 加入 PATH: {candidate}")
                    break


def _patch_litellm_prisma_check():
    """修补 LiteLLM 源码中的 prisma CLI 检测和执行，使其兼容 Windows。

    LiteLLM 使用 subprocess.run(['prisma']) 检测和执行 prisma CLI。
    在 Windows 上，subprocess.run 默认只查找 .exe 文件，不查找 .cmd。
    修补两个位置：
      1. litellm/proxy/proxy_cli.py —— prisma 检测（加 shell=True）
      2. litellm_proxy_extras/utils.py —— _get_prisma_command() 返回 prisma.cmd
    """
    try:
        # 定位 litellm 包目录（避免 import litellm，其在 venv 中会因 tiktoken 编码下载而挂起）
        litellm_dir = Path(__file__).parent.parent / 'litellm'
        if not (litellm_dir / 'proxy' / 'proxy_cli.py').exists():
            venv_site = Path(VENV_LITELLM_EXE).parent.parent / 'Lib' / 'site-packages'
            litellm_dir = venv_site / 'litellm'

        # 修补 1: proxy_cli.py 中的 prisma 检测
        cli_path = litellm_dir / 'proxy' / 'proxy_cli.py'
        if cli_path.exists():
            content = cli_path.read_text(encoding='utf-8')
            target = 'subprocess.run(["prisma"], capture_output=True, shell=True)'
            if target not in content:
                original = 'subprocess.run(["prisma"], capture_output=True)'
                if original in content:
                    content = content.replace(original, target)
                    cli_path.write_text(content, encoding='utf-8')
                    print(f"[INFO] 已修补 proxy_cli.py prisma 检测 (shell=True)")

        # 修补 2: litellm_proxy_extras/utils.py —— 让 _get_prisma_command() 返回 prisma.cmd
        extras_utils = Path(VENV_LITELLM_EXE).parent.parent / 'Lib' / 'site-packages' / 'litellm_proxy_extras' / 'utils.py'
        if extras_utils.exists():
            content = extras_utils.read_text(encoding='utf-8')
            # 在 return "prisma" 前插入 Windows 判断
            marker = '    # Fall back to the Python wrapper (will work in online mode)\n    return "prisma"'
            patched_marker = (
                '    # Fall back to the Python wrapper (will work in online mode)\n'
                '    # Windows: use prisma.cmd (npm installs .cmd, not .exe)\n'
                '    import sys as _sys\n'
                '    return "prisma.cmd" if _sys.platform == "win32" else "prisma"'
            )
            if patched_marker not in content:
                if marker in content:
                    content = content.replace(marker, patched_marker)
                    extras_utils.write_text(content, encoding='utf-8')
                    print(f"[INFO] 已修补 litellm_proxy_extras/utils.py _get_prisma_command (prisma.cmd)")

    except Exception as e:
        print(f"[WARN] 无法修补 LiteLLM prisma: {e}")


def _patch_proxy_extras_prisma():
    """修补 litellm_proxy_extras/utils.py 中的 prisma CLI 调用，使其兼容 Windows。

    LiteLLM v1.87+ 将 prisma CLI 调用从 proxy_cli.py 迁移到
    litellm_proxy_extras/utils.py。新代码使用 subprocess.run([_get_prisma_command(), ...])
    调用 prisma CLI，但 Windows 上 prisma 安装为 prisma.cmd，
    CreateProcess 无法直接执行 .cmd 文件。

    此函数在 utils.py 的 import 区域后注入一个 subprocess.run 包装器：
    - 仅对 prisma 相关命令添加 shell=True（通过 cmd.exe 解析 .cmd 文件）
    - 对含 cmd.exe 特殊字符（如 URL 中的 & ）的参数自动加双引号，
      避免 cmd.exe 将 & 解释为命令分隔符
    """
    try:
        venv_site = Path(VENV_LITELLM_EXE).parent.parent / 'Lib' / 'site-packages'
        utils_path = venv_site / 'litellm_proxy_extras' / 'utils.py'
        if not utils_path.exists():
            print(f"[WARN] 找不到 litellm_proxy_extras/utils.py: {utils_path}")
            return
    except Exception as e:
        print(f"[WARN] 无法定位 litellm_proxy_extras/utils.py: {e}")
        return

    content = utils_path.read_text(encoding='utf-8')
    marker_v2 = '# --- Windows prisma.cmd compatibility patch v2 ---'
    end_marker = '# --- End patch ---'

    # 已有 v2 补丁则跳过
    if marker_v2 in content:
        return

    # 移除旧版补丁（v1 或无版本号），清除从旧 marker 到 end_marker 的所有行
    old_marker_prefix = '# --- Windows prisma.cmd compatibility patch'
    if old_marker_prefix in content:
        lines = content.split('\n')
        new_lines = []
        skipping = False
        for line in lines:
            if line.startswith(old_marker_prefix):
                skipping = True
                continue
            if skipping and line.strip() == end_marker:
                skipping = False
                continue
            if skipping:
                continue
            new_lines.append(line)
        content = '\n'.join(new_lines)

    # 找到最后一个顶层 import 语句
    lines = content.split('\n')
    last_import_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            last_import_idx = i

    patch_code = (
        '\n'
        + marker_v2 + '\n'
        'import sys as _patch_sys\n'
        'if _patch_sys.platform == "win32":\n'
        '    _patch_orig_run = subprocess.run\n'
        '    def _patch_prisma_run(*args, **kwargs):\n'
        '        _cmd = args[0] if args else kwargs.get("args")\n'
        '        if isinstance(_cmd, list) and _cmd and _cmd[0] in ("prisma", "prisma.cmd"):\n'
        '            _special = set(" &|<>()^")\n'
        '            _parts = []\n'
        '            for _arg in _cmd:\n'
        '                if any(_c in _arg for _c in _special):\n'
        '                    _parts.append(chr(34) + _arg + chr(34))\n'
        '                else:\n'
        '                    _parts.append(_arg)\n'
        '            if args:\n'
        '                args = (" ".join(_parts),) + args[1:]\n'
        '            else:\n'
        '                kwargs["args"] = " ".join(_parts)\n'
        '            kwargs["shell"] = True\n'
        '        return _patch_orig_run(*args, **kwargs)\n'
        '    subprocess.run = _patch_prisma_run\n'
        + end_marker + '\n'
    )

    lines.insert(last_import_idx + 1, patch_code)
    content = '\n'.join(lines)

    utils_path.write_text(content, encoding='utf-8')
    print(f"[INFO] 已修补 litellm_proxy_extras prisma CLI (Windows shell=True + arg quoting): {utils_path}")


def _apply_no_proxy():
    """确保 localhost 和 GitHub 不走系统代理。

    如果系统配置了 HTTP_PROXY/HTTPS_PROXY 代理，litellm.exe 启动时
    会尝试通过代理访问 GitHub (raw.githubusercontent.com) 获取 cost map，
    代理不通会导致整个进程挂起。设置 NO_PROXY 绕过。
    """
    no_proxy_additions = "localhost,127.0.0.1,github.com,raw.githubusercontent.com"
    for var in ('NO_PROXY', 'no_proxy'):
        existing = os.environ.get(var, '')
        if no_proxy_additions not in existing:
            os.environ[var] = f"{existing},{no_proxy_additions}" if existing else no_proxy_additions


def _start_foreground(litellm_exe, config_path, port, do_health_check):
    """前台运行，直接挂载到当前终端."""
    print("[INFO] 启动模式: 前台运行")

    cmd = [litellm_exe, "--config", config_path, "--port", port]

    p = subprocess.Popen(cmd)
    print(f"[INFO] Proxy PID={p.pid}")

    if do_health_check:
        _wait_and_verify(port)

    # 前台等待子进程结束（Ctrl+C 时一起退出）
    try:
        p.wait()
    except KeyboardInterrupt:
        print("\n[INFO] 收到中断信号，正在停止...")
        p.terminate()
        p.wait()
        print("[INFO] Proxy 已停止")


def _start_background(litellm_exe, config_path, port):
    """后台运行，使用独立进程组，输出重定向到日志文件."""
    print("[INFO] 启动模式: 后台运行")

    log_dir = Path(__file__).parent
    out_path = log_dir / 'proxy.out.log'
    err_path = log_dir / 'proxy.err.log'

    cmd = [litellm_exe, "--config", config_path, "--port", port]

    with open(out_path, 'w') as out_f, open(err_path, 'w') as err_f:
        if IS_WINDOWS:
            p = subprocess.Popen(
                cmd,
                stdout=out_f,
                stderr=err_f,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            stop_cmd = f"taskkill /PID {p.pid} /F"
        else:
            # Linux: 使用 os.setsid 创建新进程组
            p = subprocess.Popen(
                cmd,
                stdout=out_f,
                stderr=err_f,
                preexec_fn=os.setsid,
            )
            stop_cmd = f"kill -TERM {p.pid}"

    print(f"[INFO] Proxy PID={p.pid}（后台运行）")
    print(f"[INFO] stdout -> {out_path}")
    print(f"[INFO] stderr -> {err_path}")
    print(f"[INFO] 停止命令: {stop_cmd}")


def _wait_and_verify(port):
    """等待 Proxy 就绪，然后打印模型列表."""
    import requests

    # 临时清除代理环境变量，确保 localhost 请求不走系统代理
    saved_proxy_vars = {}
    for var in ('HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy'):
        if var in os.environ:
            saved_proxy_vars[var] = os.environ.pop(var)

    base_url = f"http://localhost:{port}"

    print(f"[INFO] 等待 Proxy 就绪（最长 {HEALTH_CHECK_TIMEOUT}s）...")
    ready = False
    for i in range(HEALTH_CHECK_TIMEOUT):
        try:
            resp = requests.get(f"{base_url}/health", timeout=2)
            if resp.status_code in (200, 401):
                # 401 也说明服务在运行（只是需要认证）
                ready = True
                break
        except Exception:
            pass
        time.sleep(1)

    # 恢复代理环境变量
    os.environ.update(saved_proxy_vars)

    if not ready:
        print("[WARN] Proxy 未在预期时间内就绪，请检查 proxy.out.log")
        return

    elapsed = time.time()

    # 验证模型列表
    master_key = os.environ.get("LITELLM_MASTER_KEY", "sk-my-master-key-1234")
    try:
        from openai import OpenAI
        client = OpenAI(base_url=f"{base_url}/v1", api_key=master_key)
        models = client.models.list().data
        names = [m.id for m in models]
        print(f"[OK] Proxy 就绪，已加载 {len(names)} 个模型: {names}")
    except Exception as e:
        print(f"[OK] Proxy 就绪（模型列表获取失败: {e}）")


if __name__ == "__main__":
    raise SystemExit(main())
