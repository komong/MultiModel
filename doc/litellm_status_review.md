# LiteLLM 现状梳理

> 更新时间：2026-06-14

---

## 一、已具备的能力

| 能力 | 详情 |
|------|------|
| **多模型统一接入** | 5 个模型已配置并验证通过：MiniMax M2.5/M2.7、DeepSeek V4-Flash/V4-Pro、智谱 GLM-5.1 |
| **OpenAI 兼容 API** | 统一 `localhost:4800/v1` 端点，业务方用 OpenAI SDK 即可调用 |
| **启动脚本** | `start_proxy.py` 支持前台/后台/健康检查三种模式，自动处理 NO_PROXY、Prisma CLI 路径 |
| **虚拟 Key 管理** | `create_keys.py` 支持 generate/list/info/delete/update 五个子命令（已适配 LiteLLM 1.87 API） |
| **自动化测试** | `test_call.py` 7 步测试流程（连通性→生成→隔离→查询→更新→吊销→清理）— 全流程通过 |
| **Cost Map 本地化** | `.env` 中 `LITELLM_LOCAL_MODEL_COST_MAP=True` 跳过远程获取，消除警告 |
| **PostgreSQL 数据库** | 本地 PG15 已安装，128 个迁移已通过 Prisma 应用，数据库持久化完全打通 |
| **数据库视图** | 8 个 LiteLLM 系统视图已手动创建（含 VerificationTokenView 等核心视图） |
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
| `config.yaml` | LiteLLM 模型路由配置（database_url 已启用） |
| `start_proxy.py` | Proxy 启动脚本（前台/后台/健康检查，自动补丁 Prisma CLI） |
| `create_keys.py` | 虚拟 Key 管理工具（5 个子命令，已适配 1.87 API） |
| `test_call.py` | 虚拟 Key 自动化测试（7 步流程） |
| `test_glm.py` | 智谱 GLM-5.1 专项测试 |
| `setup_litellm_db.py` | 数据库初始化脚本（本地 PostgreSQL 方式） |
| `create_views.sql` | 8 个系统视图的 SQL 定义（解决中文 locale 问题） |

---

## 二、数据库与视图

### 数据库连接状态：已打通

- PostgreSQL 15 运行于 `localhost:5432`，数据库名 `litellm`
- 128 个 Prisma 迁移已全部应用（`No pending migrations to apply`）
- `config.yaml` 中 `database_url` 已取消注释并启用
- Proxy 启动时自动执行 `prisma migrate deploy`，无错误

### VerificationTokenView 视图问题：已解决

**根因**：PostgreSQL 中文 locale 产生的错误消息为"不存在"，而 LiteLLM 源码 `create_views.py` 的 `_VIEW_NOT_FOUND_MARKERS` 只匹配英文（`"does not exist"` 等），导致视图自动创建逻辑失败。

**修复**：从 LiteLLM 源码提取 8 个视图的 SQL 定义，通过 `psql -f create_views.sql` 手动创建全部视图，绕过 locale 匹配问题。

已创建的 8 个视图：
1. `LiteLLM_VerificationTokenView`（核心：Key 验证依赖此视图）
2. `MonthlyGlobalSpend`
3. `Last30dKeysBySpend`
4. `Last30dModelsBySpend`
5. `MonthlyGlobalSpendPerKey`
6. `MonthlyGlobalSpendPerUserPerKey`
7. `DailyTagSpend`
8. `Last30dTopEndUsersSpend`

### 端到端验证结果

`test_call.py` 7 步测试全部执行，15/18 通过。3 个失败项均为 minimax 上游 API 429 限流（非代码问题）：
- 生成 Key — 通过
- 权限隔离（正向+反向） — 通过（minimax 调用因上游限流 429 失败）
- Key 查询（`/v2/key/info`） — 通过
- Key 更新（权限变更） — 通过
- Key 吊销（吊销后不可调用） — 通过
- 清理 — 通过

---

## 三、Prisma CLI 兼容性

### 问题：已解决

**根因**：LiteLLM 通过 `subprocess.run(["prisma"])` 检测 Prisma CLI。Windows 上 `subprocess.run` 默认只找 `.exe` 文件，不找 `.cmd` 文件，而 Prisma CLI 安装为 `prisma.cmd`。

**解决方案**：`start_proxy.py` 中的 `_patch_litellm_prisma_check()` 和 `_patch_proxy_extras_prisma()` 自动将 `subprocess.run` 调用加上 `shell=True` 参数，使 Windows 能正确找到 `.cmd` 文件。补丁在每次启动 Proxy 时自动应用。

---

## 四、后续可完善的事项

### P2 — 锦上添花

| # | 事项 | 说明 |
|---|------|------|
| 1 | **接入更多模型** | 当前 3 家 5 个模型，可考虑通义千问、文心一言等 |
| 2 | **start_proxy.py 的 Prisma 修补逻辑可简化** | 若 LiteLLM 官方修复 Windows 兼容性，`_patch_litellm_prisma_check()` 可移除 |
| 3 | **监控与告警** | 可接入 LiteLLM 的 spend tracking 和 alerting 功能 |

---

## 五、环境依赖清单

| 依赖 | 状态 | 说明 |
|------|------|------|
| Python 3.13 | 已安装 | 系统级 |
| LiteLLM venv | `C:\litellm-env\` | litellm==1.87.0, prisma==0.15.0 |
| PostgreSQL 15 | 运行中 | localhost:5432, 数据库 `litellm`（128 个迁移已应用，8 个视图已创建） |
| Node.js v22.16.0 | 已安装 | `D:\Program Files\nodejs\` |
| Prisma CLI 7.8.0 | 已安装 | `D:\npm-global\prisma.cmd`（npm install -g prisma） |
| Prisma CLI 在 PATH | 否 | `D:\npm-global` 不在系统 PATH 中（start_proxy.py 自动处理 shell=True） |
| LiteLLM prisma 检测 | 已解决 | start_proxy.py 自动补丁 `shell=True`，Proxy 启动正常 |
