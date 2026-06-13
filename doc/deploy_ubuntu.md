# MultiModel Ubuntu 平台部署指南

> 面向 Agent 的从零到一部署文档，覆盖环境搭建、服务启动、验证和排障。
> 最后更新：2026-06

---

## 一、项目概述

MultiModel 是一个多模型统一接入与评测追踪平台，包含 4 个子模块：

| 模块 | 目录 | 功能 |
|------|------|------|
| model-platform | `model-platform/` | LiteLLM Proxy 多模型统一接入网关（端口 4800） |
| model-tracing | `model-tracing/` | 多模型调用追踪（支持 Langfuse / Console） |
| model-eval | `model-eval/` | 多语言代码生成评测框架（集成 Langfuse） |
| model-task | `model-task/` | 多模型路由任务（SmartRoute / Parallel / Pipeline） |

### 端口规划

| 服务 | 端口 | 说明 |
|------|------|------|
| LiteLLM Proxy | 4800 | 多模型统一 API 入口 |
| Langfuse Web | 3000 | 追踪数据可视化界面 |
| PostgreSQL | 5432 | LiteLLM + Langfuse 数据库 |

### 已接入模型

| 模型名 | provider | API 来源 |
|--------|----------|----------|
| minimax-m2-5 | MiniMax | platform.minimaxi.com |
| minimax-m2-7 | MiniMax | platform.minimaxi.com |
| deepseek-v4-flash | DeepSeek | platform.deepseek.com |
| deepseek-v4-pro | DeepSeek | platform.deepseek.com |
| glm-5-1 | 智谱 AI | open.bigmodel.cn |

---

## 二、前置依赖安装

### 方式一：一键脚本安装（推荐）

项目提供了 `scripts/setup_ubuntu.sh` 一键安装脚本，自动完成所有依赖安装：

```bash
cd MultiModel
chmod +x scripts/setup_ubuntu.sh
./scripts/setup_ubuntu.sh
```

脚本会自动安装：
- 系统基础包（python3、pip、venv、curl、git）
- Node.js 18 LTS + Prisma CLI
- Docker + Docker Compose
- Python 虚拟环境 + 项目依赖

脚本执行完成后，跳到 **第五章** 继续。

### 方式二：手动逐步安装

以下为手动安装的完整步骤。

#### 2.1 系统基础包

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv curl wget git ca-certificates gnupg
```

验证：

```bash
python3 --version
# 期望输出：Python 3.10+
```

#### 2.2 Node.js 18 LTS

```bash
# 添加 NodeSource 源
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

验证：

```bash
node --version
# 期望输出：v18.x.x
npm --version
```

#### 2.3 Prisma CLI

LiteLLM Proxy 依赖 Prisma CLI 管理数据库 schema：

```bash
sudo npm install -g prisma
```

验证：

```bash
prisma --version
```

#### 2.4 Docker + Docker Compose

```bash
sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker "$USER"
```

> **重要**：添加 docker 组后需要重新登录才能生效。或者临时使用 `newgrp docker`。

启动 Docker 服务：

```bash
sudo systemctl start docker
sudo systemctl enable docker
```

验证：

```bash
docker --version
docker compose version
```

---

## 三、克隆代码

```bash
git clone <REPO_URL> MultiModel
cd MultiModel
```

> 将 `<REPO_URL>` 替换为实际的 GitHub 仓库地址。

---

## 四、Python 虚拟环境与依赖

### 4.1 创建虚拟环境

```bash
python3 -m venv ~/multimodel-env
```

> 虚拟环境路径固定为 `~/multimodel-env`，`start_proxy.py` 中硬编码引用此路径。如需修改，需同步修改 `start_proxy.py` 中的 `VENV_LITELLM_EXE` 常量。

### 4.2 激活并安装依赖

```bash
source ~/multimodel-env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4.3 验证关键依赖

```bash
python -c "import litellm; print(f'litellm: {litellm.__version__}')"
# 确认版本 >= 1.84.0（glm-5-1 模型需要）

python -c "import openai; print(f'openai: {openai.__version__}')"

