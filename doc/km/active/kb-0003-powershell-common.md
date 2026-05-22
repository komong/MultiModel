---
id: kb-0003
title: PowerShell 常用命令
category: 开发工具
tags: [PowerShell, Windows, 命令行]
platform: Windows
arch: x86_64
status: active
version: ""
created_at: 2026-05-21
updated_at: 2026-05-21
author: Qoder
related: [kb-0004]
source: ""
---

# PowerShell 常用命令

> Windows PowerShell 与 CMD/Bash 的主要差异及常用命令备忘。

## 环境信息

- **操作系统**：Windows 10/11
- **硬件架构**：x86_64
- **依赖版本**：PowerShell 5.1+

## 正文内容

### 与 CMD/Bash 的主要差异

| 功能 | CMD | Bash | PowerShell |
|------|-----|------|------------|
| 命令分隔符 | `&` | `&&` | `;` |
| 变量赋值 | `%var%` | `$var` | `$var` |
| 输出重定向 | `>` | `>` | `>` |
| 追加重定向 | `>>` | `>>` | `>>` |
| 管道 | `\|` | `\|` | `\|` |
| 列表进程 | `tasklist` | `ps` | `Get-Process` |
| 结束进程 | `taskkill /PID x /F` | `kill x` | `Stop-Process -Id x` |
| 复制文件 | `copy src dst` | `cp src dst` | `Copy-Item src dst` |

### 网络命令

```powershell
# 检查端口占用
netstat -ano | findstr :8080

# 查看端口排除范围（需管理员）
netsh interface ipv4 show excludedportrange protocol=tcp

# 设置端口转发（需管理员）
netsh interface portproxy add v4tov4 listenport=3000 listenaddress=127.0.0.1 connectport=3000 connectaddress=172.x.x.x
```

### 进程管理

```powershell
# 查找进程
Get-Process -Name python

# 按命令行查找
Get-Process -Name python | Where-Object { $_.CommandLine -like "*start_proxy*" }

# 结束进程
Stop-Process -Id 12345 -Force
Stop-Process -Name python -Force

# 后台启动
Start-Process -FilePath python -ArgumentList "start_proxy.py" -WindowStyle Hidden
```

### 文件操作

```powershell
# 复制文件
Copy-Item -Path "src.txt" -Destination "dst.txt"

# 创建目录
New-Item -ItemType Directory -Path "test_dir"

# 查看文件内容
Get-Content -Path "file.txt" -Wait -Tail 20
```

### HTTP 请求

```powershell
# GET 请求（注意：PowerShell 的 curl 是 Invoke-WebRequest 别名）
Invoke-RestMethod -Uri "http://localhost:8080/api" -Method GET

# POST 请求带 Header
Invoke-RestMethod -Uri "http://localhost:8080/api" -Method POST -Headers @{"Authorization"="Bearer xxx"} -Body '{}'
```

### Python 虚拟环境

```powershell
# 创建虚拟环境
python -m venv venv

# 激活
.\venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt
```

---

## 常见问题

**Q：curl 命令报错？**
A：PowerShell 的 `curl` 是 `Invoke-WebRequest` 别名，参数语法不同。请使用 `Invoke-RestMethod`。

**Q：复制文件用 `copy` 报错？**
A：PowerShell 用 `Copy-Item`，CMD 的 `copy` 在 PowerShell 中不可用。

**Q：命令分隔符用 `&&` 报错？**
A：PowerShell 不支持 `&&`，用 `;` 分隔多个命令，或换行。

---

## 相关词条

- [[kb-0004]] Windows 端口管理

## 变更记录

| 日期 | 变更内容 | 作者 |
|---|---|---|
| 2026-05-21 | 创建 | Qoder |
