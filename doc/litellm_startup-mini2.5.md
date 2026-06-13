# LiteLLM Proxy 启动指南

> 更新时间：2026-06-03

## 一、快速启动

### 1.1 前置条件

- Python 3.10+
- litellm >= 1.84.0（虚拟环境 `C:\litellm-env` 已预装）
- PostgreSQL 服务已运行（端口 5432），litellm 使用 `DATABASE_URL` 持久化配置
- 虚拟环境中需安装 `prisma` 包：`C:\litellm-env\Scripts\pip install prisma`（否则启动报 warning）
- 项目根目录 `.env` 文件已配置 API Keys

### 1.2 启动命令

`start_proxy.py` 支持三种模式：

```powershell
cd d:\Desktop\Test\MultiModel\model-platform

# 模式1：前台运行（调试用，Ctrl+C 停止）
py start_proxy.py

# 模式2：后台运行（推荐，日志输出到 proxy.out.log / proxy.err.log）
py start_proxy.py --background

# 模式3：前台运行 + 自动健康检查（验证模型列表）
# ⚠️ 谨慎使用：存在子进程端口复用竞态问题（见 4.7 节）
py start_proxy.py --health-check
```

默认监听端口 **4800**，可通过参数修改：
```powershell
py start_proxy.py --port 4000 --background
```

### 1.3 启动成功标志

控制台输出以下内容即启动成功：

```
LiteLLM: Proxy initialized with Config, Set models:
    minimax-m2-5
    minimax-m2-7
    deepseek-v4-flash
    deepseek-v4-pro
    glm-5-1
INFO:     Uvicorn running on http://0.0.0.0:4800 (Press CTRL+C to quit)
```

### 1.4 验证服务

```powershell
# 健康检查（需带 Authorization）
Invoke-RestMethod -Uri "http://localhost:4800/health" -Headers @{"Authorization"="Bearer sk-my-master-key-1234"}

# 模型调用测试
python model-platform/test_call.py
```

### 1.5 停止服务

**前台运行时**：直接 `Ctrl+C`

**后台运行时**：
```powershell
# 方法1：通过端口查找进程
$pid = (netstat -ano | findstr :4800 | Select-String "LISTENING" | ForEach-Object { ($_ -split '\s+')[-1] })
if ($pid) { Stop-Process -Id $pid -Force }

# 方法2：通过进程名查找
Get-Process -Name python | Where-Object { $_.CommandLine -like "*start_proxy*" } | Stop-Process -Force
```

---

## 二、后台运行与日志

### 2.1 后台启动（推荐）

```powershell
cd d:\Desktop\Test\MultiModel\model-platform
py start_proxy.py --background
```

输出示例：
```
[INFO] Proxy PID=17012（后台运行）
[INFO] stdout -> D:\...\model-platform\proxy.out.log
[INFO] stderr -> D:\...\model-platform\proxy.err.log
[INFO] 停止命令: taskkill /PID 17012 /F
```

### 2.2 查看服务是否在运行

```powershell
# 检查端口是否被监听
netstat -ano | findstr :4800

# 示例输出表示服务运行中：
# TCP    0.0.0.0:4800    0.0.0.0:0    LISTENING    17012

# Python 快速验证（401 = 服务在运行）
py -c "import requests; print(requests.get('http://localhost:4800/health', timeout=5).status_code)"
```

### 2.3 日志查看

```powershell
# 查看最新 20 行输出日志
Get-Content -Path "d:\Desktop\Test\MultiModel\model-platform\proxy.out.log" -Tail 20

# 查看错误日志
Get-Content -Path "d:\Desktop\Test\MultiModel\model-platform\proxy.err.log" -Tail 20
```

### 2.4 自动健康检查模式（谨慎使用）

```powershell
py start_proxy.py --health-check
```

该模式会前台启动并自动等待就绪（最长 60s），然后打印加载的模型列表。
⚠️ **已知问题**：健康检查通过后会触发子进程端口复用冲突（见 4.7 节），建议日常使用 `--background` 模式。

---

## 三、配置说明

### 3.1 模型配置（model-platform/config.yaml）

| 模型名 | 底层模型 | API 来源 | 类型 |
|--------|---------|----------|------|
| minimax-m2-5 | openai/MiniMax-M2.5 | minimaxi.com | 普通对话 |
| minimax-m2-7 | openai/MiniMax-M2.7 | minimaxi.com | 推理模型 |
| deepseek-v4-flash | deepseek/deepseek-v4-flash | deepseek.com | 推理模型 |
| deepseek-v4-pro | deepseek/deepseek-v4-pro | deepseek.com | 推理模型 |
| glm-5-1 | openai/glm-5.1 | z.ai | 普通对话 |

