---
id: kb-0006
title: Langfuse 启动排障指南
category: 故障排查
tags: [Langfuse, Docker, WSL, 排障, 故障排查]
platform: Windows
arch: x86_64
status: active
version: "2"
created_at: 2026-05-25
updated_at: 2026-05-25
author: Qoder
related: [kb-0005, kb-0003, kb-0004]
source: ""
---

# Langfuse 启动排障指南

> Langfuse 在 WSL2 Docker 环境中启动时常见问题的诊断与解决方案汇总。

## 环境信息

- **操作系统**：Windows 22H2 + WSL2 (Ubuntu)
- **硬件架构**：x86_64
- **依赖版本**：Docker (WSL2), Langfuse v2, PostgreSQL 15

---

## 问题 1：IDE 内嵌终端报 WSL_E_CONSOLE

### 问题现象

在 IDE（如 Qoder）内嵌终端中执行 `wsl -d Ubuntu` 相关命令，报错：

```
错误: Wsl/Service/WSL_E_CONSOLE
```

### 原因分析

IDE 内嵌终端是伪终端（pseudo-console），WSL2 检测到终端类型不兼容，拒绝交互式操作。这是 WSL2 的已知限制。

### 解决方案

**方案一（推荐）：使用独立 PowerShell 窗口**

打开 Windows 开始菜单 → 搜索 "PowerShell" → 打开新窗口 → 执行命令

**方案二：使用 WSL 专属终端**

打开 Windows Terminal → 新建 WSL 标签页 → 直接操作

**方案三：通过 WSL 文件系统间接操作**

IDE 终端虽不能执行 WSL 命令，但可以通过 `\\wsl.localhost\Ubuntu\` 路径读写 WSL 文件系统：

```powershell
# 读取 WSL 中的日志
Get-Content "\\wsl.localhost\Ubuntu\tmp\startup.log"

# 复制文件到 WSL
Copy-Item "file.txt" "\\wsl.localhost\Ubuntu\tmp\" -Force
```

### 预防措施

- 所有涉及 `wsl` 的操作，统一在独立 PowerShell 窗口或 WSL 终端中执行
- IDE 终端仅用于 Windows 本地操作（如 `netstat`、Python 脚本等）

---

## 问题 2：PowerShell 中 WSL 输出中文乱码

### 问题现象

在 PowerShell 中执行 `wsl -d Ubuntu -- bash -c "..."` 后，输出内容出现乱码（如 `N譙/e` 等不可读字符）。

### 原因分析

PowerShell 默认使用 GBK 编码（代码页 936），而 WSL/Linux 输出使用 UTF-8 编码，编码不匹配导致乱码。

### 解决方案

```powershell
# 在执行 WSL 命令前，先切换代码页
chcp 65001

# 然后再执行 WSL 命令
wsl -d Ubuntu -- bash -c "docker ps -a"
```

或者一行完成：

```powershell
chcp 65001; wsl -d Ubuntu -- bash -c "docker ps -a"
```

### 预防措施

- 所有包含 WSL 调用的脚本，开头加 `chcp 65001`
- 启动脚本 `start_langfuse.ps1` 中建议加入此行

---

## 问题 3：端口 3000 被占用但 HTTP 超时

### 问题现象

```
netstat -ano | findstr :3000
# TCP  127.0.0.1:3000  0.0.0.0:0  LISTENING  10264 (svchost.exe)

Invoke-WebRequest http://localhost:3000  # 超时
```

端口被 `svchost.exe` 监听，但访问超时，Langfuse 不可用。

### 原因分析

可能有以下几种原因：
1. **旧容器残留**：之前启动的 Docker 容器未正确停止，WSL 端口转发仍在但容器已退出
2. **Docker 服务未运行**：Docker daemon 停了，但端口转发代理（Hyper-V/WSL relay）还占着端口
3. **镜像版本错误**：使用了 `langfuse:latest`（v3），需要 ClickHouse 等额外服务，容器启动后立即退出

### 解决方案

**步骤 1：清理旧容器**

在独立 PowerShell 窗口中执行：

```powershell
chcp 65001
wsl -d Ubuntu -- bash -c "cd /tmp; docker compose -f langfuse-docker-compose.yml down; docker ps -aq | xargs -r docker stop; docker ps -aq | xargs -r docker rm"
```

**步骤 2：确认 docker-compose 使用正确镜像**

检查 `model-tracing/langfuse-docker-compose.yml`，确保镜像为 `langfuse/langfuse:2`：

```yaml
services:
  langfuse-server:
    image: langfuse/langfuse:2    # 必须是 :2，不要用 :latest 或 :3
```

**步骤 3：重新启动**

```powershell
wsl -d Ubuntu -- bash -c "cd /tmp; sudo service docker start; sleep 3; docker compose -f langfuse-docker-compose.yml pull; docker compose -f langfuse-docker-compose.yml up -d"
```

**步骤 4：验证**

```powershell
wsl -d Ubuntu -- bash -c "docker compose -f /tmp/langfuse-docker-compose.yml ps"
# 确认两个容器都是 Up 状态
```

### 预防措施

- 始终使用 `langfuse/langfuse:2`，不要升级到 v3/latest
- 停止服务时用 `docker compose down` 而非直接关闭 WSL

---

## 问题 4：Docker daemon 未运行

### 问题现象

```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

