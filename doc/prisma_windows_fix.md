# LiteLLM Prisma Windows 兼容性问题修复全记录

> **日期**: 2026-06-13
> **涉及模块**: `model-platform`
> **问题级别**: 阻断级（Proxy 无法启动）
> **最终状态**: 已修复并验证通过

---

## 一、问题现象

启动 LiteLLM Proxy 时，日志 `proxy.err.log` 中出现如下崩溃：

```
FileNotFoundError: [WinError 2] 系统找不到指定的文件。
  File "...\litellm_proxy_extras\utils.py", line 712
    subprocess.run([_get_prisma_command(), "migrate", "deploy"], ...)
```

Proxy 完全无法连接 PostgreSQL 数据库，128 个数据库迁移全部未执行，服务无法启动。

---

## 二、根因分析

### 2.1 为什么 Windows 上 prisma CLI 无法执行？

Windows 上 `npm install -g prisma` 安装的是 `prisma.cmd`（批处理脚本），而非 `.exe` 可执行文件。Python 的 `subprocess.run` 底层调用 Windows `CreateProcess` API，该 API **只能直接执行 `.exe` 文件**，不识别 `.cmd`。

在 Linux 上不存在此问题，因为 npm 在 Linux 上安装的是具有可执行权限的 shell 脚本。

### 2.2 为什么之前的补丁不够？

LiteLLM 版本演进导致 prisma 调用位置发生了变化：

| LiteLLM 版本 | prisma 调用位置 | 补丁状态 |
|---|---|---|
| < 1.87 | `litellm/proxy/proxy_cli.py` | 已有 `shell=True` 补丁 |
| >= 1.87 | `litellm_proxy_extras/utils.py`（新模块） | **无补丁** ← 问题根源 |

项目原有的 `_patch_litellm_prisma_check()` 函数只修补了 `proxy_cli.py`，但新版 LiteLLM 已将 prisma 调用迁移到了 `litellm_proxy_extras/utils.py`（13+ 处 `subprocess.run` 调用），这些调用全部缺少 `shell=True`。

### 2.3 为什么不能简单加 `shell=True`？

第一版补丁（v1）尝试简单注入 `shell=True`，但引发了新问题：

```
'pool_timeout' 不是内部或外部命令
```

原因：`DATABASE_URL` 中包含 `connection_limit=10&pool_timeout=60`，当 `shell=True` 时，Python 的 `subprocess.run` 会将命令列表拼接成字符串交给 `cmd.exe` 执行。cmd.exe 将 `&` 解释为**命令分隔符**，导致 `pool_timeout=60` 被当作独立的 shell 命令执行。

涉及的特殊字符集：`&` `|` `<` `>` `(` `)` `^`

---

## 三、最终解决方案（v2 补丁）

### 3.1 核心思路

采用 **monkey-patch** 技术，在运行时替换 `litellm_proxy_extras/utils.py` 模块中的 `subprocess.run`：

1. **精准拦截**：仅对 `prisma` / `prisma.cmd` 开头的命令生效，不影响其他 subprocess 调用
2. **智能引号**：对含 cmd.exe 特殊字符的参数自动加双引号，避免 `&` 被误解释
3. **自动升级**：通过 marker 标记自动检测并升级旧补丁，幂等可重复执行

### 3.2 涉及的三层补丁

`start_proxy.py` 中的 `_ensure_prisma_cli()` 函数依次调用三个修补：

```
_ensure_prisma_cli()
  ├── PATH 修复：将 npm 全局目录加入 PATH
  ├── _patch_litellm_prisma_check()     ← 修补 proxy_cli.py (旧版 LiteLLM)
  │     ├── proxy_cli.py: 加 shell=True
  │     └── utils.py: _get_prisma_command() 返回 "prisma.cmd"
  └── _patch_proxy_extras_prisma()       ← 修补 utils.py (新版 LiteLLM v1.87+)
        └── 注入 subprocess.run 包装器
```

### 3.3 v2 补丁注入的代码

`_patch_proxy_extras_prisma()` 向 `litellm_proxy_extras/utils.py` 的 import 区域后注入以下代码：

```python
# --- Windows prisma.cmd compatibility patch v2 ---
import sys as _patch_sys
if _patch_sys.platform == "win32":
    _patch_orig_run = subprocess.run
    def _patch_prisma_run(*args, **kwargs):
        _cmd = args[0] if args else kwargs.get("args")
        if isinstance(_cmd, list) and _cmd and _cmd[0] in ("prisma", "prisma.cmd"):
            _special = set(" &|<>()^")
            _parts = []
            for _arg in _cmd:
                if any(_c in _arg for _c in _special):
                    _parts.append(chr(34) + _arg + chr(34))
                else:
                    _parts.append(_arg)
            if args:
                args = (" ".join(_parts),) + args[1:]
            else:
                kwargs["args"] = " ".join(_parts)
            kwargs["shell"] = True
        return _patch_orig_run(*args, **kwargs)
    subprocess.run = _patch_prisma_run
# --- End patch ---
```

