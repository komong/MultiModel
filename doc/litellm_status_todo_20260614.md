# LiteLLM 现状梳理与待办清单

> **创建时间**：2026-06-14
> **用途**：梳理 LiteLLM 当前真实运行状态、已完成工作、后续待办，便于团队成员及其它 AI agent 快速了解 LiteLLM 相关情况。
> **信息来源**：基于 2026-06-14 的 `proxy.out.log` / `proxy.err.log` 实际日志、项目源码、记忆库。

---

## 一、当前真实运行状态（基于 6/14 日志）

> **重要说明**：`litellm_status_review.md`（6/6）和 `虚拟Key管理进度备忘.md`（6/6）中标记为"核心阻塞"的 Prisma 检测问题，**实际已被 `start_proxy.py` 中的自动补丁解决**。以下状态以最新日志为准。

| 项目 | 状态 | 证据 |
|------|------|------|
| Proxy 启动 | 正常 | `Uvicorn running on http://0.0.0.0:4800` |
| 5 个模型加载 | 正常 | minimax-m2-5/7、deepseek-v4-flash/pro、glm-5-1 全部注册 |
| 数据库连接 | 已打通 | 128 个迁移全部 resolved，`Application startup complete` |
| Health Check | 通过 | `GET /health HTTP/1.1 200 OK` |
| Prisma CLI 检测 | 已解决 | `start_proxy.py` 的自动补丁已生效（shell=True） |
| **VerificationTokenView** | **已解决** | 8 个系统视图已手动创建（`create_views.sql`），重启 Proxy 后无错误 |

**结论**：核心能力（多模型接入、Proxy 启动、数据库连接、迁移、系统视图、虚拟 Key 管理）已全部跑通。P0 和 P1 待办项全部完成。

---

## 二、已接入模型清单（config.yaml）

| 厂商 | model_name（调用用） | LiteLLM 标识 | API Base | 状态 |
|------|---------------------|-------------|----------|------|
| MiniMax | `minimax-m2-5` | `openai/MiniMax-M2.5` | `https://api.minimaxi.com/v1` | 已验证 |
| MiniMax | `minimax-m2-7` | `openai/MiniMax-M2.7` | `https://api.minimaxi.com/v1` | 已验证 |
| DeepSeek | `deepseek-v4-flash` | `deepseek/deepseek-v4-flash` | 默认 | 已验证 |
| DeepSeek | `deepseek-v4-pro` | `deepseek/deepseek-v4-pro` | 默认 | 已验证 |
| 智谱 | `glm-5-1` | `openai/glm-5.1` | `https://api.z.ai/api/paas/v4/` | 已验证 |

---

## 三、已完成工作（按阶段梳理）

### 阶段 1：基础搭建

- 创建独立 venv（`C:\litellm-env`，litellm 1.87.0, prisma 0.15.0）
- 接入 3 家厂商 5 个模型（MiniMax / DeepSeek / 智谱）
- 编写 `model-platform/config.yaml`：重试 3 次、超时 120s、drop_params
- 编写 `model-platform/start_proxy.py`：支持前台 / 后台 / 健康检查三种模式

### 阶段 2：Windows 跨平台排障

| 问题 | 解决方案 |
|------|---------|
| 端口 4000 被 Windows 排除 | 改用 4800，`start_proxy.py` 支持 `--port` 参数 |
| litellm.exe 启动挂起 | 设置 `NO_PROXY` 绕过代理（不走 GitHub 获取 cost map） |
| Prisma CLI 找不到 .cmd | `_patch_litellm_prisma_check()` 自动加 `shell=True` |
| litellm_proxy_extras 调用 prisma 失败 | v2 补丁 `_patch_proxy_extras_prisma()`：shell=True + 参数自动加引号 |
| venv 中 import litellm 挂起 | 使用 `litellm.exe` 而非 `python -m litellm`（规避 tiktoken 编码下载阻塞） |
| Cost Map 远程获取警告 | `.env` 设置 `LITELLM_LOCAL_MODEL_COST_MAP=True` |

### 阶段 3：数据库集成