python -c "import langfuse; print('langfuse: OK')"
# 确认版本 >= 2.0.0 且 < 5.0.0
```

### 4.4 Ubuntu 与 Windows 的区别

Ubuntu 上不存在 Windows 的 `import litellm` 挂起问题。Linux 下可以直接使用 venv 中的 `litellm` 可执行文件启动，也可以用 `python -m litellm` 启动。`start_proxy.py` 已内置跨平台逻辑，自动选择正确的启动方式。

---

## 五、配置 .env 文件

### 5.1 创建 .env

项目根目录下创建 `.env` 文件（已包含在 `.gitignore` 中，不会提交到仓库）：

```bash
nano .env
# 或
vim .env
```

### 5.2 配置内容模板

```ini
# ============================================================
# MultiModel 项目统一环境变量配置
# ============================================================

# —— 模型 API Keys ——
# MiniMax Token Plan（获取地址: https://platform.minimaxi.com）
MINIMAX_API_KEY=sk-cp-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# DeepSeek（获取地址: https://platform.deepseek.com）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 智谱 AI（获取地址: https://open.bigmodel.cn）
ZAI_API_KEY=xxxxxxxx.xxxxxxxxxxxxxxxx

# —— LiteLLM Proxy ——
LITELLM_MASTER_KEY=sk-my-master-key-1234
LITELLM_BASE_URL=http://localhost:4800
# 跳过远程 GitHub cost map 获取，使用本地备份文件
LITELLM_LOCAL_MODEL_COST_MAP=True

# LiteLLM PostgreSQL（根据实际端口调整）
DATABASE_URL=postgresql://langfuse:langfuse@localhost:5432/litellm

# —— 追踪后端：console（默认） | langfuse | noop ——
TRACER_BACKEND=langfuse

# —— Langfuse（TRACER_BACKEND=langfuse 时填写）——
# 启动 Langfuse 后在 http://localhost:3000 Settings -> API Keys 获取
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxx
LANGFUSE_HOST=http://localhost:3000
```

### 5.3 必填项说明

| 环境变量 | 是否必填 | 获取方式 |
|----------|----------|----------|
| `MINIMAX_API_KEY` | 使用 MiniMax 模型时必填 | https://platform.minimaxi.com |
| `DEEPSEEK_API_KEY` | 使用 DeepSeek 模型时必填 | https://platform.deepseek.com |
| `ZAI_API_KEY` | 使用 GLM 模型时必填 | https://open.bigmodel.cn |
| `LITELLM_MASTER_KEY` | 必填 | 自定义，用于 Proxy 认证 |
| `DATABASE_URL` | 必填 | PostgreSQL 连接串 |
| `LANGFUSE_PUBLIC_KEY` | 启用追踪时必填 | Langfuse Web 界面获取 |
| `LANGFUSE_SECRET_KEY` | 启用追踪时必填 | Langfuse Web 界面获取 |

---

## 六、PostgreSQL 数据库初始化

Ubuntu 上有两种方式部署 PostgreSQL。

### 方式一：Docker 独立 PostgreSQL 容器（推荐）

项目提供了启动脚本 `model-platform/start_litellm_db.sh`：

```bash
bash model-platform/start_litellm_db.sh
```

此脚本会自动：
- 清理旧容器（如存在）
- 启动新的 PostgreSQL 15 Alpine 容器（端口 5433）
- 等待数据库就绪
- 输出连接串

默认连接串为：

```
DATABASE_URL=postgresql://litellm:litellm123@localhost:5433/litellm
```

> **注意**：此容器使用 Docker volume `litellm_pg_data` 持久化数据，重启不丢失。

将输出的 `DATABASE_URL` 填入 `.env` 文件。

### 方式二：复用 Langfuse 的 PostgreSQL 容器

如果已经启动了 Langfuse（见第七章），可以复用其 PostgreSQL 容器（`langfuse-db`）。

**步骤 1：确保 Langfuse 已启动（见第七章）。**

**步骤 2：运行自动化脚本创建 litellm 数据库：**

```bash
source ~/multimodel-env/bin/activate
python model-platform/setup_litellm_db.py
```

此脚本会自动：
- 查找运行中的 postgres 容器
- 在容器中创建 `litellm` 数据库
- 检测端口映射，输出 `DATABASE_URL`

**步骤 3：根据脚本输出更新 .env 中的 DATABASE_URL。**

如果 langfuse-db 的 5432 端口映射到主机，输出为：

```
DATABASE_URL=postgresql://langfuse:langfuse@localhost:5432/litellm
```

如果端口未映射，脚本会使用容器 bridge IP。

### 方式三：给 Langfuse docker-compose 添加端口映射

项目提供了 `model-platform/setup_litellm_db.sh` 脚本，可自动为 Langfuse 的 PostgreSQL 容器添加端口映射并创建数据库：

```bash
bash model-platform/setup_litellm_db.sh
```

此脚本会：
- 检查 `langfuse-db` 的端口映射
- 如果未映射 5432 端口，自动修改 compose 配置并重启
- 等待 PostgreSQL 就绪
- 创建 `litellm` 数据库
- 输出验证结果

对应 .env 配置：

```ini
DATABASE_URL=postgresql://langfuse:langfuse@localhost:5432/litellm
```

### 验证数据库连接

```bash
# 检查 PostgreSQL 端口监听
ss -tlnp | grep 5432
# 或
ss -tlnp | grep 5433

