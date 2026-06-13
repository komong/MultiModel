# MultiModel Windows 平台部署指南

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
| PostgreSQL | 5432 / 5433 | LiteLLM + Langfuse 数据库 |

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

### 2.1 Git

从 https://git-scm.com/download/win 下载安装，安装时勾选 "Add to PATH"。

验证：

```powershell
git --version
```

### 2.2 Python 3.10+

从 https://www.python.org/downloads/ 下载安装。安装时 **必须勾选**：
- "Add Python to PATH"
- "pip"

推荐使用 Windows py 启动器（安装后自带）：

```powershell
py --version
# 期望输出：Python 3.10+ 
```

### 2.3 Node.js 18 LTS

从 https://nodejs.org/ 下载安装 LTS 版本。

验证：

```powershell
node --version
# 期望输出：v18.x.x
npm --version
```

### 2.4 Prisma CLI

LiteLLM Proxy 依赖 Prisma CLI 管理数据库 schema：

```powershell
npm install -g prisma
```

验证：

```powershell
prisma --version
```

> **注意**：Prisma 安装路径通常为 `%APPDATA%\npm\prisma.cmd`。`start_proxy.py` 已内置自动检测此路径并加入 PATH。

### 2.5 WSL2 + Docker

Langfuse 通过 Docker 容器运行，Windows 上需要 WSL2 + Docker。

**安装 WSL2：**

```powershell
wsl --install -d Ubuntu
```

安装完成后重启计算机，设置 Ubuntu 用户名和密码。

**安装 Docker Desktop：**

从 https://www.docker.com/products/docker-desktop/ 下载安装。安装时确保：
- 勾选 "Use WSL 2 based engine"
- 在 Settings -> Resources -> WSL Integration 中启用 Ubuntu

验证 Docker：

```powershell
wsl -d Ubuntu -- bash -c "docker --version"
```

---

## 三、克隆代码

```powershell
git clone <REPO_URL> MultiModel
cd MultiModel
```

> 将 `<REPO_URL>` 替换为实际的 GitHub 仓库地址。

---

## 四、Python 虚拟环境与依赖

### 4.1 创建虚拟环境

```powershell
py -m venv C:\litellm-env
```

> 虚拟环境路径固定为 `C:\litellm-env`，`start_proxy.py` 中硬编码引用此路径。如需修改，需同步修改 `start_proxy.py` 中的 `VENV_LITELLM_EXE` 常量。

### 4.2 激活并安装依赖

```powershell
C:\litellm-env\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4.3 验证关键依赖

```powershell
pip show litellm
# 确认版本 >= 1.84.0（glm-5-1 模型需要）

pip show langfuse
# 确认版本 >= 2.0.0 且 < 5.0.0
```

### 4.4 Windows 特殊说明：litellm.exe

**重要**：Windows 下 `import litellm` 会因 tiktoken 编码下载而永久挂起。因此：
- 不能使用 `python -m litellm.proxy.proxy_server` 启动
- 必须使用 `C:\litellm-env\Scripts\litellm.exe` CLI 启动
- `start_proxy.py` 已内置此逻辑，自动查找 `litellm.exe`

---

## 五、配置 .env 文件

### 5.1 创建 .env

项目根目录下创建 `.env` 文件（已包含在 `.gitignore` 中，不会提交到仓库）：

```powershell
notepad .env
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
DATABASE_URL=postgresql://litellm@localhost:5432/litellm

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

Windows 上有两种方式部署 PostgreSQL。

### 方式一：WSL Docker 中复用 Langfuse 的 PostgreSQL（推荐）

Langfuse 自带一个 PostgreSQL 容器（`langfuse-db`），可以复用它来创建 `litellm` 数据库。

**步骤 1：先启动 Langfuse（见第七章），确保 langfuse-db 容器运行。**

**步骤 2：运行自动化脚本创建 litellm 数据库：**

```powershell
C:\litellm-env\Scripts\python.exe model-platform\setup_litellm_db.py
```

此脚本会自动：
- 通过 WSL 查找运行中的 postgres 容器
- 在容器中创建 `litellm` 数据库
- Windows 下启动 socat 端口转发容器（端口 5433）
- 输出最终的 `DATABASE_URL`

**步骤 3：根据脚本输出更新 .env 中的 DATABASE_URL。**

如果脚本输出的连接串为 `postgresql://langfuse:langfuse@localhost:5433/litellm`，则更新：

```ini
DATABASE_URL=postgresql://langfuse:langfuse@localhost:5433/litellm
```

### 方式二：独立 PostgreSQL 容器

通过 WSL 启动一个独立的 PostgreSQL 容器：

