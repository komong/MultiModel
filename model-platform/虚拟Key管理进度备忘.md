# 虚拟 Key 管理完善 — 进度备忘

> 日期: 2026-06-06
> 状态: **代码改造完成，端到端测试被 DB 连接问题阻塞**

---

## 一、已完成的工作

### 1.1 create_keys.py 重写为完整 Key 管理工具

**文件**: `model-platform/create_keys.py`

已从"仅生成"改造为支持 5 个子命令的完整管理工具：

| 子命令 | 用法 | 说明 |
|--------|------|------|
| `generate` | `py create_keys.py generate` | 预定义模板批量生成 / `--name --models --budget` 自定义生成 |
| `list` | `py create_keys.py list` | 列出所有虚拟 Key |
| `info` | `py create_keys.py info <key>` | 查询单个 Key 详情（用量、过期、模型范围） |
| `delete` | `py create_keys.py delete <key>` | 吊销 Key（支持 `--yes` 跳过确认） |
| `update` | `py create_keys.py update <key> --models ... --budget N` | 更新 Key 的模型范围或预算 |

代码特点：
- 使用 `argparse` 子命令模式
- 所有子命令共享 Proxy 连通性前置检查
- 输出统一中文
- 预定义 3 个模板：system-a(MiniMax/$10)、system-b(DeepSeek/$20)、system-c(全模型)

### 1.2 test_call.py 重写为动态 Key 自动化测试

**文件**: `model-platform/test_call.py`

已从"硬编码 Key 手动测试"改造为 7 步自动化测试：

| 步骤 | 测试内容 |
|------|----------|
| 1 | Master Key 连通性检查 |
| 2 | 动态生成 3 个测试 Key |
| 3 | 权限隔离测试（7 个正向+反向用例） |
| 4 | Key 查询验证（info 返回正确模型范围） |
| 5 | Key 更新验证（权限变更生效） |
| 6 | Key 吊销验证（吊销后不可调用） |
| 7 | 清理（删除所有测试 Key） |

代码特点：
- 运行时动态生成 Key，无硬编码
- 测试结束自动清理
- 统计汇总（passed/failed/total），exit code 反映结果
- 中文输出

### 1.3 start_proxy.py 增加了 Prisma CLI 自动发现

**文件**: `model-platform/start_proxy.py`

新增两个函数：
- `_ensure_prisma_cli()` — 自动将 npm 全局目录（D:\npm-global）加入 PATH
- `_patch_litellm_prisma_check()` — 自动修补 LiteLLM 源码中的 prisma 检测（添加 shell=True）

同时删除了旧的 `os.environ.pop('DATABASE_URL', None)` 代码，不再主动移除数据库连接字符串。

---

## 二、未完成的工作（阻塞项）

### 2.1 核心阻塞：LiteLLM Proxy 无法连接 PostgreSQL

**现象**: 启动时输出 `Unable to connect to DB. DATABASE_URL found in environment, but prisma package not found.`

**根因分析**:

```
LiteLLM 源码 (proxy_cli.py 第 1110 行):
    subprocess.run(["prisma"], capture_output=True)

问题链:
1. litellm.exe 是 PyInstaller 编译的独立二进制文件
2. 它不使用 venv 中 pip 安装的 prisma Python 包
3. 而是通过 subprocess.run(["prisma"]) 调用系统 PATH 中的 prisma CLI
4. prisma CLI 需要通过 npm install -g prisma 安装
5. 已安装到 D:\npm-global\prisma.cmd
6. 但 Windows 上 subprocess.run 默认只找 .exe 文件，不找 .cmd 文件
7. 因此 FileNotFoundError → is_prisma_runnable = False → DB not connected
```

**解决方案**（优先级从高到低）：

#### 方案 A：手动修补 LiteLLM 源码（最直接）

```bash
# 用编辑器打开此文件
C:\litellm-env\Lib\site-packages\litellm\proxy\proxy_cli.py

# 找到第 1110 行，修改：
# 原：
subprocess.run(["prisma"], capture_output=True)
# 改为：
subprocess.run(["prisma"], capture_output=True, shell=True)

# 保存后重启 Proxy
```