### 3.2 环境变量（项目根 .env）

```env
# 模型 API Keys
MINIMAX_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
ZAI_API_KEY=...

# LiteLLM Proxy
LITELLM_MASTER_KEY=sk-my-master-key-1234
LITELLM_BASE_URL=http://localhost:4800

# Langfuse（可选，评测/追踪时需要）
TRACER_BACKEND=langfuse
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000
```

### 3.3 max_tokens 分模型配置

推理模型的思考链（reasoning）与最终输出共享 max_tokens 上限，需更高限制：

| 模型类型 | 模型 | max_tokens |
|---------|------|-----------|
| 推理模型 | minimax-m2-7, deepseek-v4-flash, deepseek-v4-pro | **8192** |
| 普通对话 | minimax-m2-5, glm-5-1 | 2048 |

代码中通过 `REASONING_MODELS` 集合自动判断，无需手动传参：

```python
REASONING_MODELS = {"minimax-m2-7", "deepseek-v4-flash", "deepseek-v4-pro"}
max_tokens = 8192 if model in REASONING_MODELS else 2048
```

涉及的文件：
- `model-eval/run_eval.py` — 评测框架
- `model-tracing/core/llm_client.py` — 追踪模块
- `model-task/core/llm_client.py` — 任务模块

---

## 四、实际遇到的问题及解决

### 4.1 cost map 警告：getaddrinfo failed

**现象**：启动时报错

```
LiteLLM:WARNING: Failed to fetch remote model cost map from https://raw.githubusercontent.com/...: [Errno 11004] getaddrinfo failed.
```

**原因**：无法访问 GitHub（网络不通或 DNS 失败），LiteLLM 自动回退本地模型成本映射。

**解决**：可安全忽略，不影响代理服务功能和模型调用。

### 4.2 健康检查返回 401

**现象**：`curl http://localhost:4800/health` 返回 `Authentication Error`

**原因**：config.yaml 配置了 `master_key`，所有请求需携带认证。

**解决**：请求时带 Authorization header：

```powershell
Invoke-RestMethod -Uri "http://localhost:4800/health" -Headers @{"Authorization"="Bearer sk-my-master-key-1234"}
```

### 4.3 PowerShell 中 curl 不支持 -H 参数

**现象**：`curl -H "Authorization: Bearer ..."` 报错无法转换参数

**原因**：PowerShell 的 `curl` 是 `Invoke-WebRequest` 的别名，语法不同。

**解决**：使用 `Invoke-RestMethod` 替代，或直接用 Python 脚本测试。

### 4.4 推理模型返回空 content

**现象**：minimax-m2-7 / deepseek-v4-flash 调用成功（200 OK），但 `content` 为空字符串，`finish_reason=length`。

**原因**：推理模型的思考链（reasoning_content）消耗大量 token，max_tokens=2048 仅够思考过程，无余量输出最终答案。content 与 reasoning 共享 max_tokens 上限。

**解决**：推理模型 max_tokens 提升至 8192（见 3.3 节）。调整后 `finish_reason=stop`，content 正常输出。

### 4.5 test_call.py 端口不一致

**现象**：`test_call.py` 中 `base_url="http://localhost:4000/v1"`，与实际服务端口 4800 不匹配。

**原因**：端口曾从 4000 改为 4800，但测试脚本未同步更新。

**解决**：已修正 `base_url="http://localhost:4800/v1"`。llm_client.py 同步修正。

### 4.6 启动报 prisma 包缺失

**现象**：启动时输出

```
Unable to connect to DB. DATABASE_URL found in environment, but prisma package not found.
```

**原因**：虚拟环境 `C:\litellm-env` 中未安装 `prisma` 包，LiteLLM 无法通过 Prisma ORM 连接 PostgreSQL。虽不影响核心代理功能，但会导致配置无法持久化到数据库。

**解决**：

```powershell
C:\litellm-env\Scripts\pip install prisma
```

安装后需重启 LiteLLM 使生效。

### 4.7 --health-check 模式端口冲突

**现象**：使用 `--health-check` 启动后，健康检查通过但随后报错

