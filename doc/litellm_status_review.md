# LiteLLM 现状梳理

> 更新时间：2026-06-06

---

## 一、已具备的能力

| 能力 | 详情 |
|------|------|
| **多模型统一接入** | 5 个模型已配置并验证通过：MiniMax M2.5/M2.7、DeepSeek V4-Flash/V4-Pro、智谱 GLM-5.1 |
| **OpenAI 兼容 API** | 统一 `localhost:4800/v1` 端点，业务方用 OpenAI SDK 即可调用 |
| **启动脚本** | `start_proxy.py` 支持前台/后台/健康检查三种模式，自动处理 NO_PROXY、Prisma CLI 路径 |
| **虚拟 Key 管理** | `create_keys.py` 支持 generate/list/info/delete/update 五个子命令 |
| **自动化测试** | `test_call.py` 7 步测试流程（连通性→生成→隔离→查询→更新→吊销→清理） |
| **Cost Map 本地化** | `.env` 中 `LITELLM_LOCAL_MODEL_COST_MAP=True` 跳过远程获取，消除警告 |
| **PostgreSQL 数据库** | 本地 PG15 已安装，64 张表已通过 `prisma db push` 创建 |
| **知识库文档** | `model_readme.md` + km 目录下 4 个标准化词条 |

### 已接入模型清单（config.yaml）

| 厂商 | model_name（调用用） | LiteLLM 标识 | API Base | 状态 |
|------|---------------------|-------------|----------|------|
| MiniMax | `minimax-m2-5` | `openai/MiniMax-M2.5` | `https://api.minimaxi.com/v1` | 已验证 |
| MiniMax | `minimax-m2-7` | `openai/MiniMax-M2.7` | `https://api.minimaxi.com/v1` | 已验证 |
| DeepSeek | `deepseek-v4-flash` | `deepseek/deepseek-v4-flash` | 默认 | 已验证 |
| DeepSeek | `deepseek-v4-pro` | `deepseek/deepseek-v4-pro` | 默认 | 已验证 |
| 智谱 | `glm-5-1` | `openai/glm-5.1` | `https://api.z.ai/api/paas/v4/` | 已验证 |

### 关键文件一览

| 文件 | 用途 |
|------|------|
| `config.yaml` | LiteLLM 模型路由配置 |
| `start_proxy.py` | Proxy 启动脚本（前台/后台/健康检查） |
| `create_keys.py` | 虚拟 Key 管理工具（5 个子命令） |
| `test_call.py` | 虚拟 Key 自动化测试（7 步流程） |
| `test_glm.py` | 智谱 GLM-5.1 专项测试 |
| `setup_litellm_db.py` | 数据库初始化脚本（WSL Docker 方式） |

---

## 二、核心阻塞问题：DB 连接未打通

这是目前最关键的问题，直接导致**虚拟 Key 功能不可用**。

### 现象

启动日志显示：

```
Unable to connect to DB. DATABASE_URL found in environment, but prisma package not found.
```

err.log 中还有：

```
prisma.errors.RawQueryError: 关系 "LiteLLM_VerificationTokenView" 不存在
```

### 根因分析

```
LiteLLM 源码 (proxy_cli.py):
    subprocess.run(["prisma"], capture_output=True)

问题链:
1. litellm.exe 是 PyInstaller 编译的独立二进制文件
2. 它不使用 venv 中 pip 安装的 prisma Python 包
3. 而是通过 subprocess.run(["prisma"]) 调用系统 PATH 中的 prisma CLI
4. prisma CLI 通过 npm install -g prisma 安装到 D:\npm-global\prisma.cmd
5. Windows 上 subprocess.run 默认只找 .exe 文件，不找 .cmd 文件
6. 因此 FileNotFoundError → is_prisma_runnable = False → DB not connected
```

### 代码层面已做的工作

- `start_proxy.py` 中的 `_patch_litellm_prisma_check()` 已实现自动修补逻辑（给 `subprocess.run` 加 `shell=True`）
- 但修补的是 venv 中的源码，而 `litellm.exe` 是 PyInstaller 编译的独立二进制，**不走 venv 源码**
- 数据库中还缺少 `LiteLLM_VerificationTokenView` 视图，说明数据库迁移不完整

