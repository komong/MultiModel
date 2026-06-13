# LiteLLM Proxy 启动指南（Agent 专用）

> 更新时间：2026-06-01
> 编写背景：经历多次启动失败后，整理面向 Agent 的可靠启动流程及排障方案。

## 一、推荐启动方式（经过实战验证）

### 正确命令

```powershell
cd d:\Desktop\Test\MultiModel\model-platform
C:\litellm-env\Scripts\python.exe start_debug.py
```

**为什么用 `start_debug.py` 而不是 `start_proxy.py`：**
- `start_debug.py` 使用 `litellm.exe` CLI 直接启动，进程独立于终端（`CREATE_NEW_PROCESS_GROUP`）
- `start_proxy.py` 用 `subprocess.call` 阻塞等待，终端关闭或复用时进程会一起被杀

### 一键验证（启动后执行）

```powershell
# 1. 确认端口已监听
netstat -ano | findstr ":4800"
# 期望输出：TCP    0.0.0.0:4800    0.0.0.0:0    LISTENING    <PID>

# 2. 模型列表验证
py -c "from openai import OpenAI; c = OpenAI(base_url='http://localhost:4800/v1', api_key='sk-my-master-key-1234'); print([m.id for m in c.models.list().data])"
# 期望输出：['minimax-m2-5', 'minimax-m2-7', 'deepseek-v4-flash', 'deepseek-v4-pro', 'glm-5-1']
```

---

## 二、前置条件检查清单

| 检查项 | 命令 | 期望结果 |
|--------|------|----------|
| PostgreSQL 运行中 | `netstat -ano \| findstr ":5432"` | `LISTENING` |
| 虚拟环境存在 | `Test-Path C:\litellm-env\Scripts\python.exe` | `True` |
| `.env` 文件完整 | 检查 3 个 API Key 均已配置 | - |
| 端口 4800 未占用 | `netstat -ano \| findstr ":4800"` | 无输出 |

---

## 三、实际遇到的坑及解决方案

### 3.1 venv Python 中 import litellm 挂起（核心问题）

**现象：**

```powershell
C:\litellm-env\Scripts\python.exe -c "import litellm; print('ok')"
# 永远不返回，必须 Ctrl+C 终止
```

**原因：** LiteLLM v1.86.2 在 import 时尝试下载 tiktoken 编码数据（`cl100k_base.tiktoken`），若网络不通或代理配置导致连接挂起，整个 import 永久阻塞。注意这不是 Python 层级的问题——`litellm.exe`（编译后的 CLI 入口）不触发此问题。

**解决：** 必须使用 `litellm.exe` CLI 启动，不能使用 `python -m litellm.proxy.proxy_server`。

```diff
# start_debug.py 中的关键修复
- p = subprocess.Popen([sys.executable, "-m", "litellm.proxy.proxy_server", ...])
+ litellm_exe = str(Path(sys.executable).parent / 'litellm.exe')
+ p = subprocess.Popen([litellm_exe, "--config", config_path, "--port", "4800"], ...)
```

**历史遗留：** `start_proxy.py` 仍使用 `python -m litellm.proxy.proxy_server`，在 venv 环境下同样会挂起。建议淘汰。

### 3.2 子进程被终端复用杀死

**现象：** 用 `subprocess.call` 或 `subprocess.run` 启动后，过一会儿端口消失，进程不存在。

**原因：**
- `subprocess.call/run` 会阻塞等待子进程退出
- Agent 执行的终端被复用（下一个命令在同一终端执行）时，阻塞中的父进程收到信号退出，连带杀死子进程
- `subprocess.Popen` 即使不阻塞，如果未设置 `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP`，子进程也可能被父终端信号影响

**解决：** 使用 `subprocess.Popen` + `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP`，让代理进程脱离当前终端进程组。

### 3.3 数据库表缺失（非致命警告）

**现象：** 启动日志中出现：

```
prisma.errors.RawQueryError: 关系 "LiteLLM_VerificationTokenView" 不存在
prisma.errors.RawQueryError: 关系 "LiteLLM_SpendLogs" 不存在
```

**原因：** PostgreSQL 数据库已连接但从未执行过 schema 迁移（`prisma db push`）。

**影响：** 不影响模型路由和调用功能。Proxy 会正常启动并响应请求。仅以下功能受影响：
- SpendLogs（用量统计）
- VerificationToken（Token 验证视图）

**如果需要完整 DB 功能：**

```powershell
$env:DATABASE_URL = "postgresql://litellm@localhost:5432/litellm"
cd d:\Desktop\Test\MultiModel\model-platform
C:\litellm-env\Scripts\litellm.exe --config config.yaml --use_prisma_db_push --skip_server_startup
```

**注意：** 该命令执行时间较长（30s+），因为 Prisma 需要生成客户端代码。

### 3.4 环境变量传递失败

**现象：** 用 PowerShell 设置 `$env:XXX=...` 后直接运行 `litellm.exe`，模型加载成功但调用时报 API Key 错误。

**原因：**
- `config.yaml` 中使用 `os.environ/MINIMAX_API_KEY` 语法引用环境变量
- 在 Agent 执行的终端中，通过 `$env:` 设置的变量可能不会被子进程继承（取决于终端实现）
- 最可靠的方式是通过 Python `load_dotenv()` 加载 `.env` 文件

**解决：** 启动脚本（`start_debug.py`）已内置 `load_dotenv(Path(__file__).parent.parent / '.env')`，确保所有环境变量正确传递给子进程。

### 3.5 健康检查返回 401

**现象：** `curl http://localhost:4800/health` 返回 `401 Unauthorized`。

**这不是错误**——Proxy 配置了 `master_key`，健康端点也需要认证。验证服务是否正常用模型列表接口即可（见第一章）。

---

## 四、停止服务

```powershell
# 查找占用 4800 端口的进程
netstat -ano | findstr ":4800.*LISTENING"

# 强制终止
taskkill /PID <PID> /F

# 或批量终止所有 litellm 进程
taskkill /f /im litellm.exe
```

---

## 五、启动流程速查（Agent 执行用）

```
1. netstat -ano | findstr ":5432"           → 确认 PG 运行
2. netstat -ano | findstr ":4800"           → 确认端口空闲
3. cd model-platform && C:\litellm-env\Scripts\python.exe start_debug.py
4. 等待 ~15 秒
5. netstat -ano | findstr ":4800"           → 确认 LISTENING
6. py -c "from openai import OpenAI; ..."   → 模型列表验证
```

---

## 六、关键文件

| 文件 | 用途 |
|------|------|
| `model-platform/start_debug.py` | **推荐**启动脚本（CLI 模式，进程独立） |
| `model-platform/start_proxy.py` | 旧版启动脚本（有挂起风险，不建议） |
| `model-platform/config.yaml` | 模型列表与路由配置 |
| `.env` | 统一环境变量（API Keys + DB 配置） |
| `doc/litellm_startup.md` | 完整启动指南（面向人类） |
