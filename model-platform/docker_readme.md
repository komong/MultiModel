# WSL Docker 环境说明

## 环境概览

| 项目 | 内容 |
|------|------|
| **WSL 发行版** | Ubuntu 24.04.4 LTS (WSL 2) |
| **用户** | `nigel`（sudo 密码：`nigel`） |
| **Docker Engine** | Community **29.3.1** |
| **Docker Compose** | v5.1.1 |
| **Buildx** | v0.33.0 |
| **内核** | 6.6.114.1-microsoft-standard-WSL2 |
| **存储驱动** | overlayfs |
| **CPU** | 8 核 |
| **Docker Desktop** | **未安装**（Docker 直接在 WSL 内安装） |

## Docker 服务管理

### 启动 Docker daemon

由于 WSL 重启后 Docker daemon 不会自启，需要手动启动：

```bash
# 方式一：后台启动（推荐）
sudo dockerd &

# 方式二：通过 systemd（需 WSL 启用 systemd）
sudo systemctl start docker
# 设置开机自启
sudo systemctl enable docker
```

### 验证运行状态

```bash
docker info --format '{{.ServerVersion}} {{.ContainersRunning}} running / {{.Containers}} total'
docker ps
```

## 容器列表

### 全量容器（共 20 个）

所有容器当前均为 **Exited（已停止）** 状态，数据保留在持久卷中。

#### build 项目
| 容器名 | 镜像 | 创建时间 |
|--------|------|----------|
| `build-webui-local` | `f9dc36bdd3da` | 2026-05-03 |
| `build-backend-local` | `6b0674c2a95b` | 2026-05-03 |

#### dim0-src 项目
| 容器名 | 镜像 | 创建时间 |
|--------|------|----------|
| `dim0-src-webui-dev` | `37a6384823c5` | 2026-05-03 |
| `dim0-src-backend-dev` | `06f5810c5891` | 2026-05-03 |

#### langfuse（可观测性平台）
| 容器名 | 镜像 | 创建时间 |
|--------|------|----------|
| `langfuse:3` | `cdfdca609912` | 2026-04-xx |
| `langfuse-worker:3` | `f8a9eb480b31` | 2026-04-xx |
| `clickhouse-server` | `537014a67ce8` | 2026-04-xx |
| `minio/minio` | `14cea493d9a3` | 2026-04-xx |
| `postgres:15` (x2) | `29342cb52157` | 2026-04-xx |

#### n8n（自动化平台）
| 容器名 | 镜像 | 创建时间 |
|--------|------|----------|
| `n8nio/n8n:latest` | `331ce55da625` | 2026-04-20 |

#### planka（项目管理）
| 容器名 | 镜像 | 创建时间 |
|--------|------|----------|
| `plankanban/planka:latest` | `32c919d9e65b` | 2026-04-xx |

#### 其他基础组件
| 容器名 | 镜像 | 数量 |
|--------|------|------|
| `postgres:17` | `7b405451d054` | 1 |
| `postgres:16-alpine` | `20edbde7749f` | 1 |
| `qdrant/qdrant:latest` | `94728574965d` | 3 |
| `redis:7` | `3e0669e42d4f` | 1 |
| `redis:7-alpine` | `7aec734b2bb2` | 2 |

## 持久卷

### Volume 列表

| 卷名 | 所属项目 |
|------|----------|
| `langfuse_langfuse_clickhouse_data` | langfuse |
| `langfuse_langfuse_clickhouse_logs` | langfuse |
| `langfuse_langfuse_postgres_data` | langfuse |
| `langfuse_langfuse_minio_data` | langfuse |
| `langfuse_langfuse_redis_data` | langfuse |
| `n8n_n8n_data` | n8n |
| `planka_planka-db-data` | planka |
| `build_pg_data_local` | build |
| `build_qdrant_data_local` | build |
| `build_redis_data_local` | build |
| `build_backend_data_local` | build |
| `dim0-src_pg_data_dev` | dim0-src |
| `dim0-src_qdrant_data_dev` | dim0-src |
| `dim0-src_redis_data_dev` | dim0-src |
| `dim0-src_backend_data_dev` | dim0-src |

## 已知限制

### 1. WSL 终端集成限制
当前 PowerShell 终端环境与 WSL 的交互式控制台兼容性不佳（`WSL_E_CONSOLE`），部分命令执行会失败。

**可靠替代方案：通过 `\\wsl.localhost\Ubuntu\` 路径直接访问 WSL 文件系统**
```powershell
# 读取容器配置示例
Get-Content "\\wsl.localhost\Ubuntu\var\lib\docker\containers\<容器ID>\config.v2.json" | ConvertFrom-Json

# 查看文件
Get-Item "\\wsl.localhost\Ubuntu\usr\bin\docker" | Select-Object Length, LastWriteTime
```

### 2. 绕过限制的有效命令格式
```bash
# 单引号包裹 bash -c 参数内容（避免 PowerShell 双引号冲突）
wsl -d Ubuntu -- bash -c 'echo nigel | sudo -S docker ps'

# 简短命令通常成功，复杂多行命令易触发 WSL_E_CONSOLE
```

### 3. Docker daemon 不自启
WSL 重启后 Docker daemon 不会自动启动，需手动执行 `sudo dockerd &`。

## 容器配置文件路径参考

```plaintext
\\wsl.localhost\Ubuntu\var\lib\docker\
├── containers\         # 容器运行时数据
│   └── <container_id>\config.v2.json   # 容器配置（镜像、状态、挂载等）
├── volumes\            # 持久卷数据
│   ├── <volume_name>\_data\
│   └── metadata.db
├── image\              # 镜像层数据
├── runtimes\           # 运行时配置
└── engine-id           # 引擎唯一标识
```
