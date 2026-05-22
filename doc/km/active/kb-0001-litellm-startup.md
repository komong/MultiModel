---
id: kb-0001
title: LiteLLM Proxy 启动与验证
category: 软件配置
tags: [LiteLLM, Python, 模型代理, Windows]
platform: Windows
arch: x86_64
status: active
version: "1.84.0+"
created_at: 2026-05-21
updated_at: 2026-05-21
author: Qoder
related: [kb-0002, kb-0003, kb-0004]
source: ""
---

# LiteLLM Proxy 启动与验证

> 启动 LiteLLM 多模型代理服务，支持 MiniMax、DeepSeek、智谱等模型的统一接入。

## 环境信息

- **操作系统**：Windows 22H2
- **硬件架构**：x86_64
- **依赖版本**：Python 3.10+, litellm >= 1.84.0

## 正文内容

### 安装

```powershell
pip install litellm[proxy]>=1.84.0
```

### 配置

1. 确保项目根目录 `.env` 已配置 API Keys：
```env
MINIMAX_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
ZAI_API_KEY=...
LITELLM_MASTER_KEY=sk-my-master-key-1234
```

2. 模型配置在 `model-platform/config.yaml` 中定义

### 启动

**前台运行（调试用）：**
```powershell
cd d:\Desktop\Test\MultiModel\model-platform
python start_proxy.py
```

**后台运行（生产用）：**
```powershell
cd d:\Desktop\Test\MultiModel\model-platform
Start-Process -FilePath python -ArgumentList "start_proxy.py" -WindowStyle Hidden
```

默认端口 **4800**，可通过参数修改：
```powershell
python start_proxy.py --port 4000
```

### 验证

```powershell
# 检查端口是否被监听
netstat -ano | findstr :4800

# 健康检查（需带 Authorization）
Invoke-RestMethod -Uri "http://localhost:4800/health" -Headers @{"Authorization"="Bearer sk-my-master-key-1234"}

# 模型调用测试
python model-platform/test_call.py
```

### 停止服务

**前台运行时**：直接 `Ctrl+C`

**后台运行时**：
```powershell
# 通过端口查找进程
$pid = (netstat -ano | findstr :4800 | Select-String "LISTENING" | ForEach-Object { ($_ -split '\s+')[-1] })
if ($pid) { Stop-Process -Id $pid -Force }
```

### 日志

```powershell
# 启动时重定向到文件
python start_proxy.py *> litellm.log

# 查看实时日志
Get-Content -Path "litellm.log" -Wait -Tail 20
```

---

## 常见问题

**Q：启动报 `getaddrinfo failed` 警告？**
A：无法访问 GitHub 获取远程 cost map，可安全忽略，不影响功能。

**Q：健康检查返回 401？**
A：需要携带 Authorization header，见上方验证命令。

**Q：端口被占用？**
A：用 `netstat -ano | findstr :4800` 查看占用进程，或用其他端口启动。

---

## 相关词条

- [[kb-0002]] LiteLLM 多模型配置
- [[kb-0003]] PowerShell 常用命令
- [[kb-0004]] Windows 端口管理

## 变更记录

| 日期 | 变更内容 | 作者 |
|---|---|---|
| 2026-05-21 | 创建 | Qoder |
