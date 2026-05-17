# Langfuse 集成现状

> 更新时间：2026-05-17

## 一、架构设计

项目采用**抽象工厂模式**，追踪层与业务逻辑解耦，切换后端只需改环境变量。

```
model-tracing/core/
├── tracer.py            ← 抽象接口（BaseTracer / TraceData / SpanData / ConsoleTracer / NoopTracer）
├── langfuse_tracer.py   ← Langfuse v4 API 实现
└── tracer_factory.py    ← 工厂，按 TRACER_BACKEND 切换
```

**后端切换**（由 `.env` 中 `TRACER_BACKEND` 控制）：

| 值 | 行为 |
|----|------|
| `console` | 打印到终端（默认，本地调试） |
| `langfuse` | 写入 Langfuse |
| `noop` | 不追踪 |

---

## 二、环境配置

### 2.1 `.env` 配置（项目根目录）

```env
TRACER_BACKEND=langfuse

LANGFUSE_PUBLIC_KEY=pk-lf-518f4247-e182-4728-9db5-601d689ac277
LANGFUSE_SECRET_KEY=sk-lf-8fb6619a-1447-4330-b4ce-e89ff0688ead
LANGFUSE_HOST=http://localhost:3000
```

### 2.2 Docker 部署

配置文件：`model-tracing/langfuse-docker-compose.yml`

- Langfuse Server：`langfuse/langfuse:2`，端口 3000
- PostgreSQL 15：`langfuse-db`，端口 5432（内部）
- 数据持久化：`langfuse_postgres` volume
- 健康检查：`pg_isready`，5s 间隔，10 次重试

### 2.3 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| LiteLLM Proxy | 4800 | 模型统一接入 |
| Langfuse Web | 3000 | 追踪可视化（WSL Docker） |

---

## 三、LangfuseTracer 实现细节

### 3.1 v4 API 适配

已从旧版 `client.trace()` 迁移至 v4 的 `start_observation` 分层模型：

- **Trace 级**：`start_observation(trace_context={...})` 创建
- **Span 级**：`start_observation(parent=trace_obs.id)` 创建，关联父级
- **完成上报**：显式调用 `obs.end()`

### 3.2 写入字段

**Trace 级 observation**：

| 字段 | 来源 |
|------|------|
| id | trace.trace_id |
| name | trace.name |
| input | trace.input |
| output | trace.output |
| metadata.task_mode | parallel / pipeline / smart_route |
| metadata.source_system | 来源业务系统 |
| metadata.task_type | 任务类型 |
| metadata.total_tokens | 总 token 数 |
| metadata.total_latency_ms | 总延迟(ms) |
| tags | [task_mode, source_system, task_type, status] |

**Span 级 Generation**：

| 字段 | 来源 |
|------|------|
| name | span.name（步骤名称） |
| model | span.model |
| input | span.input |
| output | span.output |
| metadata.latency_ms | 单步延迟 |
| metadata.status | success / error |
| metadata.error | 错误信息 |
| metadata.input_tokens | 输入 token（当前默认 0，见问题） |
| metadata.output_tokens | 输出 token（当前默认 0，见问题） |
| metadata.total_tokens | 总 token |
| usage_details | {input, output, total} |
| level | ERROR / DEFAULT |

### 3.3 容错机制

追踪失败不影响主流程，仅打印警告：

```python
except Exception as e:
    print(f"[LangfuseTracer] 写入失败: {e}")
```

---

## 四、三种任务模式的追踪集成

### 4.1 ParallelTask（并行评测）

- 文件：`tasks/parallel_task.py`
- `_record()` 方法将多个模型的调用结果转为多个 SpanData
- Trace name：`parallel:{task_type}`
- 多个 Span 并行，total_latency 取 max

### 4.2 PipelineTask（流水线）

- 文件：`tasks/pipeline_task.py`
- `_record()` 方法将步骤链结果转为有序 SpanData
- Trace name：`pipeline:{task_type}`
- 多个 Span 串行，total_latency 取 sum

### 4.3 SmartRouteTask（智能路由）

- 文件：`tasks/smart_route_task.py`
- 追踪包含路由决策信息（routing_rule、routed_type）
- Trace name：`smart_route:{task_type}`
- 单个 Span，metadata 含路由规则

---

## 五、已知问题

| # | 问题 | 详情 | 严重度 | 状态 |
|---|------|------|--------|------|
| ~~1~~ | ~~**SpanData 缺少 input/output_tokens**~~ | ~~`SpanData` 的 `input_tokens`/`output_tokens` 默认为 0；任务层 `_record()` 只传了 `tokens`~~ | ~~中~~ | ✅ 已修复 |
| ~~2~~ | ~~**SmartRoute 路由规则硬编码国外模型**~~ | ~~`DEFAULT_RULES` 指向 gpt-4o / claude-sonnet / gpt-4o-mini~~ | ~~中~~ | ✅ 已修复 |
| 3 | **Langfuse 服务依赖 WSL Docker** | 需先启动 WSL Docker + Windows 端口转发，才能访问 localhost:3000 | 低 | 待处理 |
| ~~4~~ | ~~**model-task 与 model-tracing 代码重复且未适配**~~ | ~~model-task 未适配根 .env、langfuse v4、国产模型~~ | ~~中~~ | ✅ 已修复 |

> **已修复项**（2026-05-17）：
> - 问题 1：`StepResult` 增加 `input_tokens`/`output_tokens` 字段，三种任务 `_record()` 均已传递，SpanData 写入 Langfuse 时包含完整 token 分离数据
> - 问题 2：`SmartRouteTask` 路由规则改为国产模型（deepseek-v4-pro / glm-5-1 / minimax-m2-5 / deepseek-v4-flash），新增 SIMPLE_QA 路由，保留国外模型注释模板便于后续接入
> - 问题 4：`model-task` 已适配根 `.env`（`load_dotenv` 指向父目录）、`langfuse_tracer.py` 升级 v4 API、`config.yaml` 同步国产模型、`main.py` 默认端口 4800 + 国产模型

---

## 六、写入 Langfuse 的前置条件

1. **启动 Langfuse 服务**：WSL 中 `docker-compose -f langfuse-docker-compose.yml up -d`
2. **Windows 端口转发**：将 WSL 的 3000 端口转发到 Windows localhost:3000
3. **确认 `.env` 配置**：`TRACER_BACKEND=langfuse` + 三项 Langfuse Key
4. **启动 LiteLLM Proxy**：`python start_proxy.py`（端口 4800）
5. **运行任务**：`python main.py`，执行结束后 `tracer.flush()` 确保数据上报
6. **查看数据**：访问 http://localhost:3000
