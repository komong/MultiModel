"""
Setup LiteLLM database using local PostgreSQL 15 installation.

本脚本假设 PostgreSQL 15 已安装在本地（非 Docker/WSL），执行以下操作：
  1. 检查本地 PostgreSQL 服务是否运行
  2. 创建 litellm 数据库（如不存在）
  3. 应用 Prisma 迁移（通过 LiteLLM Proxy 启动时自动完成）
  4. 创建 8 个系统视图（解决中文 locale 问题）

Usage:
  python setup_litellm_db.py
"""
import subprocess
import sys
import os
from pathlib import Path
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env')
except ImportError:
    pass

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
MODEL_PLATFORM = Path(__file__).parent

# 本地 PostgreSQL 15 路径
PG_BIN = PROJECT_ROOT / "pg15" / "pgsql" / "bin"
PSQL = PG_BIN / "psql.exe"

# 从 DATABASE_URL 解析连接参数（默认值适用于本项目的本地 PG15）
_database_url = os.getenv("DATABASE_URL", "postgresql://litellm@localhost:5432/litellm")
_parsed = urlparse(_database_url)
PG_HOST = _parsed.hostname or "localhost"
PG_PORT = str(_parsed.port or 5432)
PG_USER = _parsed.username or "litellm"
PG_PASSWORD = _parsed.password or ""
DB_NAME = _parsed.path.lstrip("/") or "litellm"

# 系统视图 SQL 文件
VIEWS_SQL = MODEL_PLATFORM / "create_views.sql"


def run_psql(sql: str, database: str = "postgres", timeout: int = 30):
    """执行 psql 命令，返回 (success, stdout, stderr)。"""
    cmd = [
        str(PSQL),
        "-h", PG_HOST,
        "-p", PG_PORT,
        "-U", PG_USER,
        "-d", database,
        "-t",  # 只输出数据，不输出表头
        "-c", sql,
    ]
    env = os.environ.copy()
    if PG_PASSWORD:
        env["PGPASSWORD"] = PG_PASSWORD
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=timeout, env=env,
        )
        return (
            result.returncode == 0,
            result.stdout.decode("utf-8", errors="replace"),
            result.stderr.decode("utf-8", errors="replace"),
        )
    except FileNotFoundError:
        return False, "", f"psql not found at {PSQL}"
    except subprocess.TimeoutExpired:
        return False, "", "TIMEOUT"
    except Exception as e:
        return False, "", str(e)


def check_postgres():
    """检查 PostgreSQL 服务是否运行。"""
    print("=== Step 1: 检查 PostgreSQL 服务 ===")
    if not PSQL.exists():
        print(f"  [ERROR] psql 不存在: {PSQL}")
        print(f"  请确认 PostgreSQL 15 已安装在 {PROJECT_ROOT / 'pg15'}")
        sys.exit(1)
    print(f"  psql 路径: {PSQL}")

    ok, out, err = run_psql("SELECT version();")
    if not ok:
        print(f"  [ERROR] 无法连接 PostgreSQL: {err}")
        print("  请确认 PostgreSQL 服务已启动")
        sys.exit(1)
    version = out.strip().split("\n")[0] if out else "unknown"
    print(f"  PostgreSQL 版本: {version}")
    print("  连接正常")


def create_database():
    """创建 litellm 数据库（如不存在）。"""
    print(f"\n=== Step 2: 创建数据库 '{DB_NAME}' ===")
    ok, out, _ = run_psql(
        f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}';"
    )
    if "1" in out:
        print(f"  数据库 '{DB_NAME}' 已存在")
    else:
        # 创建数据库（不能用 -t 模式，CREATE DATABASE 不支持在事务中）
        cmd = [
            str(PSQL),
            "-h", PG_HOST,
            "-p", PG_PORT,
            "-U", PG_USER,
            "-d", "postgres",
            "-c", f'CREATE DATABASE "{DB_NAME}";',
        ]
        env = os.environ.copy()
        if PG_PASSWORD:
            env["PGPASSWORD"] = PG_PASSWORD
        try:
            result = subprocess.run(
                cmd, capture_output=True, timeout=30, env=env,
            )
            if result.returncode == 0:
                print(f"  数据库 '{DB_NAME}' 创建成功")
            else:
                err = result.stderr.decode("utf-8", errors="replace")
                print(f"  [ERROR] 创建数据库失败: {err}")
                sys.exit(1)
        except Exception as e:
            print(f"  [ERROR] 创建数据库异常: {e}")
            sys.exit(1)