### 原因分析

WSL2 中 Docker 服务需要手动启动（除非配置了 systemd 自动启动）。

### 解决方案

```powershell
# 在 WSL 中启动 Docker 服务
wsl -d Ubuntu -- bash -c "sudo service docker start"
```

如果报权限问题，确保 WSL 用户在 docker 组中：

```bash
sudo usermod -aG docker $USER
# 需要重新登录 WSL 生效
```

### 预防措施

- 启动脚本中已包含自动启动 Docker 的逻辑
- 可考虑配置 WSL 的 `/etc/wsl.conf` 启用 systemd，实现 Docker 开机自启

---

## 问题 5：镜像拉取超时/失败

### 问题现象

```
ERROR: failed to do request: Head "https://registry-1.docker.io/v2/...": dial tcp: lookup registry-1.docker.io
```

### 原因分析

WSL2 中 DNS 解析失败或 Docker Hub 网络不通（国内常见）。

### 解决方案

**步骤 1：修复 DNS**

```bash
# 在 WSL 中执行
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
echo "nameserver 114.114.114.114" | sudo tee -a /etc/resolv.conf
```

**步骤 2：配置国内镜像源**

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
EOF
sudo service docker restart
```

**步骤 3：重新拉取**

```bash
cd /tmp
docker compose -f langfuse-docker-compose.yml pull
```

### 预防措施

- WSL 重启后 `/etc/resolv.conf` 可能被重置，需要配合 `/etc/wsl.conf` 固定 DNS 配置
- 镜像源地址可能失效，需要定期更新

---

## 问题 6：Langfuse server 容器启动后立即退出 (Exited 1)

### 问题现象

```
docker compose ps
# langfuse-server   Exited (1)
# langfuse-db       Up (healthy)
```

### 原因分析

查看容器日志确定具体原因：

```bash
docker logs langfuse-server-1 2>&1 | tail -30
```

常见原因：
1. **镜像版本错误**：使用了 `langfuse:latest`（v3），缺少 ClickHouse 配置
2. **数据库连接失败**：`langfuse-db` 尚未就绪（healthcheck 未通过）

### 解决方案

**如果是镜像版本问题：**

修改 `langfuse-docker-compose.yml`，将镜像改为 `langfuse/langfuse:2`，然后重新启动。

**如果是数据库未就绪：**

等待几秒后重启 server 容器：

```bash
docker compose -f langfuse-docker-compose.yml restart langfuse-server
```

docker-compose 中已配置 `depends_on` + `healthcheck`，正常情况下会等待数据库就绪。

### 预防措施

- 始终使用 `langfuse/langfuse:2` 镜像
- 启动后等待 10-15 秒再验证，给 healthcheck 留足时间

---

## 问题 7：Windows 无法访问 WSL 中的 Langfuse

### 问题现象

WSL 中容器正常运行，但 Windows 侧 `localhost:3000` 无法访问。

### 原因分析

WSL2 的端口自动转发可能未生效，或 Windows 防火墙阻止了连接。

### 解决方案

**方案一：检查 WSL IP 并手动设置端口转发**

```powershell
# 获取 WSL IP
$wslIp = (wsl -d Ubuntu -- bash -c "hostname -I").Trim()

# 添加端口转发（需管理员 PowerShell）
netsh interface portproxy add v4tov4 listenport=3000 listenaddress=127.0.0.1 connectport=3000 connectaddress=$wslIp

# 验证
netsh interface portproxy show all
```

**方案二：检查防火墙**

```powershell
# 临时允许 3000 端口（需管理员）
New-NetFirewallRule -DisplayName "Langfuse" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow
```

### 预防措施

- WSL2 默认支持 localhost 端口转发，通常无需手动配置
- 如果频繁失效，考虑在启动脚本中加入端口转发命令

---

## 诊断命令速查

遇到问题时，按以下顺序排查：

```powershell
# 1. WSL 状态
wsl -l -v

# 2. 端口占用
netstat -ano | findstr :3000

# 3. 容器状态（独立 PowerShell 窗口）
chcp 65001; wsl -d Ubuntu -- bash -c "docker ps -a"

# 4. 容器日志（独立 PowerShell 窗口）
chcp 65001; wsl -d Ubuntu -- bash -c "docker logs langfuse-server-1 2>&1 | tail -30"

# 5. Docker 服务状态（独立 PowerShell 窗口）
chcp 65001; wsl -d Ubuntu -- bash -c "sudo service docker status"

# 6. WSL 文件系统日志（IDE 终端也可用）
Get-Content "\\wsl.localhost\Ubuntu\tmp\startup.log"
```

---

## 相关词条

- [[kb-0005]] Langfuse 启动与验证
- [[kb-0003]] PowerShell 常用命令
- [[kb-0004]] Windows 端口管理

## 变更记录

| 日期 | 变更内容 | 作者 |
|---|---|---|
| 2026-05-25 | 创建 | Qoder |