```powershell
wsl -d Ubuntu -- bash -c "cd /tmp && cat > start_pg.sh << 'EOF'
docker rm -f litellm-postgres 2>/dev/null
docker run -d \
  --name litellm-postgres \
  -e POSTGRES_USER=litellm \
  -e POSTGRES_PASSWORD=litellm123 \
  -e POSTGRES_DB=litellm \
  -p 5433:5432 \
  -v litellm_pg_data:/var/lib/postgresql/data \
  postgres:15-alpine
EOF
chmod +x /tmp/start_pg.sh && bash /tmp/start_pg.sh"
```

对应 .env 配置：

```ini
DATABASE_URL=postgresql://litellm:litellm123@localhost:5433/litellm
```

### 验证数据库连接

```powershell
netstat -ano | findstr ":5432"
# 或
netstat -ano | findstr ":5433"
# 期望看到 LISTENING 状态
```

---

## 七、Langfuse 追踪服务部署

### 7.1 复制 docker-compose 到 WSL

```powershell
copy /Y "model-tracing\langfuse-docker-compose.yml" "\\wsl.localhost\Ubuntu\tmp\langfuse-docker-compose.yml"
```

### 7.2 在 WSL 中启动 Langfuse

```powershell
wsl -d Ubuntu -- bash -c "cd /tmp && docker compose -f langfuse-docker-compose.yml up -d"
```

### 7.3 等待服务就绪

```powershell
# 等待约 15-30 秒，检查容器状态
wsl -d Ubuntu -- bash -c "docker ps --format 'table {{.Names}}\t{{.Status}}'"
# 期望看到 langfuse-server 和 langfuse-db 都为 Up
```

### 7.4 验证 Langfuse 可访问

```powershell
curl.exe --noproxy '*' -sI http://localhost:3000/api/health
# 期望返回 200 OK
```

> **注意**：Langfuse 健康检查端点是 `/api/health`，不是 `/health`。

### 7.5 获取 Langfuse API Keys

1. 浏览器打开 http://localhost:3000
2. 首次访问需要注册账号（任意邮箱即可）
3. 进入 Settings -> API Keys
4. 复制 Public Key 和 Secret Key
5. 填入 `.env` 文件的 `LANGFUSE_PUBLIC_KEY` 和 `LANGFUSE_SECRET_KEY`

### 7.6 Windows 端口转发（如果 localhost:3000 无法访问）

WSL2 的 Docker 容器端口通常自动映射到 Windows localhost。如果无法访问，需要手动设置端口转发：

```powershell
# 获取 WSL IP
$wslIp = wsl -d Ubuntu -- bash -c "hostname -I | awk '{print `$1}'"
Write-Host "WSL IP: $wslIp"

# 设置端口转发（需要管理员权限）
netsh interface portproxy add v4tov4 listenport=3000 listenaddress=0.0.0.0 connectport=3000 connectaddress=$wslIp
```

---

## 八、LiteLLM Proxy 启动

### 8.1 前置检查

```powershell
# 1. 确认 PostgreSQL 运行中
netstat -ano | findstr ":5432"
# 或
netstat -ano | findstr ":5433"

# 2. 确认端口 4800 未占用
netstat -ano | findstr ":4800"
# 期望无输出

# 3. 确认 .env 文件存在
Test-Path .env
# 期望 True

# 4. 确认虚拟环境存在
Test-Path C:\litellm-env\Scripts\litellm.exe
# 期望 True
```

### 8.2 前台启动（推荐调试用）

```powershell
cd model-platform
C:\litellm-env\Scripts\python.exe start_proxy.py --health-check
```

`--health-check` 模式会：
- 启动 Proxy 进程
- 自动等待服务就绪（最长 60 秒）
- 验证模型列表并打印

期望输出：

```
[INFO] litellm 路径: C:\litellm-env\Scripts\litellm.exe
[INFO] 配置文件:   d:\...\model-platform\config.yaml
[INFO] 监听端口:   4800
[INFO] 已将 Prisma CLI 加入 PATH: ...
[INFO] 启动模式: 前台运行
[INFO] Proxy PID=xxxxx
[OK] Proxy 就绪，已加载 5 个模型: ['minimax-m2-5', 'minimax-m2-7', 'deepseek-v4-flash', 'deepseek-v4-pro', 'glm-5-1']
```

按 `Ctrl+C` 停止。

### 8.3 后台启动（推荐长期运行）

```powershell
cd model-platform
C:\litellm-env\Scripts\python.exe start_proxy.py --background
```

日志输出位置：
- 标准输出：`model-platform/proxy.out.log`
- 标准错误：`model-platform/proxy.err.log`

### 8.4 停止 Proxy

```powershell
# 方式一：按 PID
netstat -ano | findstr ":4800.*LISTENING"
taskkill /PID <PID> /F