def create_views():
    """创建 LiteLLM 系统视图。"""
    print(f"\n=== Step 3: 创建系统视图 ===")
    if not VIEWS_SQL.exists():
        print(f"  [WARN] 视图 SQL 文件不存在: {VIEWS_SQL}")
        print("  跳过视图创建（Proxy 启动时会自动尝试创建）")
        return

    # 执行 SQL 文件
    cmd = [
        str(PSQL),
        "-h", PG_HOST,
        "-p", PG_PORT,
        "-U", PG_USER,
        "-d", DB_NAME,
        "-f", str(VIEWS_SQL),
    ]
    env = os.environ.copy()
    if PG_PASSWORD:
        env["PGPASSWORD"] = PG_PASSWORD
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=60, env=env,
        )
        out = result.stdout.decode("utf-8", errors="replace")
        err = result.stderr.decode("utf-8", errors="replace")
        if result.returncode == 0:
            # 统计创建的视图数（CREATE VIEW 输出 "CREATE VIEW"）
            view_count = out.count("CREATE VIEW")
            print(f"  视图创建完成（{view_count} 个）")
        else:
            # 有些 "already exists" 错误可以忽略
            lines = [l for l in err.strip().split("\n") if l.strip()]
            real_errors = [l for l in lines if "already exists" not in l]
            if real_errors:
                print(f"  [WARN] 部分视图创建有警告:")
                for l in lines:
                    print(f"    {l}")
            else:
                print("  视图已全部存在，无需创建")
    except Exception as e:
        print(f"  [ERROR] 执行视图 SQL 异常: {e}")


def verify_database():
    """验证数据库状态。"""
    print(f"\n=== Step 4: 验证数据库状态 ===")

    # 检查表数量
    ok, out, _ = run_psql(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';",
        database=DB_NAME,
    )
    table_count = out.strip() if ok else "?"
    print(f"  表数量: {table_count}")

    # 检查视图数量
    ok, out, _ = run_psql(
        "SELECT count(*) FROM pg_views WHERE schemaname='public';",
        database=DB_NAME,
    )
    view_count = out.strip() if ok else "?"
    print(f"  视图数量: {view_count}")

    # 检查核心视图
    ok, out, _ = run_psql(
        "SELECT viewname FROM pg_views WHERE schemaname='public' "
        "AND viewname ILIKE '%verificationtoken%';",
        database=DB_NAME,
    )
    has_core_view = bool(out.strip()) if ok else False
    print(f"  VerificationTokenView: {'存在' if has_core_view else '缺失'}")


def print_connection_info():
    """打印连接信息。"""
    print(f"\n{'='*60}")
    print(f"数据库设置完成")
    print(f"{'='*60}")
    print(f"  连接信息:")
    print(f"    Host: {PG_HOST}:{PG_PORT}")
    print(f"    Database: {DB_NAME}")
    print(f"    User: {PG_USER}")
    print(f"")
    print(f"  DATABASE_URL:")
    if PG_PASSWORD:
        db_url = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{DB_NAME}"
    else:
        db_url = f"postgresql://{PG_USER}@{PG_HOST}:{PG_PORT}/{DB_NAME}"
    print(f"    {db_url}")
    print(f"")
    print(f"  下一步:")
    print(f"    1. 确保 .env 中 DATABASE_URL 已设置")
    print(f"    2. 启动 Proxy: cd model-platform; py start_proxy.py")
    print(f"    3. Proxy 会自动执行 prisma migrate deploy 应用迁移")
    print(f"{'='*60}")


def main():
    print("=" * 60)
    print("LiteLLM 数据库初始化 (本地 PostgreSQL 15)")
    print("=" * 60)

    check_postgres()
    create_database()
    create_views()
    verify_database()
    print_connection_info()


if __name__ == "__main__":
    main()
