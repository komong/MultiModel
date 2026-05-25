---
id: kb-0005
title: Langfuse 启动与验证
category: 软件配置
tags: [Langfuse, Docker, WSL, 追踪平台, 启动]
platform: Windows
arch: x86_64
status: active
version: "2"
created_at: 2026-05-25
updated_at: 2026-05-25
author: Qoder
related: [kb-0001, kb-0003, kb-0004, kb-0006]
source: ""
---

# Langfuse 启动与验证

> 在 Windows WSL2 Docker 环境中启动 Langfuse v2 追踪平台，通过端口映射提供 Windows 侧访问。

## 环境信息

- **操作系统**：Windows 22H2 + WSL2 (Ubuntu)
- **硬件架构**：x86_64
- **依赖版本**：Docker (WSL2), Langfuse v2, PostgreSQL 15

## 正文内容

### 架构概览

```
Windows (localhost:3000) <--端口映射-- WSL2 Docker
                                          ├── langfuse-server (langfuse/langfuse:2, 端口 3000)
                                          └── langfuse-db     (postgres:15, 端口 5432)
```

- Langfuse 运行在 **WSL2 Docker** 中，不在 Windows 本地
- 通过 WSL2 端口自动映射，Windows 侧 `localhost:3000` 可访问
- 数据持久化通过 Docker Volume `langfuse_postgres`

### 相关文件

| 文件 | 路径 | 用途 |
|------|------|------|
| Docker Compose | `model-tracing/langfuse-docker-compose.yml` | 容器编排定义 |
| 启动脚本 (PS1) | `scripts/start_langfuse.ps1` | PowerShell 一键启动 |
| 启动脚本 (BAT) | `scripts/start_langfuse.bat` | CMD 批处理启动 |
| WSL 侧脚本 | `\\wsl.localhost\Ubuntu\tmp\start_langfuse.sh` | WSL 内部启动流程 |
| Docker 检查 | `scripts/check_docker.ps1` | 检查容器/镜像状态 |

### 启动前检查

**1. 确认 WSL 正在运行：**

```powershell
wsl -l -v
# 预期输出：Ubuntu  Running  2
```

如果 WSL 未运行，先启动：
```powershell
wsl -d Ubuntu -- bash -c ""
```

**2. 确认端口 3000 未被其他程序占用：**

```powershell
netstat -ano | findstr :3000
# 如果被 svchost.exe 占用，是 WSL 的端口转发代理，正常
# 如果被其他程序占用，需先停止该程序
```

### 启动步骤

**方式一：使用启动脚本（推荐）**

在**独立 PowerShell 窗口**（非 IDE 内嵌终端）中执行：

```powershell
powershell -ExecutionPolicy Bypass -File "d:\Desktop\Test\MultiModel\scripts\start_langfuse.ps1"
```

脚本会自动完成：复制 docker-compose 到 WSL → 启动 Docker → pull 镜像 → docker compose up -d → 显示状态

**方式二：手动启动**

```powershell
# 1. 复制 docker-compose 到 WSL
Copy-Item "d:\Desktop\Test\MultiModel\model-tracing\langfuse-docker-compose.yml" "\\wsl.localhost\Ubuntu\tmp\" -Force

# 2. 在独立 PowerShell 窗口中执行
chcp 65001
wsl -d Ubuntu -- bash -c "sudo service docker start; sleep 3; cd /tmp; docker compose -f langfuse-docker-compose.yml pull; docker compose -f langfuse-docker-compose.yml up -d"
```

**方式三：直接进入 WSL 操作**

```powershell
# 打开 WSL 终端
wsl -d Ubuntu

# 在 WSL 内执行
cd /tmp
sudo service docker start
docker compose -f langfuse-docker-compose.yml pull
docker compose -f langfuse-docker-compose.yml up -d
```

### 验证

```powershell
# 检查端口监听
netstat -ano | findstr :3000

# 浏览器访问
# http://localhost:3000

# HTTP 验证（PowerShell）
(Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 10).StatusCode
# 预期输出：200
```

### 停止服务

```powershell
# 在独立 PowerShell 窗口或 WSL 终端中执行
wsl -d Ubuntu -- bash -c "cd /tmp; docker compose -f langfuse-docker-compose.yml down"
```

### 状态检查

```powershell
# 在独立 PowerShell 窗口中查看容器状态
chcp 65001
wsl -d Ubuntu -- bash -c "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
```

正常状态下应看到两个容器：
- `langfuse-server` - 状态 `Up`, 端口 `0.0.0.0:3000->3000/tcp`
- `langfuse-db` - 状态 `Up (healthy)`

---

## 常见问题

**Q：IDE 内嵌终端执行 WSL 命令报 WSL_E_CONSOLE？**
A：IDE 终端不支持 WSL 交互式命令。必须在独立 PowerShell 窗口或 WSL 终端中执行。详见 [[kb-0006]]。

**Q：启动脚本报中文乱码？**
A：执行前先运行 `chcp 65001` 切换到 UTF-8 编码。详见 [[kb-0006]]。

**Q：端口 3000 被占用？**
A：用 `netstat -ano | findstr :3000` 检查。如果被 svchost.exe 占用且 HTTP 请求超时，说明有旧容器残留，需先清理。详见 [[kb-0006]]。

**Q：镜像版本用哪个？**
A：必须使用 `langfuse/langfuse:2`（v2）。v3/latest 需要 ClickHouse 等额外依赖，本地部署不支持。

---

## 相关词条

- [[kb-0001]] LiteLLM Proxy 启动与验证
- [[kb-0003]] PowerShell 常用命令
- [[kb-0004]] Windows 端口管理
- [[kb-0006]] Langfuse 启动排障指南

## 变更记录

| 日期 | 变更内容 | 作者 |
|---|---|---|
| 2026-05-25 | 创建 | Qoder |