# 方式二：按进程名
taskkill /f /im litellm.exe
```

### 8.5 Prisma 数据库迁移（可选）

首次启动后，数据库中缺少部分表（LiteLLM_VerificationTokenView 等），不影响模型路由和调用。如需完整 DB 功能（虚拟 Key 管理、用量统计）：

```powershell
$env:DATABASE_URL = "postgresql://litellm@localhost:5432/litellm"
cd model-platform
C:\litellm-env\Scripts\litellm.exe --config config.yaml --use_prisma_db_push --skip_server_startup
```

> 此命令执行约 30 秒，Prisma 需要生成客户端代码。

---

## 九、验证清单

按顺序执行以下验证，确认所有服务正常运行。

### 9.1 端口检查

```powershell
netstat -ano | findstr ":4800.*LISTENING"   # LiteLLM Proxy
netstat -ano | findstr ":3000.*LISTENING"   # Langfuse
netstat -ano | findstr ":5432.*LISTENING"   # PostgreSQL（或 5433）
```

三个端口都应处于 LISTENING 状态。

### 9.2 模型列表验证

```powershell
py -c "from openai import OpenAI; c = OpenAI(base_url='http://localhost:4800/v1', api_key='sk-my-master-key-1234'); print([m.id for m in c.models.list().data])"
```

期望输出：

```
['minimax-m2-5', 'minimax-m2-7', 'deepseek-v4-flash', 'deepseek-v4-pro', 'glm-5-1']
```

### 9.3 追踪演示验证

```powershell
cd model-tracing
C:\litellm-env\Scripts\python.exe main.py
```

此脚本会依次运行：
1. 智能路由分类（不需要 Proxy）
2. 并行评测（需要 Proxy）
3. 流水线任务（需要 Proxy）

### 9.4 评测 Dry-Run（不需要 Proxy）

```powershell
cd model-eval
C:\litellm-env\Scripts\python.exe run_eval.py --dry-run
```

使用参考答案测试评测器，验证评测逻辑正常。

### 9.5 完整评测（需要 Proxy + Langfuse）

```powershell
cd model-eval
C:\litellm-env\Scripts\python.exe run_eval.py --models deepseek-v4-flash
```

---

## 十、虚拟 Key 管理（可选）

LiteLLM Proxy 支持虚拟 Key 管理，可以为不同应用创建独立 Key，限制可用模型和预算。

```powershell
cd model-platform

# 批量生成预定义模板 Key
C:\litellm-env\Scripts\python.exe create_keys.py generate

# 自定义生成
C:\litellm-env\Scripts\python.exe create_keys.py generate --name my-app --models minimax-m2-5 --budget 5

# 列出所有 Key
C:\litellm-env\Scripts\python.exe create_keys.py list

# 查看 Key 详情
C:\litellm-env\Scripts\python.exe create_keys.py info <key_or_id>

# 吊销 Key
C:\litellm-env\Scripts\python.exe create_keys.py delete <key_or_id> -y

# 更新 Key
C:\litellm-env\Scripts\python.exe create_keys.py update <key_or_id> --budget 30
```

---

## 十一、完整启动流程速查

以下是从零启动所有服务的标准顺序：

```
1. 启动 WSL Docker
   wsl -d Ubuntu -- bash -c "docker ps"  # 确认 Docker 运行

2. 启动 Langfuse
   copy /Y "model-tracing\langfuse-docker-compose.yml" "\\wsl.localhost\Ubuntu\tmp\"
   wsl -d Ubuntu -- bash -c "cd /tmp && docker compose -f langfuse-docker-compose.yml up -d"

3. 初始化数据库（仅首次）
   C:\litellm-env\Scripts\python.exe model-platform\setup_litellm_db.py

4. 启动 LiteLLM Proxy
   cd model-platform
   C:\litellm-env\Scripts\python.exe start_proxy.py --background

5. 等待就绪后验证
   netstat -ano | findstr ":4800"
   py -c "from openai import OpenAI; c = OpenAI(base_url='http://localhost:4800/v1', api_key='sk-my-master-key-1234'); print([m.id for m in c.models.list().data])"

6. 运行业务（追踪 / 评测）
   cd model-tracing && C:\litellm-env\Scripts\python.exe main.py
   cd model-eval && C:\litellm-env\Scripts\python.exe run_eval.py --dry-run
```

---

## 十二、常见排障

### 12.1 `import litellm` 永久挂起

**现象**：`python -c "import litellm"` 命令永不返回。

**原因**：LiteLLM v1.86+ 在 import 时尝试下载 tiktoken 编码数据，网络不通或代理配置导致连接挂起。

**解决**：使用 `litellm.exe` CLI 启动，不要用 `python -m litellm`。`start_proxy.py` 已自动处理。

### 12.2 Prisma CLI 找不到

**现象**：启动日志提示 `prisma` 命令不存在。

**解决**：

```powershell
# 确认 prisma 已安装
npm list -g prisma