```
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 4800):
[winerror 10048] 通常每个套接字地址(协议/网络地址/端口)只允许使用一次。
```

**原因**：LiteLLM 内部存在子进程竞态——健康检查通过后主进程收到中断信号停止，但 litellm 内部的 worker 子进程仍试图绑定 4800 端口，与主进程产生冲突。这是 `start_proxy.py --health-check` 模式的设计缺陷。

**解决**：日常使用 `--background` 模式代替 `--health-check`：

```powershell
py start_proxy.py --background
# 手动验证
py -c "import requests; print(requests.get('http://localhost:4800/health', timeout=5).status_code)"
```

---

## 五、可能遇到的问题及预案

### 5.1 端口被占用

**现象**：`OSError: [WinError 10048]` 或 `Address already in use`

**排查**：

```powershell
netstat -ano | findstr :4800
```

**解决**：
- 终止占用进程：`taskkill /PID <PID> /F`
- 或使用其他端口启动：`python start_proxy.py --port 5000`

### 5.2 启动前端口检测

在启动服务前，建议先检查端口是否可用：

```powershell
$port = 4800
$listener = (netstat -ano | findstr ":$port " | Select-String "LISTENING")
if ($listener) {
    Write-Host "端口 $port 已被占用，请先停止现有服务或使用其他端口" -ForegroundColor Red
    netstat -ano | findstr ":$port "
} else {
    Write-Host "端口 $port 可用" -ForegroundColor Green
    cd d:\Desktop\Test\MultiModel\model-platform
    python start_proxy.py
}
```

### 5.3 API Key 无效或过期

**现象**：模型调用返回 `401 Unauthorized` 或 `Invalid API Key`

**排查**：检查 `.env` 中对应 Key 是否正确

```
MINIMAX_API_KEY   → https://platform.minimaxi.com
DEEPSEEK_API_KEY  → https://platform.deepseek.com
ZAI_API_KEY       → https://open.bigmodel.cn
```

### 5.4 模型调用超时

**现象**：请求长时间无响应

**原因**：模型 API 网络不通或服务端限流

**解决**：
- 检查网络连通性
- config.yaml 已配置 `request_timeout: 120`，可适当增大
- 代理环境需确保 localhost 请求不走代理（设置 `no_proxy=localhost,127.0.0.1`）

### 5.5 Langfuse 连接失败（评测/追踪场景）

**现象**：`run_eval.py` 或 `main.py` 报 Langfuse 连接错误

**前置条件**：
1. WSL Docker 中 Langfuse 服务已启动（端口 3000）
2. Windows 端口转发已配置（WSL → Windows localhost:3000）
3. `.env` 中 Langfuse Key 配置正确

**排查**：

```powershell
Invoke-RestMethod -Uri "http://localhost:3000/api/public/traces" -Headers @{"Authorization"="Bearer $(pk-lf-...:sk-lf-... 的 Base64 编码)"}
```

详见 `doc/langfuse.md`。

### 5.6 litellm 版本过低导致 glm-5-1 不可用

**现象**：glm-5-1 调用报错 `Model not found` 或 provider 不支持

**原因**：`zai/` provider 需要 litellm >= 1.84.0

**解决**：

```powershell
pip install --upgrade "litellm[proxy]>=1.84.0"
```

### 5.7 Windows 端口排除导致绑定失败

**现象**：`start_proxy.py` 启动时端口被排除（Windows Hyper-V 保留端口范围）

**排查**：

```powershell
netsh interface ipv4 show excludedportrange protocol=tcp
```

**解决**：选择不在排除范围内的端口，如 4800（当前默认端口已避开常见排除范围）。

---

## 六、服务端口速查

| 服务 | 端口 | 说明 |
|------|------|------|
| LiteLLM Proxy | 4800 | 模型统一接入（Windows 本地） |
| Langfuse Web | 3000 | 追踪可视化（WSL Docker） |

---

## 七、关键文件索引

| 文件 | 用途 |
|------|------|
| `model-platform/start_proxy.py` | LiteLLM Proxy 启动脚本 |
| `model-platform/config.yaml` | 模型列表与路由配置 |
| `.env` | 项目统一环境变量 |
| `model-platform/test_call.py` | 5 模型快速调用测试 |
| `model-eval/run_eval.py` | 代码生成评测主入口 |
| `model-tracing/core/llm_client.py` | 追踪模块 LLM 客户端 |
| `model-task/core/llm_client.py` | 任务模块 LLM 客户端 |