# 在容器中验证数据库存在
docker exec langfuse-db psql -U langfuse -l | grep litellm
# 或独立容器
docker exec litellm-postgres psql -U litellm -l
```

---

## 七、Langfuse 追踪服务部署

### 7.1 启动 Langfuse

```bash
cd model-tracing
docker compose -f langfuse-docker-compose.yml up -d
```

### 7.2 等待服务就绪

```bash
# 查看容器状态
docker compose -f langfuse-docker-compose.yml ps
# 期望看到 langfuse-server 和 langfuse-db 都为 healthy/Up
```

### 7.3 验证 Langfuse 可访问

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/health
# 期望返回 200
```

> **注意**：Langfuse 健康检查端点是 `/api/health`，不是 `/health`。

### 7.4 获取 Langfuse API Keys

1. 浏览器打开 http://localhost:3000
2. 首次访问需要注册账号（任意邮箱即可）
3. 进入 Settings -> API Keys
4. 复制 Public Key 和 Secret Key
5. 填入 `.env` 文件的 `LANGFUSE_PUBLIC_KEY` 和 `LANGFUSE_SECRET_KEY`

### 7.5 停止 Langfuse

```bash
cd model-tracing
docker compose -f langfuse-docker-compose.yml down
# 停止并删除数据
# docker compose -f langfuse-docker-compose.yml down -v
```

---

## 八、LiteLLM Proxy 启动

### 8.1 前置检查

```bash
# 激活虚拟环境
source ~/multimodel-env/bin/activate

# 1. 确认 PostgreSQL 运行中
ss -tlnp | grep 5432
# 或
ss -tlnp | grep 5433

# 2. 确认端口 4800 未占用
ss -tlnp | grep 4800
# 期望无输出

# 3. 确认 .env 文件存在
test -f .env && echo "OK" || echo "MISSING"

# 4. 确认 litellm 可执行文件存在
test -x ~/multimodel-env/bin/litellm && echo "OK" || echo "MISSING"

# 5. 确认 prisma 在 PATH 中
which prisma
```

### 8.2 前台启动（推荐调试用）

```bash
cd model-platform
python start_proxy.py --health-check
```

`--health-check` 模式会：
- 启动 Proxy 进程
- 自动等待服务就绪（最长 60 秒）
- 验证模型列表并打印

期望输出：

```
[INFO] litellm 路径: /home/xxx/multimodel-env/bin/litellm
[INFO] 配置文件:   /home/xxx/MultiModel/model-platform/config.yaml
[INFO] 监听端口:   4800
[INFO] Prisma CLI 已在 PATH 中
[INFO] 启动模式: 前台运行
[INFO] Proxy PID=xxxxx
[OK] Proxy 就绪，已加载 5 个模型: ['minimax-m2-5', 'minimax-m2-7', 'deepseek-v4-flash', 'deepseek-v4-pro', 'glm-5-1']
```

按 `Ctrl+C` 停止。

### 8.3 后台启动（推荐长期运行）

```bash
cd model-platform
python start_proxy.py --background
```

日志输出位置：
- 标准输出：`model-platform/proxy.out.log`
- 标准错误：`model-platform/proxy.err.log`

脚本会输出停止命令：

```
[INFO] 停止命令: kill -TERM <PID>
```

