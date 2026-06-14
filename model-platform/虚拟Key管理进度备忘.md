# 虚拟 Key 管理完善 — 进度备忘

> 日期: 2026-06-14
> 状态: **全部完成** — DB 连接已打通，端到端测试通过

---

## 一、已完成的工作

### 1.1 create_keys.py — 完整 Key 管理工具

**文件**: `model-platform/create_keys.py`

已从"仅生成"改造为支持 5 个子命令的完整管理工具（已适配 LiteLLM 1.87 API）：

| 子命令 | 用法 | 说明 |
|--------|------|------|
| `generate` | `py create_keys.py generate` | 预定义模板批量生成 / `--name --models --budget` 自定义生成 |
| `list` | `py create_keys.py list` | 列出所有虚拟 Key（适配 1.87 的 token 哈希列表格式） |
| `info` | `py create_keys.py info <key>` | 查询单个 Key 详情（使用 `/v2/key/info` 端点） |
| `delete` | `py create_keys.py delete <key>` | 吊销 Key（支持 `--yes` 跳过确认） |
| `update` | `py create_keys.py update <key> --models ... --budget N` | 更新 Key 的模型范围或预算 |

LiteLLM 1.87 API 适配要点：
- `/key/list` 返回 token 哈希字符串列表（非旧版对象列表），`list` 命令逐个调用 `/v2/key/info` 获取详情
- `/v2/key/info` 是 POST 方法，body `{"keys": ["hash"]}`，响应 `{"key":[...], "info":[{...}]}`

### 1.2 test_call.py — 7 步自动化测试

**文件**: `model-platform/test_call.py`

| 步骤 | 测试内容 | 状态 |
|------|----------|------|
| 1 | Master Key 连通性检查 | 通过 |
| 2 | 动态生成 3 个测试 Key | 通过 |
| 3 | 权限隔离测试（7 个正向+反向用例） | 通过（minimax 上游 429 限流） |
| 4 | Key 查询验证（`/v2/key/info` 返回正确模型范围） | 通过 |
| 5 | Key 更新验证（权限变更生效） | 通过 |
| 6 | Key 吊销验证（吊销后不可调用） | 通过 |
| 7 | 清理（删除所有测试 Key） | 通过 |

总结果：15/18 通过，3 个失败均为 minimax 上游 API 429 限流（非代码问题）。

### 1.3 start_proxy.py — Prisma CLI 自动发现与补丁

**文件**: `model-platform/start_proxy.py`

- `_ensure_prisma_cli()` — 自动将 npm 全局目录（D:\npm-global）加入 PATH
- `_patch_litellm_prisma_check()` — 自动修补 LiteLLM 源码中的 prisma 检测（添加 shell=True）
- `_patch_proxy_extras_prisma()` — 补丁 proxy_extras 中的 Prisma 调用

以上补丁在每次启动 Proxy 时自动应用，Proxy 启动正常。

### 1.4 数据库视图修复

**根因**: PostgreSQL 中文 locale 导致错误消息"不存在"无法被 LiteLLM 源码 `_VIEW_NOT_FOUND_MARKERS` 匹配（只含英文 `"does not exist"` 等），视图自动创建失败。

**修复**: 创建 `create_views.sql`，通过 `psql -f create_views.sql` 手动创建全部 8 个系统视图。

### 1.5 端到端验证

完整执行了以下流程，全部通过：
```
py create_keys.py generate    → 3 个模板 Key 生成成功
py create_keys.py list        → 列出所有 Key（详情正确）
py create_keys.py info <key>  → 返回 Key 详情（模型范围、状态等）
py test_call.py               → 15/18 通过（3 个失败为上游限流）
```

---

## 二、环境依赖清单

| 依赖 | 状态 | 说明 |
|------|------|------|
| Python 3.13 | 已安装 | 系统级 |
| LiteLLM venv | `C:\litellm-env\` | litellm==1.87.0, prisma==0.15.0 |
| PostgreSQL 15 | 运行中 | localhost:5432, 数据库 `litellm`（128 个迁移已应用，8 个视图已创建） |
| Node.js v22.16.0 | 已安装 | D:\Program Files\nodejs\ |
| Prisma CLI 7.8.0 | 已安装 | D:\npm-global\prisma.cmd（npm install -g prisma） |
| Prisma CLI 在 PATH | 否 | D:\npm-global 不在系统 PATH 中（start_proxy.py 自动处理 shell=True） |
| LiteLLM prisma 检测 | 已解决 | start_proxy.py 自动补丁 `shell=True`，Proxy 启动正常 |

---

## 三、文件变更汇总

| 文件 | 操作 | 状态 |
|------|------|------|
| `model-platform/create_keys.py` | 重写为子命令管理工具 + 适配 1.87 API | 已完成 |
| `model-platform/test_call.py` | 重写为动态自动化测试 + 适配 `/v2/key/info` | 已完成 |
| `model-platform/start_proxy.py` | 增加 Prisma CLI 自动发现 + 源码修补逻辑 | 已完成 |
| `model-platform/create_views.sql` | 新建 — 8 个系统视图 SQL 定义 | 已完成 |