# 如果已安装但找不到，手动添加 PATH
$env:PATH = "$env:APPDATA\npm;$env:PATH"
```

`start_proxy.py` 会自动检测 `%APPDATA%\npm` 路径。如果 npm 全局安装路径不在默认位置（如安装到了 `D:\npm-global`），需修改 `start_proxy.py` 中的 `npm_global_candidates` 列表。

### 12.3 代理导致 LiteLLM 启动挂起

**现象**：启动后进程卡住，无任何输出。

**原因**：系统配置了 HTTP_PROXY，litellm 尝试通过代理访问 GitHub 获取 cost map，代理不通导致挂起。

**解决**：`start_proxy.py` 已内置 `_apply_no_proxy()` 自动设置绕过。如果仍有问题，手动设置：

```powershell
$env:NO_PROXY = "localhost,127.0.0.1,github.com,raw.githubusercontent.com"
$env:LITELLM_LOCAL_MODEL_COST_MAP = "True"
```

### 12.4 Langfuse 健康检查返回错误

**现象**：访问 `http://localhost:3000/health` 返回 404。

**原因**：Langfuse 健康检查端点不是 `/health`。

**解决**：使用正确的端点：

```powershell
curl.exe --noproxy '*' -sI http://localhost:3000/api/health
```

### 12.5 数据库连接失败

**现象**：启动日志出现 `connection refused` 或 `database "litellm" does not exist`。

**排查步骤**：

```powershell
# 1. 确认 PostgreSQL 容器运行
wsl -d Ubuntu -- bash -c "docker ps | grep postgres"

# 2. 确认端口映射
wsl -d Ubuntu -- bash -c "docker port langfuse-db"

# 3. 确认数据库已创建
wsl -d Ubuntu -- bash -c "docker exec langfuse-db psql -U langfuse -l" | Select-String "litellm"
```

### 12.6 端口 4800 已被占用

```powershell
# 查找占用进程
netstat -ano | findstr ":4800.*LISTENING"

# 终止占用进程
taskkill /PID <PID> /F

# 或指定其他端口启动
cd model-platform
C:\litellm-env\Scripts\python.exe start_proxy.py --port 4801 --health-check
```

### 12.7 WSL 容器端口无法从 Windows 访问

**排查**：

```powershell
# 获取 WSL IP
wsl -d Ubuntu -- bash -c "hostname -I | awk '{print `$1}'"

# 设置端口转发（管理员 PowerShell）
netsh interface portproxy add v4tov4 listenport=3000 listenaddress=0.0.0.0 connectport=3000 connectaddress=<WSL_IP>
```

### 12.8 PowerShell 中 curl 参数不兼容

PowerShell 的 `curl` 是 `Invoke-WebRequest` 的别名，不支持 Linux 风格参数。使用 `curl.exe` 代替：

```powershell
# 错误
curl http://localhost:4800/health

# 正确
curl.exe --noproxy '*' http://localhost:4800/health
```

### 12.9 数据库表缺失警告（非致命）

**现象**：启动日志出现 `LiteLLM_VerificationTokenView` 或 `LiteLLM_SpendLogs` 不存在。

**影响**：不影响模型路由和调用功能，仅影响用量统计和 Token 验证视图。

**解决**（如需完整功能）：见第八章 8.5 节 Prisma 数据库迁移。

---

## 十三、关键文件速查

| 文件路径 | 用途 |
|----------|------|
| `.env` | 统一环境变量（API Keys + DB + Langfuse） |
| `requirements.txt` | Python 依赖列表 |
| `model-platform/config.yaml` | LiteLLM 模型路由配置 |
| `model-platform/start_proxy.py` | Proxy 启动脚本（跨平台） |
| `model-platform/setup_litellm_db.py` | 数据库初始化脚本（跨平台） |
| `model-platform/create_keys.py` | 虚拟 Key 管理工具 |
| `model-tracing/langfuse-docker-compose.yml` | Langfuse Docker Compose 配置 |
| `model-tracing/main.py` | 追踪演示入口 |
| `model-tracing/core/tracer_factory.py` | 追踪后端工厂（console/langfuse/noop） |
| `model-tracing/core/llm_client.py` | 统一 LLM 调用客户端 |
| `model-eval/run_eval.py` | 评测主入口 |
| `model-eval/langfuse_dataset.py` | Langfuse Dataset 集成 |
| `model-eval/datasets/code_gen_v1.json` | 评测数据集 |
| `model-eval/core/evaluator.py` | L1 语法 + L2 功能评测器 |
