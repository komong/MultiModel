# GLM-5.2 接入 MultiModel LiteLLM Proxy

## 背景

MultiModel 项目已通过 LiteLLM Proxy 接入了 5 个模型（MiniMax x2、DeepSeek x2、智谱 GLM-5.1）。GLM-5.2 是智谱最新发布的推理模型（2026-06-13 全量开放），API 格式与 GLM-5.1 完全兼容，复用同一个 `ZAI_API_KEY` 和 `https://api.z.ai/api/paas/v4/` 端点。

接入后 model_name 为 `glm-5-2`，对外调用方式与 `glm-5-1` 一致。

---

## Task 1: 在 config.yaml 中新增 GLM-5.2 模型配置

**文件**: `model-platform/config.yaml`

在 `glm-5-1` 配置块之后追加：

```yaml
  - model_name: glm-5-2
    litellm_params:
      model: openai/glm-5.2
      api_key: os.environ/ZAI_API_KEY
      api_base: https://api.z.ai/api/paas/v4/
      input_cost_per_token: 0
      output_cost_per_token: 0
```

与 GLM-5.1 配置完全对齐（同 provider、同端点、同 Key、cost 置 0）。

---

## Task 2: 创建 GLM-5.2 专项测试脚本

**文件**: `model-platform/test_glm52.py`（新建）

基于现有 `test_glm.py` 改造，验证 GLM-5.2 连通性。关键点：
- model 改为 `glm-5-2`
- 保留 `extra_body={"thinking": {"type": "disabled"}}` 参数（GLM-5.2 是推理模型，默认可能开启思考链）
- 复用 `http://localhost:4800/v1` 端点和 Master Key

完整脚本内容：

```python
"""
Test GLM-5.2 through the local LiteLLM proxy.

Start the proxy first:
  py start_proxy.py
"""
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key="sk-my-master-key-1234",
    base_url="http://localhost:4800/v1",
)

response = client.chat.completions.create(
    model="glm-5-2",
    messages=[
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "Reply in one short sentence: is GLM-5.2 connected successfully?"},
    ],
    max_tokens=1024,
    temperature=0.6,
    extra_body={"thinking": {"type": "disabled"}},
)

message = response.choices[0].message
content = message.content or ""
if not content.strip():
    print(response.model_dump_json(indent=2))
else:
    print(content)
```

---

## Task 3: 更新智能路由规则，将分析推理任务路由到 GLM-5.2

**文件**: `model-tracing/tasks/smart_route_task.py`

在 `DEFAULT_RULES` 中（第 36-116 行）：
- 将 `ANALYSIS` 规则的 model 从 `glm-5-1` 改为 `glm-5-2`（GLM-5.2 推理能力更强，优先级 8 不变）
- 保留原 `glm-5-1` 规则作为备选（降级到 priority 6，作为 fallback）

修改后 ANALYSIS 相关部分：

```python
        RoutingRule(
            task_type=TaskType.ANALYSIS,
            model="glm-5-2",
            matcher=lambda p: any(
                kw in p.lower() for kw in
                ["分析", "为什么", "原因", "对比", "比较", "评估",
                 "analyze", "compare", "evaluate", "reason"]
            ),
            priority=8,
            description="分析推理任务 → glm-5-2",
        ),
        # GLM-5.1 作为分析任务的 fallback（优先级降低）
        RoutingRule(
            task_type=TaskType.ANALYSIS,
            model="glm-5-1",
            matcher=lambda p: any(
                kw in p.lower() for kw in
                ["分析", "为什么", "原因", "对比", "比较", "评估",
                 "analyze", "compare", "evaluate", "reason"]
            ),
            priority=6,
            description="分析推理任务（备选） → glm-5-1",
        ),
```

---

## Task 4: 更新 llm_client.py 推理模型集合

**文件**: `model-tracing/core/llm_client.py`

第 29 行 `REASONING_MODELS` 集合，将 `glm-5-2` 加入：

```python
# 推理模型：思考链消耗大量 token，需要更高的 max_tokens
REASONING_MODELS = {"minimax-m2-7", "deepseek-v4-flash", "deepseek-v4-pro", "glm-5-2"}
```

使其自动获得更高的 `max_tokens`（8192），因为 GLM-5.2 的思考链会消耗大量 token。

---

## Task 5: 更新虚拟 Key 测试脚本

**文件**: `model-platform/test_call.py`

### 5a. TEST_KEY_CONFIGS 的 `test-all` 配置（第 49-56 行）

models 列表追加 `"glm-5-2"`：

```python
    {
        "name": "test-all",
        "models": [
            "minimax-m2-5", "minimax-m2-7",
            "deepseek-v4-flash", "deepseek-v4-pro",
            "glm-5-1", "glm-5-2",
        ],
        "budget": None,
    },
```

### 5b. 权限隔离测试用例（第 204-212 行）

在 `cases` 列表追加：

```python
        ("test-all", "glm-5-2", True),
```

---

## Task 6: 更新文档

### 6a. model_readme.md

**文件**: `model-platform/model_readme.md`

已接入模型表格（第 16-22 行）追加一行：

| 智谱 | `glm-5-2` | `openai/glm-5.2` | `https://api.z.ai/api/paas/v4/` | 新增 |

### 6b. README.md（项目根）

**文件**: `README.md`

#### 第四节「已接入模型」（第 166-175 行）

表格追加：

| glm-5-2 | `openai/glm-5.2` | `https://api.z.ai/api/paas/v4/` | 智谱 AI |

#### 第七节「智能路由规则」（第 276-288 行）

将 ANALYSIS 行的路由模型更新为 `glm-5-2`：

| ANALYSIS（分析推理） | glm-5-2 | 分析、为什么、对比、评估... | 8 |

---

## 验证方式

接入完成后，启动 Proxy 并运行测试：

```bash
cd model-platform
python start_proxy.py --health-check    # 启动并确认 glm-5-2 出现在模型列表
python test_glm52.py                     # 验证 GLM-5.2 调用成功
```

---

## 涉及文件清单

| # | 文件路径 | 操作 |
|---|---------|------|
| 1 | `model-platform/config.yaml` | 编辑：新增 GLM-5.2 模型配置块 |
| 2 | `model-platform/test_glm52.py` | 新建：GLM-5.2 连通性测试脚本 |
| 3 | `model-tracing/tasks/smart_route_task.py` | 编辑：ANALYSIS 路由改为 glm-5-2，glm-5-1 降级 fallback |
| 4 | `model-tracing/core/llm_client.py` | 编辑：REASONING_MODELS 加入 glm-5-2 |
| 5 | `model-platform/test_call.py` | 编辑：test-all 配置和权限隔离用例追加 glm-5-2 |
| 6a | `model-platform/model_readme.md` | 编辑：已接入模型表格追加行 |
| 6b | `README.md` | 编辑：已接入模型表格 + 智能路由规则表更新 |