- 本地安装 PostgreSQL 15（`pg15\` 目录），运行于 `localhost:5432`
- 创建 `litellm` 数据库，执行 `prisma db push`（初始 64 张表）
- `config.yaml` 中 `database_url` 已启用（不再注释）
- LiteLLM 自身迁移机制跑通 128 个迁移

### 阶段 4：虚拟 Key 管理

- `model-platform/create_keys.py` 重写为 5 子命令工具（generate / list / info / delete / update）
- `model-platform/test_call.py` 重写为 7 步自动化测试（动态生成 Key、权限隔离测试、自动清理）
- 预定义 3 个模板：system-a（MiniMax/$10）、system-b（DeepSeek/$20）、system-c（全模型）

### 阶段 5：文档与知识库

- `model-platform/model_readme.md`：模型接入说明
- `doc/litellm_startup.md` / `doc/litellm_startup-mini2.5.md`：启动文档
- `doc/litellm_status_review.md`：现状梳理（已更新至 6/14）
- `doc/km/` 目录下标准化知识库词条

---

## 四、待办事项状态

### P0 — 阻塞项（已全部解决 ✅）

| # | 事项 | 状态 | 实际执行结果 |
|---|------|------|-------------|
| 1 | **修复 VerificationTokenView 缺失** | ✅ 已完成 | 根因：PG 中文 locale 导致错误消息"不存在"无法被 LiteLLM 源码 `_VIEW_NOT_FOUND_MARKERS` 匹配。修复：从源码提取 8 个视图 SQL，通过 `psql -f create_views.sql` 手动创建 |
| 2 | **端到端验证虚拟 Key 全流程** | ✅ 已完成 | `test_call.py` 7 步测试执行完毕，15/18 通过。3 个失败均为 minimax 上游 API 429 限流（非代码问题）。同时修复了 `create_keys.py` 和 `test_call.py` 适配 LiteLLM 1.87 `/v2/key/info` 端点 |

### P1 — 文档同步与改进（已全部完成 ✅）

| # | 事项 | 状态 | 实际执行结果 |
|---|------|------|-------------|
| 3 | **更新过时文档** | ✅ 已完成 | 三个文档均已更新：`litellm_status_review.md`（删除阻塞章节、更新表数/视图/Prisma 状态）、`虚拟Key管理进度备忘.md`（状态改为“全部完成”）、`model_readme.md`（版本号 1.84→1.87、补充 DB 信息和 5 个子命令说明） |
| 4 | **model-task 与 model-tracing 去重** | ✅ 已完成 | 在 `model-task/` 创建 `DEPRECATED.md` 标记废弃，指引使用 `model-tracing/`。不删除代码以保留可追溯性 |
| 5 | **setup_litellm_db.py 方式不一致** | ✅ 已完成 | 重写为本地 PostgreSQL 方式：从 .env 读取 DATABASE_URL、使用 `pg15\pgsql\bin\psql.exe` 执行 SQL、支持检查/创建数据库、创建视图、验证状态 |

### P2 — 能力增强

| # | 事项 | 说明 |
|---|------|------|
| 6 | **接入更多模型** | 当前 3 家 5 个模型，可考虑通义千问、文心一言、Kimi 等 |
| 7 | **Cost / Usage 统计** | 当前 cost 都设为 0（包月模式），可完善用量统计看板 |
| 8 | **Docker 化部署** | 目前是裸 venv 运行，可考虑容器化以简化部署 |
| 9 | **简化 Prisma 补丁逻辑** | 若 LiteLLM 后续版本修复了 Windows 兼容性，可移除 `start_proxy.py` 中的补丁代码 |

---

## 五、关键文件索引

| 文件 | 用途 |
|------|------|
| `model-platform/config.yaml` | LiteLLM 模型路由配置（5 个模型 + 重试/超时/master_key/database_url） |
| `model-platform/start_proxy.py` | Proxy 启动脚本（前台/后台/健康检查 + Prisma 补丁 + NO_PROXY） |
| `model-platform/create_keys.py` | 虚拟 Key 管理工具（generate/list/info/delete/update） |
| `model-platform/test_call.py` | 虚拟 Key 自动化测试（7 步流程） |
| `model-platform/test_glm.py` | 智谱 GLM-5.1 专项测试 |
| `model-platform/setup_litellm_db.py` | 数据库初始化脚本（本地 PostgreSQL 方式） |
| `model-platform/create_views.sql` | 8 个 LiteLLM 系统视图 SQL 定义 |
| `model-platform/proxy.out.log` | Proxy 启动日志（stdout） |
| `model-platform/proxy.err.log` | Proxy 启动日志（stderr，含迁移和错误信息） |
| `model-platform/model_readme.md` | 模型接入说明 |
| `model-platform/虚拟Key管理进度备忘.md` | Key 管理进度备忘 |
| `.env` | 项目统一环境变量（API Keys / DATABASE_URL / Langfuse） |

---

## 六、环境依赖清单

| 依赖 | 状态 | 说明 |
|------|------|------|
| Python 3.13 | 已安装 | 系统级 |
| LiteLLM venv | `C:\litellm-env\` | litellm==1.87.0, prisma==0.15.0 |
| PostgreSQL 15 | 运行中 | localhost:5432, 数据库 `litellm`（128 个迁移已应用） |
| Node.js v22.16.0 | 已安装 | `D:\Program Files\nodejs\` |
| Prisma CLI 7.8.0 | 已安装 | `D:\npm-global\prisma.cmd`（npm install -g prisma） |
| Prisma CLI 在 PATH | 否 | `D:\npm-global` 不在系统 PATH 中（`start_proxy.py` 已自动处理） |

---

## 七、核心环境变量（.env）

```env
# 模型 API Keys
MINIMAX_API_KEY=sk-cp-...
DEEPSEEK_API_KEY=sk-...
ZAI_API_KEY=...

