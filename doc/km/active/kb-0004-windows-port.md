---
id: kb-0004
title: Windows 端口管理
category: 软件配置
tags: [Windows, 端口, netstat, Hyper-V]
platform: Windows
arch: x86_64
status: active
version: ""
created_at: 2026-05-21
updated_at: 2026-05-21
author: Qoder
related: [kb-0001, kb-0003]
source: ""
---

# Windows 端口管理

> Windows 系统中端口占用检查、端口排除范围及端口转发配置。

## 环境信息

- **操作系统**：Windows 10/11
- **硬件架构**：x86_64
- **依赖版本**：PowerShell 5.1+

## 正文内容

### 检查端口占用

```powershell
# 检查特定端口是否被占用
netstat -ano | findstr :4800

# 检查端口监听状态
netstat -ano | findstr "LISTENING"

# 查找所有 Python 进程占用的端口
netstat -ano | findstr python
```

### 查看端口排除范围

Windows Hyper-V 会保留一段端口范围（通常是 10000-65535），以下端口可能无法使用：

```powershell
# 查看被排除的端口范围（需管理员）
netsh interface ipv4 show excludedportrange protocol=tcp
```

常见被排除的端口：80, 443, 8000-9000 等。

### 端口转发（WSL）

```powershell
# 添加端口转发（需管理员）
netsh interface portproxy add v4tov4 listenport=3000 listenaddress=127.0.0.1 connectport=3000 connectaddress=172.x.x.x

# 查看现有转发规则
netsh interface portproxy show all

# 删除转发规则
netsh interface portproxy delete v4tov4 listenport=3000 listenaddress=127.0.0.1
```

### 终止占用端口的进程

```powershell
# 方法1：通过 netstat 找到 PID 后终止
$pid = (netstat -ano | findstr :4800 | Select-String "LISTENING" | ForEach-Object { ($_ -split '\s+')[-1] })
if ($pid) { Stop-Process -Id $pid -Force }

# 方法2：直接用 taskkill
taskkill /PID 12345 /F
taskkill /IM python.exe /F
```

### 选择可用端口

建议使用 **4800** 或其他避开常见排除范围的端口。

常见端口参考：
| 端口 | 用途 |
|------|------|
| 3000 | Langfuse |
| 4000 | 旧版 LiteLLM |
| 4800 | 当前 LiteLLM |
| 8000 | FastAPI 默认 |
| 8080 | HTTP 代理 |

---

## 常见问题

**Q：端口绑定失败 `OSError: [WinError 10048]`？**
A：端口被占用。用 `netstat -ano | findstr :端口` 查找占用进程，或使用其他端口。

**Q：端口被 Hyper-V 排除？**
A：用 `netsh interface ipv4 show excludedportrange` 查看排除范围，选择不在范围内的端口。

**Q：netsh 命令报错需要权限？**
A：需要以管理员身份运行 PowerShell。

---

## 相关词条

- [[kb-0001]] LiteLLM Proxy 启动与验证
- [[kb-0003]] PowerShell 常用命令

## 变更记录

| 日期 | 变更内容 | 作者 |
|---|---|---|
| 2026-05-21 | 创建 | Qoder |