注意：IDE 沙箱无法写入 venv 目录，需在 IDE 外手动编辑此文件。

#### 方案 B：在 PATH 中创建 prisma.exe 代理

在 `D:\npm-global\` 目录创建一个名为 `prisma.exe` 的可执行包装器，调用 `prisma.cmd`。可使用以下方法之一：
- 用 Python + PyInstaller 编译一个小的 .exe 包装器
- 用 Go/C 编译一个小程序
- 使用 `prisma` npm 包自带的 schema-engine-windows.exe 做符号链接（不推荐）

#### 方案 C：回退到不依赖数据库的 Proxy 模式

移除 config.yaml 中的 `database_url`，Proxy 以无数据库模式运行。但这样虚拟 Key 功能完全不可用，本任务无法完成。

#### 方案 D：升级 LiteLLM 或提交 Issue

检查 LiteLLM 新版本是否修复了 Windows 上 subprocess + .cmd 的兼容性问题，或向官方提交 Issue。

### 2.2 端到端测试（被 2.1 阻塞）

修复 DB 连接后，需执行以下测试步骤：

```bash
# 1. 启动 Proxy（DB 应已连接成功）
cd model-platform
py start_proxy.py --port 4800 --background

# 2. 验证 Proxy + DB 连接正常
#    查看日志不应有 "prisma package not found"
type proxy.out.log

# 3. 测试 Key 生成
py create_keys.py generate

# 4. 测试 Key 列表
py create_keys.py list

# 5. 测试全流程自动化测试
py test_call.py

# 6. 测试单个 Key 查询
py create_keys.py info <key>

# 7. 测试 Key 吊销
py create_keys.py delete <key> --yes
```

---

## 三、环境依赖清单

| 依赖 | 状态 | 说明 |
|------|------|------|
| Python 3.13 | 已安装 | 系统级 |
| LiteLLM venv | `C:\litellm-env\` | litellm==1.87.0, prisma==0.15.0 |
| PostgreSQL 15 | 运行中 | localhost:5432, 数据库 `litellm`（64 张表已存在） |
| Node.js v22.16.0 | 已安装 | D:\Program Files\nodejs\ |
| Prisma CLI 7.8.0 | 已安装 | D:\npm-global\prisma.cmd（npm install -g prisma） |
| Prisma CLI 在 PATH | 否 | D:\npm-global 不在系统 PATH 中（start_proxy.py 已自动处理） |
| LiteLLM prisma 检测 | 失败 | subprocess.run 找不到 .cmd 文件，需手动修补（见 2.1 方案 A） |

---

## 四、文件变更汇总

| 文件 | 操作 | 状态 |
|------|------|------|
| `model-platform/create_keys.py` | 重写为子命令管理工具 | 已完成，语法检查通过 |
| `model-platform/test_call.py` | 重写为动态自动化测试 | 已完成，语法检查通过 |
| `model-platform/start_proxy.py` | 增加 Prisma CLI 自动发现 + 源码修补逻辑 | 已完成，语法检查通过 |

无其他文件变更。不涉及 model-tracing、model-eval、.env 等文件的修改。

---

## 五、记忆更新建议

完成本任务后，建议更新以下记忆：

1. **新增经验**: LiteLLM Proxy 在 Windows 上因 subprocess.run 找不到 .cmd 文件导致 DB 连接失败的修复方案
2. **更新记忆**: LiteLLM启动报prisma包缺失需手动安装 — 补充 npm install -g prisma + 手动修补 shell=True 的步骤
3. **更新记忆**: 项目服务启动命令 — start_proxy.py 已增加 Prisma CLI 自动发现逻辑

---

## 六、快速恢复命令

```bash
# 若已完成方案 A（手动修补 proxy_cli.py），直接：
cd d:\Desktop\Test\MultiModel\model-platform
py start_proxy.py --port 4800 --background

# 等 15 秒后测试
py create_keys.py generate
py test_call.py

# 查看日志
type proxy.out.log
type proxy.err.log
```