# LiteLLM Proxy
LITELLM_MASTER_KEY=sk-my-master-key-1234
LITELLM_BASE_URL=http://localhost:4800
LITELLM_LOCAL_MODEL_COST_MAP=True

# LiteLLM PostgreSQL
DATABASE_URL=postgresql://litellm@localhost:5432/litellm
```

---

## 八、快速恢复路径

### 启动 LiteLLM Proxy

```powershell
cd d:\Desktop\Test\MultiModel\model-platform
py start_proxy.py              # 前台运行
py start_proxy.py --background # 后台运行
py start_proxy.py --health-check  # 前台 + 健康检查
```

### 验证 Proxy 正常

```powershell
# 查看 stdout 日志
type proxy.out.log

# 查看 stderr 日志（含迁移信息）
type proxy.err.log

# 健康检查
curl http://localhost:4800/health
```

### 虚拟 Key 管理

```powershell
py create_keys.py generate              # 生成预定义模板 Key
py create_keys.py list                  # 列出所有 Key
py create_keys.py info <key>            # 查询单个 Key
py create_keys.py update <key> --models ...  # 更新 Key
py create_keys.py delete <key> --yes    # 删除 Key
py test_call.py                         # 7 步自动化测试
```

---

## 九、VerificationTokenView 修复记录（已解决 ✅）

### 根因

PostgreSQL 中文 locale 产生的错误消息为 `关系 "LiteLLM_VerificationTokenView" 不存在`，而 LiteLLM 源码 `create_views.py` 的 `_VIEW_NOT_FOUND_MARKERS` 只包含英文标记（`"does not exist"`、`"no such table"`、`"undefined table"`），无法匹配中文 `"不存在"`，导致异常直接抛出而非触发视图创建逻辑。

### 修复方案

1. 从 LiteLLM 源码 `C:\litellm-env\Lib\site-packages\litellm\proxy\db\create_views.py` 提取全部 8 个视图的 CREATE VIEW SQL
2. 保存为 `model-platform/create_views.sql`
3. 通过 `pg15\pgsql\bin\psql.exe -f create_views.sql` 手动执行，成功创建全部 8 个视图
4. 重启 Proxy，确认 `proxy.err.log` 不再出现视图错误

### 创建的 8 个视图

1. `LiteLLM_VerificationTokenView`（核心：Key 验证依赖此视图）
2. `MonthlyGlobalSpend`
3. `Last30dKeysBySpend`
4. `Last30dModelsBySpend`
5. `MonthlyGlobalSpendPerKey`
6. `MonthlyGlobalSpendPerUserPerKey`
7. `DailyTagSpend`
8. `Last30dTopEndUsersSpend`
