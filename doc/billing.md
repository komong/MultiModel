# MultiModel 用量统计与计费说明

## 一、背景

MultiModel 项目通过 LiteLLM Proxy 统一接入多个大模型供应商，所有 API 调用都经过 Proxy 转发。LiteLLM 内置了按 token 单价计费的能力（`spend = prompt_tokens x input_price + completion_tokens x output_price`），费用记录写入 PostgreSQL 数据库的 `LiteLLM_SpendLogs` 表。

但本项目当前接入的模型付费模式各不相同，并非全部按 token 用量计费：

| 模型 | 供应商 | 付费模式 | 说明 |
|------|--------|---------|------|
| MiniMax-M2.5 | MiniMax | Token Plan 包月 | 按请求数计费，不按 token |
| MiniMax-M2.7 | MiniMax | Token Plan 包月 | 按请求数计费，不按 token |
| DeepSeek-v4-flash | DeepSeek | 按量计费 | 按 token 用量计费 |
| DeepSeek-v4-pro | DeepSeek | 按量计费 | 按 token 用量计费 |
| GLM-5.1 | 智谱 AI | 待确认 | 付费方式待确认 |

由于部分模型为包月订阅、按请求数计费，直接使用 LiteLLM 的 token 单价计费会产生不准确的费用数据。因此当前策略是 **只统计消耗量，不计费用**。

## 二、当前策略：仅统计消耗量，费用置零

### 2.1 配置方式

在 `config.yaml` 中，所有模型显式设置 `input_cost_per_token: 0` 和 `output_cost_per_token: 0`，覆盖 LiteLLM cost map 中的默认定价：

```yaml
# model-platform/config.yaml（model-tracing/config/config.yaml 同步）
model_list:
  - model_name: minimax-m2-5
    litellm_params:
      model: openai/MiniMax-M2.5
      api_key: os.environ/MINIMAX_API_KEY
      api_base: https://api.minimaxi.com/v1
      input_cost_per_token: 0      # 强制单价为 0
      output_cost_per_token: 0     # 强制单价为 0

  # ... 其他模型同理，均设为 0
```

**优先级**：`config.yaml` 中的 `input_cost_per_token` / `output_cost_per_token` > cost map JSON 中的定价。即使后续运行 `update_cost_map.py` 更新了定价文件，也不会影响这里的 0 价设置。

### 2.2 统计维度

SpendLogs 表中每次 API 调用记录以下信息：

| 字段 | 含义 | 当前值 |
|------|------|--------|
| `model` | 模型名（config.yaml 中的 `model_name`） | 如 `deepseek-v4-flash` |
| `prompt_tokens` | 输入 token 数 | 实际值 |
| `completion_tokens` | 输出 token 数 | 实际值 |
| `spend` | 费用（美元） | **0**（全部模型单价为 0） |
| `startTime` | 请求时间 | 实际值 |
| `endTime` | 响应时间 | 实际值 |
| `request_id` | 请求唯一 ID | 实际值 |
| `user` | 调用用户（如有） | 取决于请求 |

### 2.3 请求数统计

包月模型的核心指标是 **请求数**，可以通过 SQL 直接统计：

```sql
-- 按模型统计请求数和 token 消耗（按月）
SELECT
  model,
  DATE_TRUNC('month', "startTime") AS month,
  COUNT(*) AS request_count,
  SUM(prompt_tokens) AS total_input_tokens,
  SUM(completion_tokens) AS total_output_tokens,
  SUM(prompt_tokens + completion_tokens) AS total_tokens
FROM "LiteLLM_SpendLogs"
GROUP BY model, DATE_TRUNC('month', "startTime")
ORDER BY month DESC, request_count DESC;
```

## 三、计费流程

```
API 请求 → LiteLLM Proxy（config.yaml 定价=0）
    ↓
转发到模型供应商（MiniMax / DeepSeek / 智谱）
    ↓
模型返回响应（含 usage.prompt_tokens / completion_tokens）
    ↓
LiteLLM 计算费用 = prompt_tokens x 0 + completion_tokens x 0 = 0
    ↓
写入 PostgreSQL SpendLogs 表（token 数记录，spend=0）
    ↓
应用层（Langfuse Tracer）同步 token 明细到 Langfuse Dashboard
```

## 四、涉及文件

| 文件 | 作用 |
|------|------|
| `model-platform/config.yaml` | 主 Proxy 配置，定义模型列表和单价 |
| `model-tracing/config/config.yaml` | model-tracing 模块的 Proxy 配置（与上面保持一致） |
| `.env` | `LITELLM_LOCAL_MODEL_COST_MAP=True` 使用本地 cost map |
| `scripts/update_cost_map.py` | 手动更新 LiteLLM 定价文件（不影响 config.yaml 中的 0 价覆盖） |
| `model-platform/create_keys.py` | 虚拟 Key 管理（含 `max_budget` 预算管控，当前因 spend=0 实际不生效） |

## 五、如需切换为按量计费

如果某个模型切换为按 token 付费，只需在 `config.yaml` 中修改对应模型的单价：

```yaml
# 示例：DeepSeek-v4-flash 切换为按量计费
- model_name: deepseek-v4-flash
  litellm_params:
    model: deepseek/deepseek-v4-flash
    api_key: os.environ/DEEPSEEK_API_KEY
    # 删除 input_cost_per_token 和 output_cost_per_token
    # LiteLLM 会自动使用 cost map 中的定价
```

或者手动指定单价（更精确）：

```yaml
- model_name: deepseek-v4-flash
  litellm_params:
    model: deepseek/deepseek-v4-flash
    api_key: os.environ/DEEPSEEK_API_KEY
    input_cost_per_token: 0.0000001    # $0.1 / 1M tokens
    output_cost_per_token: 0.0000004   # $0.4 / 1M tokens
```

修改后重启 LiteLLM Proxy 生效。

## 六、Cost Map 机制说明

LiteLLM 维护一个全局定价文件 `model_prices_and_context_window.json`，包含 2700+ 模型的 token 单价和上下文窗口信息。

- 本项目通过 `.env` 中 `LITELLM_LOCAL_MODEL_COST_MAP=True` 跳过远程获取，直接使用本地备份
- 通过 `scripts/update_cost_map.py` 手动同步最新定价
- `config.yaml` 中显式设置的单价 **优先级高于** cost map，不受更新影响

详细说明见 `doc/cost_map.md`。

## 七、查询用量报表

### 7.1 按模型汇总

```sql
SELECT
  model,
  COUNT(*) AS total_requests,
  SUM(prompt_tokens) AS total_input_tokens,
  SUM(completion_tokens) AS total_output_tokens
FROM "LiteLLM_SpendLogs"
GROUP BY model
ORDER BY total_requests DESC;
```

### 7.2 按天统计

```sql
SELECT
  model,
  DATE("startTime") AS date,
  COUNT(*) AS daily_requests,
  SUM(prompt_tokens + completion_tokens) AS daily_tokens
FROM "LiteLLM_SpendLogs"
GROUP BY model, DATE("startTime")
ORDER BY date DESC;
```

### 7.3 通过 LiteLLM API 查询

```powershell
# 查看虚拟 Key 的累计用量
py model-platform/create_keys.py info <key_or_id>

# 列出所有 Key 及其用量
py model-platform/create_keys.py list
```

### 7.4 通过 Langfuse Dashboard

访问 `http://localhost:3000`，可按 Trace/Span 维度查看每次调用的 token 明细和延迟。