### 3.4 工作流程图

```
Proxy 启动
  │
  ├─ start_proxy.py 执行
  │   ├─ _ensure_prisma_cli()
  │   │   ├─ PATH 修复
  │   │   ├─ _patch_litellm_prisma_check()  → 修补 proxy_cli.py
  │   │   └─ _patch_proxy_extras_prisma()   → 注入 v2 包装器到 utils.py
  │   │
  │   └─ 启动 litellm.exe
  │       │
  │       └─ utils.py 加载，v2 包装器生效
  │           │
  │           ├─ prisma migrate deploy  → shell=True + 引号 → 成功
  │           ├─ prisma migrate resolve → shell=True + 引号 → 成功
  │           ├─ ... (128 个迁移)
  │           └─ Proxy 正常监听 :4800
  │
  └─ /health 返回 200 ✓
```

---

## 四、关键文件清单

| 文件 | 作用 |
|---|---|
| `model-platform/start_proxy.py` | 启动脚本，包含全部三层补丁逻辑 |
| `model-platform/start_proxy.py` → `_ensure_prisma_cli()` | 补丁入口（第 123-165 行） |
| `model-platform/start_proxy.py` → `_patch_litellm_prisma_check()` | 旧版补丁：proxy_cli.py + _get_prisma_command（第 168-215 行） |
| `model-platform/start_proxy.py` → `_patch_proxy_extras_prisma()` | v2 补丁：注入 subprocess.run 包装器（第 218-305 行） |
| `C:\litellm-env\Lib\site-packages\litellm_proxy_extras\utils.py` | 被修补的目标文件（运行时自动写入） |
| `C:\litellm-env\Lib\site-packages\litellm\proxy\proxy_cli.py` | 被修补的旧位置（已由第一层补丁处理） |

---

## 五、验证结果

修复后 Proxy 启动日志（`proxy.out.log`）：

```
[INFO] 已将 Prisma CLI 加入 PATH: D:\npm-global
[INFO] 已修补 proxy_cli.py prisma 检测 (shell=True)
[INFO] 已修补 litellm_proxy_extras/utils.py _get_prisma_command (prisma.cmd)
[INFO] 已修补 litellm_proxy_extras prisma CLI (Windows shell=True + arg quoting)
[INFO] litellm 路径: C:\litellm-env\Scripts\litellm.exe
[INFO] 配置文件:   d:\Desktop\Test\MultiModel\model-platform\config.yaml
[INFO] 监听端口:   4800
```

Prisma 迁移结果：**128 个迁移全部成功 resolve**

健康检查：`GET http://localhost:4800/health` 返回 **200 OK**

---

## 六、经验总结

### 6.1 Windows + Python subprocess 的坑

| 问题 | 原因 | 解法 |
|---|---|---|
| `.cmd` 文件无法执行 | `CreateProcess` 只认 `.exe` | 加 `shell=True` 让 cmd.exe 解析 |
| `shell=True` 后 `&` 被截断 | cmd.exe 将 `&` 当命令分隔符 | 对含特殊字符的参数加双引号 |
| 补丁失效 | LiteLLM 版本升级迁移了调用位置 | 跟踪新模块 `litellm_proxy_extras` |

### 6.2 设计原则

- **幂等性**：补丁通过 marker 标记检测，重复执行不会重复注入
- **版本兼容**：支持自动从 v1 升级到 v2（清除旧补丁再注入新补丁）
- **最小影响面**：包装器仅对 prisma 命令生效，不干扰其他 subprocess 调用
- **跨平台**：通过 `sys.platform` 判断，Linux 上自动跳过

### 6.3 如果未来 LiteLLM 再次迁移代码

1. 在 `proxy.err.log` 中搜索 `FileNotFoundError` 或 `[WinError 2]`
2. 确认崩溃文件路径（可能不再是 `utils.py`）
3. 在 `start_proxy.py` 中新增对应的 `_patch_xxx()` 函数
4. 在 `_ensure_prisma_cli()` 中添加调用

---

## 七、已知遗留问题（非阻断）

日志中可能出现如下警告，与 prisma CLI 兼容性无关，不影响 Proxy 运行：

```
LiteLLM_VerificationTokenView 不存在
```

这是数据库视图层面的历史遗留问题，不影响核心代理功能。
