#!/usr/bin/env bash
# =============================================================
# MultiModel 项目 Ubuntu 开发环境一键搭建脚本
# 用途：在全新 Ubuntu 系统上快速配置开发环境
# 使用：chmod +x setup_ubuntu.sh && ./setup_ubuntu.sh
# =============================================================

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# 项目根目录（脚本所在目录的上级）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$HOME/multimodel-env"

info "项目根目录: $PROJECT_ROOT"
info "虚拟环境路径: $VENV_DIR"

# ---- 1. 系统基础包 ----
info "=== Step 1: 安装系统基础包 ==="
sudo apt update
sudo apt install -y \
    python3 python3-pip python3-venv \
    curl wget git \
    ca-certificates gnupg

python3 --version

# ---- 2. Node.js + Prisma CLI ----
info "=== Step 2: 安装 Node.js + Prisma CLI ==="
if command -v node &>/dev/null; then
    info "Node.js 已安装: $(node --version)"
else
    # 使用 NodeSource 安装 Node.js 18 LTS
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt install -y nodejs
    info "Node.js 安装完成: $(node --version)"
fi

if command -v prisma &>/dev/null; then
    info "Prisma CLI 已安装: $(prisma --version 2>&1 | head -1)"
else
    sudo npm install -g prisma
    info "Prisma CLI 安装完成"
fi

# ---- 3. Docker + Docker Compose ----
info "=== Step 3: 安装 Docker ==="
if command -v docker &>/dev/null; then
    info "Docker 已安装: $(docker --version)"
else
    sudo apt install -y docker.io docker-compose-plugin
    sudo usermod -aG docker "$USER"
    info "Docker 安装完成（需重新登录以生效 docker 组权限）"
fi

# 确保 Docker 服务运行
if ! sudo systemctl is-active --quiet docker; then
    sudo systemctl start docker
    sudo systemctl enable docker
    info "Docker 服务已启动并设为开机自启"
fi

# ---- 4. Python 虚拟环境 + 依赖 ----
info "=== Step 4: 创建 Python 虚拟环境 ==="
if [ -d "$VENV_DIR" ]; then
    warn "虚拟环境已存在: $VENV_DIR（跳过创建）"
else
    python3 -m venv "$VENV_DIR"
    info "虚拟环境创建完成: $VENV_DIR"
fi

# 激活虚拟环境
source "$VENV_DIR/bin/activate"

info "安装 Python 依赖..."
pip install --upgrade pip
pip install -r "$PROJECT_ROOT/requirements.txt"
info "Python 依赖安装完成"

# 验证关键包
python -c "import litellm; print(f'  litellm: {litellm.__version__}')"
python -c "import openai; print(f'  openai: {openai.__version__}')"
python -c "import langfuse; print(f'  langfuse: OK')"

# ---- 5. 配置 .env ----
info "=== Step 5: 配置环境变量 ==="
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/model-tracing/.env.example"

if [ -f "$ENV_FILE" ]; then
    warn ".env 已存在，跳过（如需重新配置请手动编辑）"
else
    if [ -f "$ENV_EXAMPLE" ]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        warn "已从 .env.example 复制，请编辑 .env 填入 API Key"
    else
        warn "未找到 .env.example，请手动创建 .env"
    fi
    echo "  编辑命令: nano $ENV_FILE"
fi

# ---- 6. 验证环境 ----
info "=== Step 6: 环境验证 ==="

# 检查 litellm 可执行文件
LITELLM_BIN="$VENV_DIR/bin/litellm"
if [ -x "$LITELLM_BIN" ]; then
    info "litellm 可执行文件: $LITELLM_BIN"
else
    warn "litellm 可执行文件未找到，尝试: python -m litellm"
fi

# 检查 prisma
if command -v prisma &>/dev/null; then
    info "prisma CLI: $(which prisma)"
else
    warn "prisma CLI 未在 PATH 中"
fi

# 检查 docker
if docker info &>/dev/null; then
    info "Docker: 正常运行"
else
    warn "Docker 未运行或当前用户无权限（可能需要重新登录）"
fi

echo ""
info "====================================="
info "  Ubuntu 环境搭建完成！"
info "====================================="
echo ""
info "后续步骤："
echo "  1. 编辑 .env 填入 API Key："
echo "     nano $ENV_FILE"
echo ""
echo "  2. 启动 Langfuse（Docker）："
echo "     cd $PROJECT_ROOT/model-tracing"
echo "     docker compose -f langfuse-docker-compose.yml up -d"
echo ""
echo "  3. 启动 LiteLLM Proxy："
echo "     source $VENV_DIR/bin/activate"
echo "     cd $PROJECT_ROOT/model-platform"
echo "     python start_proxy.py --health-check"
echo ""
echo "  4. 运行追踪演示："
echo "     cd $PROJECT_ROOT/model-tracing"
echo "     python main.py"
echo ""
echo "  5. 运行评测（dry-run）："
echo "     cd $PROJECT_ROOT/model-eval"
echo "     python run_eval.py --dry-run"