### 8.4 停止 Proxy

```bash
# 方式一：按 PID（后台模式启动时会显示 PID）
kill -TERM <PID>

# 方式二：查找并终止占用 4800 端口的进程
lsof -i :4800 -t | xargs kill -TERM

# 方式三：如果以上无效，强制终止
kill -9 <PID>
```

### 8.5 Prisma 数据库迁移（可选）

首次启动后，数据库中缺少部分表（LiteLLM_VerificationTokenView 等），不影响模型路由和调用。如需完整 DB 功能（虚拟 Key 管理、用量统计）：

```bash
export DATABASE_URL="postgresql://langfuse:langfuse@localhost:5432/litellm"
cd model-platform
~/multimodel-env/bin/litellm --config config.yaml --use_prisma_db_push --skip_server_startup
```

> 此命令执行约 30 秒，Prisma 需要生成客户端代码。

---

## 九、验证清单

按顺序执行以下验证，确认所有服务正常运行。

### 9.1 端口检查

```bash
ss -tlnp | grep 4800   # LiteLLM Proxy
ss -tlnp | grep 3000   # Langfuse
ss -tlnp | grep 5432   # PostgreSQL（或 5433）
```

三个端口都应处于 LISTEN 状态。

### 9.2 模型列表验证

```bash
source ~/multimodel-env/bin/activate
python -c "from openai import OpenAI; c = OpenAI(base_url='http://localhost:4800/v1', api_key='sk-my-master-key-1234'); print([m.id for m in c.models.list().data])"
```

期望输出：

```
['minimax-m2-5', 'minimax-m2-7', 'deepseek-v4-flash', 'deepseek-v4-pro', 'glm-5-1']
```

### 9.3 追踪演示验证

```bash
cd model-tracing
python main.py
```

此脚本会依次运行：
1. 智能路由分类（不需要 Proxy）
2. 并行评测（需要 Proxy）
3. 流水线任务（需要 Proxy）

### 9.4 评测 Dry-Run（不需要 Proxy）

```bash
cd model-eval
python run_eval.py --dry-run
```

使用参考答案测试评测器，验证评测逻辑正常。

### 9.5 完整评测（需要 Proxy + Langfuse）

```bash
cd model-eval
python run_eval.py --models deepseek-v4-flash
```

---

## 十、虚拟 Key 管理（可选）

LiteLLM Proxy 支持虚拟 Key 管理，可以为不同应用创建独立 Key，限制可用模型和预算。

```bash
source ~/multimodel-env/bin/activate
cd model-platform

# 批量生成预定义模板 Key
python create_keys.py generate

# 自定义生成
python create_keys.py generate --name my-app --models minimax-m2-5 --budget 5

# 列出所有 Key
python create_keys.py list

# 查看 Key 详情
python create_keys.py info <key_or_id>

# 吊销 Key
python create_keys.py delete <key_or_id> -y

# 更新 Key
python create_keys.py update <key_or_id> --budget 30
```

---

## 十一、完整启动流程速查

以下是从零启动所有服务的标准顺序：

```bash
# 1. 激活虚拟环境
source ~/multimodel-env/bin/activate

# 2. 启动 Langfuse
cd model-tracing
docker compose -f langfuse-docker-compose.yml up -d

# 3. 初始化数据库（仅首次）
python ../model-platform/setup_litellm_db.py
# 或独立容器方式
bash ../model-platform/start_litellm_db.sh

# 4. 启动 LiteLLM Proxy
cd ../model-platform
python start_proxy.py --background

# 5. 等待就绪后验证
ss -tlnp | grep 4800
python -c "from openai import OpenAI; c = OpenAI(base_url='http://localhost:4800/v1', api_key='sk-my-master-key-1234'); print([m.id for m in c.models.list().data])"

# 6. 运行业务（追踪 / 评测）
cd ../model-tracing && python main.py
cd ../model-eval && python run_eval.py --dry-run
```

---

## 十二、常见排障

### 12.1 Docker 权限不足

**现象**：`permission denied while trying to connect to the Docker daemon socket`

**解决**：

```bash
# 将当前用户加入 docker 组
sudo usermod -aG docker "$USER"

# 重新登录或临时生效
newgrp docker
```

### 12.2 Docker 服务未运行

