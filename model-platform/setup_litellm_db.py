"""
Setup LiteLLM database in Docker PostgreSQL.

跨平台支持：
  - Windows: 通过 WSL 调用 Docker 命令
  - Linux: 直接调用本地 Docker 命令

Safe approach: only creates the database, does NOT modify existing containers.

Usage:
  python setup_litellm_db.py
"""
import subprocess
import sys
import os

os.environ['PYTHONIOENCODING'] = 'utf-8'

IS_WINDOWS = sys.platform == "win32"


def run_docker_cmd(cmd: str, timeout: int = 30):
    """执行 Docker 命令，Windows 通过 WSL 中转，Linux 直接执行."""
    if IS_WINDOWS:
        full_cmd = f'wsl -d Ubuntu -- bash -c "{cmd}"'
    else:
        full_cmd = cmd
    try:
        result = subprocess.run(
            full_cmd, shell=True, capture_output=True, timeout=timeout,
        )
        return (
            result.returncode == 0,
            result.stdout.decode('utf-8', errors='replace'),
            result.stderr.decode('utf-8', errors='replace'),
        )
    except subprocess.TimeoutExpired:
        return False, "", "TIMEOUT"
    except Exception as e:
        return False, "", str(e)


def main():
    # Step 1: Find postgres container
    print("=== Step 1: Find postgres container ===")
    ok, out, _ = run_docker_cmd(
        "docker ps --filter status=running --format '{{.Names}} {{.Image}}'"
    )
    lines = [l.strip() for l in out.strip().split('\n') if 'postgres' in l.lower()]
    if not lines:
        print("  No running postgres container. Start Langfuse first.")
        sys.exit(1)
    print(f"  Candidates: {lines}")

    # Pick the first postgres container
    container = lines[0].split()[0]
    print(f"  Using: {container}")

    # Step 2: Create litellm database
    print("\n=== Step 2: Create litellm database ===")
    ok, out, _ = run_docker_cmd(
        f"docker exec {container} psql -U langfuse -tAc "
        "\"SELECT 1 FROM pg_database WHERE datname='litellm'\""
    )
    if "1" in out:
        print("  Already exists")
    else:
        ok, out, err = run_docker_cmd(
            f"docker exec {container} psql -U langfuse -c 'CREATE DATABASE litellm;'"
        )
        print(f"  Created: {'OK' if ok else 'FAILED ' + err}")

    # Step 3: Determine connectivity
    print("\n=== Step 3: Determine connection ===")
    ok, out, _ = run_docker_cmd(f"docker port {container}")
    print(f"  Published ports: {out.strip() or 'none'}")

    # Test database connection inside container
    print(f"\n  Testing connection inside container...")
    ok, out, _ = run_docker_cmd(
        f"docker exec {container} psql -U langfuse -d litellm -c 'SELECT 1;'"
    )
    if ok:
        print("  Database litellm is accessible inside container")
    else:
        print(f"  Database test failed: {out}")

    # Step 4: Setup access for the host platform
    if IS_WINDOWS:
        # Windows via WSL: need port forwarding
        print("\n=== Step 4: Start port forwarding for Windows access ===")
        print("  Starting a socat forwarder container on port 5433...")

        ok, out, _ = run_docker_cmd("hostname -I | awk '{print $1}'")
        wsl_ip = out.strip()

        ok, out, _ = run_docker_cmd(
            f"docker rm -f litellm-pg-forward 2>/dev/null; "
            f"docker run -d --name litellm-pg-forward "
            f"--link {container}:postgres "
            f"-p 5433:5432 "
            f"alpine/socat TCP-LISTEN:5432,fork TCP:postgres:5432",
            timeout=30,
        )
        if ok:
            print("  Forwarder started on port 5433")
            db_url = "postgresql://langfuse:langfuse@localhost:5433/litellm"
        else:
            print(f"  Forwarder failed: {out}")
            print("  Fallback: using WSL bridge IP")
            db_url = f"postgresql://langfuse:langfuse@{wsl_ip}:5432/litellm"
    else:
        # Linux: Docker 容器通过 localhost 直接访问已映射端口
        print("\n=== Step 4: Linux direct access ===")
        # 检查是否有端口映射到 host
        ok, out, _ = run_docker_cmd(f"docker port {container}")
        host_port = None
        for line in out.strip().split('\n'):
            if '5432' in line and '->' in line:
                # 格式如 "5432/tcp -> 0.0.0.0:5432"
                host_port = line.split('->')[-1].strip().split(':')[-1]
                break

        if host_port:
            db_url = f"postgresql://langfuse:langfuse@localhost:{host_port}/litellm"
            print(f"  Container port mapped to host:{host_port}")
        else:
            # 使用 Docker 网络 bridge IP
            ok, out, _ = run_docker_cmd(
                f"docker inspect {container} --format '{{{{.NetworkSettings.IPAddress}}}}'"
            )
            container_ip = out.strip()
            db_url = f"postgresql://langfuse:langfuse@{container_ip}:5432/litellm"
            print(f"  Using container bridge IP: {container_ip}")

    print(f"\n=== DONE ===")
    print(f"  DATABASE_URL={db_url}")


if __name__ == "__main__":
    main()