---

## 三、后续需要完善的事项

### P0 — 必须解决

| # | 事项 | 说明 |
|---|------|------|
| 1 | **修复 Prisma 检测 → 打通 DB 连接** | 需手动编辑 `C:\litellm-env\Lib\site-packages\litellm\proxy\proxy_cli.py`，找到 `subprocess.run(["prisma"], capture_output=True)` 改为 `subprocess.run(["prisma"], capture_output=True, shell=True)`。或考虑直接用 `python -m litellm` 替代 `litellm.exe` 启动（需解决 tiktoken 编码下载阻塞问题） |
| 2 | **补全数据库视图** | DB 连通后，需运行 `prisma db push` 或 `litellm --migrate` 补全 `LiteLLM_VerificationTokenView` 等缺失对象 |
| 3 | **端到端验证虚拟 Key 全流程** | DB 打通后执行 `test_call.py`，验证 generate/list/info/update/delete 完整链路 |

### P1 — 重要改进

| # | 事项 | 说明 |
|---|------|------|
| 4 | **config.yaml 中 database_url 被注释** | 当前 `# database_url: os.environ/DATABASE_URL`，需取消注释才能启用 DB 持久化 |
| 5 | **model_readme.md 版本信息过时** | LiteLLM 实际已升级到 1.87.0，但 README 仍写 1.84.0 |
| 6 | **setup_litellm_db.py 基于 WSL Docker** | 当前 PostgreSQL 是本地安装（PG15），但 setup 脚本仍按 WSL Docker 方式编写，存在不一致 |

### P2 — 锦上添花

| # | 事项 | 说明 |
|---|------|------|
| 7 | **接入更多模型** | 当前 3 家 5 个模型，可考虑通义千问、文心一言等 |
| 8 | **model-task 与 model-tracing 重复** | system_status.md 已标记为待处理，建议废弃 model-task 或合并 |
| 9 | **虚拟 Key 管理进度备忘可归档** | `虚拟Key管理进度备忘.md` 记录了阻塞状态，DB 打通后应更新为已完成 |
| 10 | **start_proxy.py 的 Prisma 修补逻辑可简化** | 若最终用方案 A 手动修改，`_patch_litellm_prisma_check()` 中的自动修补代码可移除 |

---

## 四、快速恢复路径

解除阻塞的最小步骤：

```bash
# 步骤 1：手动编辑 LiteLLM 源码
# 打开文件: C:\litellm-env\Lib\site-packages\litellm\proxy\proxy_cli.py
# 找到: subprocess.run(["prisma"], capture_output=True)
# 改为: subprocess.run(["prisma"], capture_output=True, shell=True)
# 保存

# 步骤 2：取消 config.yaml 中 database_url 的注释
# 打开文件: model-platform/config.yaml
# 将 "# database_url: os.environ/DATABASE_URL" 改为 "database_url: os.environ/DATABASE_URL"

# 步骤 3：确认 PostgreSQL 服务运行中
# 检查数据库 litellm 是否存在

# 步骤 4：启动 Proxy
cd model-platform
py start_proxy.py

# 步骤 5：验证
# 查看日志不应有 "prisma package not found"
type proxy.out.log

# 步骤 6：运行自动化测试
py test_call.py
```

---

## 五、环境依赖清单

| 依赖 | 状态 | 说明 |
|------|------|------|
| Python 3.13 | 已安装 | 系统级 |
| LiteLLM venv | `C:\litellm-env\` | litellm==1.87.0, prisma==0.15.0 |
| PostgreSQL 15 | 运行中 | localhost:5432, 数据库 `litellm`（64 张表已存在） |
| Node.js v22.16.0 | 已安装 | `D:\Program Files\nodejs\` |
| Prisma CLI 7.8.0 | 已安装 | `D:\npm-global\prisma.cmd`（npm install -g prisma） |
| Prisma CLI 在 PATH | 否 | `D:\npm-global` 不在系统 PATH 中（start_proxy.py 已自动处理） |
| LiteLLM prisma 检测 | 失败 | subprocess.run 找不到 .cmd 文件，需手动修补 |