**现象**：`Cannot connect to the Docker daemon`

**解决**：

```bash
sudo systemctl start docker
sudo systemctl enable docker   # 设为开机自启
```

### 12.3 Prisma CLI 找不到

**现象**：启动日志提示 `prisma` 命令不存在。

**解决**：

```bash
# 确认 prisma 已安装
npm list -g prisma

# 如果已安装但找不到，检查 PATH
which prisma

# 常见安装路径
ls ~/.npm-global/bin/prisma
ls /usr/local/bin/prisma

# 手动添加 PATH
export PATH="$HOME/.npm-global/bin:$PATH"
```

`start_proxy.py` 会自动检测 `~/.npm-global/bin`、`/usr/local/bin`、`~/.nvm/versions/node` 路径。

### 12.4 Langfuse 健康检查返回错误

**现象**：访问 `http://localhost:3000/health` 返回 404。

**原因**：Langfuse 健康检查端点不是 `/health`。

**解决**：使用正确的端点：

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/health
```

### 12.5 数据库连接失败

**现象**：启动日志出现 `connection refused` 或 `database "litellm" does not exist`。

**排查步骤**：

```bash
# 1. 确认 PostgreSQL 容器运行
docker ps | grep postgres

# 2. 确认端口映射
docker port langfuse-db
# 或
docker port litellm-postgres

# 3. 确认数据库已创建
docker exec langfuse-db psql -U langfuse -l | grep litellm
# 或独立容器
docker exec litellm-postgres psql -U litellm -l
```

### 12.6 端口 4800 已被占用

```bash
# 查找占用进程
lsof -i :4800
# 或
ss -tlnp | grep 4800

# 终止占用进程
kill -TERM <PID>

# 或指定其他端口启动
cd model-platform
python start_proxy.py --port 4801 --health-check
```

### 12.7 pip 安装 litellm 失败

**现象**：`pip install litellm[proxy]` 报错。

**排查**：

```bash
# 确认 Python 版本 >= 3.10
python3 --version

# 确认 pip 版本
pip --version

# 升级 pip 后重试
pip install --upgrade pip
pip install -r requirements.txt
```

### 12.8 数据库表缺失警告（非致命）

**现象**：启动日志出现 `LiteLLM_VerificationTokenView` 或 `LiteLLM_SpendLogs` 不存在。

**影响**：不影响模型路由和调用功能，仅影响用量统计和 Token 验证视图。

**解决**（如需完整功能）：见第八章 8.5 节 Prisma 数据库迁移。

### 12.9 Node.js 版本过低

**现象**：Prisma CLI 安装失败或运行报错。

**解决**：

```bash
# 检查 Node.js 版本（需要 >= 18）
node --version

# 如果版本过低，重新安装
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

---

## 十三、关键文件速查

| 文件路径 | 用途 |
|----------|------|
| `.env` | 统一环境变量（API Keys + DB + Langfuse） |
| `requirements.txt` | Python 依赖列表 |
| `scripts/setup_ubuntu.sh` | Ubuntu 一键环境搭建脚本 |
| `model-platform/config.yaml` | LiteLLM 模型路由配置 |
| `model-platform/start_proxy.py` | Proxy 启动脚本（跨平台） |
| `model-platform/setup_litellm_db.py` | 数据库初始化脚本（跨平台） |
| `model-platform/setup_litellm_db.sh` | Langfuse DB 端口映射+建库脚本 |
| `model-platform/start_litellm_db.sh` | 独立 PostgreSQL 容器启动脚本 |
| `model-platform/create_keys.py` | 虚拟 Key 管理工具 |
| `model-tracing/langfuse-docker-compose.yml` | Langfuse Docker Compose 配置 |
| `model-tracing/main.py` | 追踪演示入口 |
| `model-tracing/core/tracer_factory.py` | 追踪后端工厂（console/langfuse/noop） |
| `model-tracing/core/llm_client.py` | 统一 LLM 调用客户端 |
| `model-eval/run_eval.py` | 评测主入口 |
| `model-eval/langfuse_dataset.py` | Langfuse Dataset 集成 |
| `model-eval/datasets/code_gen_v1.json` | 评测数据集 |
| `model-eval/core/evaluator.py` | L1 语法 + L2 功能评测器 |
