# MultiModel 系统现状梳理

> 更新时间：2026-05-17

## 一、系统定位

MultiModel 是多模型统一接入与追踪系统，核心能力：

1. **统一接入** — 通过 LiteLLM Proxy 接入多个国产/国际大模型
2. **调用追踪** — 通过 Langfuse 实现全链路可观测性
3. **任务编排** — 支持并行（parallel）、流水线（pipeline）、智能路由（smart_route）三种推理模式

---

## 二、模块架构

```
MultiModel/
├── model-platform/     ← LiteLLM Proxy 多模型统一接入层
├── model-tracing/      ← 模型调用追踪层（主力模块，Langfuse / Console）
├── model-task/         ← 任务层（早期版本，与 model-tracing 高度重复）
├── scripts/            ← 运维脚本（WSL/Docker/端口转发）
├── .env                ← 项目统一环境变量
├── requirements.txt    ← 根依赖（统一版本）
└── README.md
```

---

## 三、各模块详情

### 3.1 `model-platform/` — 模型接入层

**职责**：通过 LiteLLM Proxy 统一接入多个大模型，对外提供 OpenAI 兼容 API。

**已配置模型**（config.yaml）：

| 模型名 | LiteLLM 标识 | API 端点 |
|--------|-------------|---------|
| minimax-m2-5 | `openai/MiniMax-M2.5` | `https://api.minimaxi.com/v1` |
| minimax-m2-7 | `openai/MiniMax-M2.7` | `https://api.minimaxi.com/v1` |
| deepseek-v4-flash | `deepseek/deepseek-v4-flash` | DeepSeek 默认端点 |
| deepseek-v4-pro | `deepseek/deepseek-v4-pro` | DeepSeek 默认端点 |
| glm-5-1 | `openai/glm-5.1` | `https://api.z.ai/api/paas/v4/` |

**关键文件**：

| 文件 | 说明 |
|------|------|
| `config.yaml` | LiteLLM 模型路由配置 |
| `start_proxy.py` | Proxy 启动脚本，支持 `--port` 参数（默认 4800） |
| `create_keys.py` | 虚拟 Key 管理工具 |
| `test_call.py` | 模型调用测试脚本 |
| `test_glm.py` | 智谱模型专项测试脚本 |

**LiteLLM 设置**：重试 3 次，超时 120s，`drop_params: true`（自动丢弃不支持的参数）

---

### 3.2 `model-tracing/` — 追踪层（主力模块）

**职责**：封装三种任务模式 + 集成 Langfuse 追踪。

**核心代码结构**：

```
model-tracing/
├── core/
│   ├── llm_client.py       ← 统一 LLM 调用客户端（AsyncOpenAI）
│   ├── tracer.py            ← 追踪抽象接口（BaseTracer / ConsoleTracer / NoopTracer）
│   ├── langfuse_tracer.py   ← Langfuse v4 API 追踪实现
│   ├── tracer_factory.py    ← 追踪器工厂（按环境变量切换后端）
│   └── task.py              ← 任务模式枚举与结果数据结构
├── tasks/
│   ├── parallel_task.py     ← 并行评测任务
│   ├── pipeline_task.py     ← 流水线任务
│   └── smart_route_task.py  ← 智能路由任务
├── config/config.yaml       ← LiteLLM 模型配置
├── main.py                  ← 演示入口
├── .env.example             ← 已指向根 .env
└── requirements.txt         ← 子模块依赖
```

**追踪后端切换**（由 `.env` 中 `TRACER_BACKEND` 控制）：

| 值 | 行为 |
|----|------|
| `console` | 打印到终端（默认，本地调试） |
| `langfuse` | 写入 Langfuse |
| `noop` | 不追踪 |

**Langfuse 集成**：
- 使用 v4 API（`start_observation` 创建 Trace+Span 层级结构）
- 追踪数据包括：task_mode、source_system、task_type、token 用量、延迟、状态
- 追踪失败不影响主流程，仅打印警告

**main.py 现状**：
- 已将模型改为 `minimax-m2-5`（适配国产模型）
- `demo_parallel()` 和 `demo_pipeline()` 已启用
- `demo_smart_route_classify()` 仅做路由分类验证，不需要 Proxy

---

### 3.3 `model-task/` — 任务层（早期版本）

**现状**：与 `model-tracing/` 代码结构几乎完全相同，但未做国产模型适配。

| 对比项 | model-task | model-tracing |
|--------|-----------|---------------|
| config.yaml 模型 | OpenAI / Claude（未更新） | **国产模型（已同步）** |
| main.py 模型 | gpt-4o / claude-sonnet / gpt-4o-mini | minimax-m2-5 |
| .env 加载 | `load_dotenv()`（当前目录） | `load_dotenv(Path(__file__).parent.parent / '.env')`（根目录） |
| .env.example | 独立配置 | 已指向根 .env |
| requirements.txt | 未单独列出 | `litellm>=1.84.0`（已统一） |

---

### 3.4 `scripts/` — 运维脚本

| 脚本 | 用途 |
|------|------|
| `full_setup.ps1` | 全栈安装 |
| `start_langfuse.bat/ps1/sh` | 启动 Langfuse Docker |
| `port_forward.bat` / `wsl-port-forward.ps1` | WSL 端口转发 |
| `diagnose.sh` | Docker 全栈诊断 |
| `run_check.bat/ps1` | 运行检查 |

---

## 四、环境配置

### 4.1 统一 `.env` 配置

所有子模块共用项目根目录 `.env`，包含：

```env
# 模型 API Keys
MINIMAX_API_KEY=sk-cp-...
DEEPSEEK_API_KEY=sk-...
ZAI_API_KEY=fc467de3...

# LiteLLM Proxy
LITELLM_MASTER_KEY=sk-my-master-key-1234
LITELLM_BASE_URL=http://localhost:4800

# 追踪后端
TRACER_BACKEND=langfuse

# Langfuse
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000
```

### 4.2 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| LiteLLM Proxy | 4800 | 模型统一接入 |
| Langfuse Web | 3000 | 追踪可视化（WSL Docker） |

---

## 五、依赖版本

| 依赖 | 根 requirements.txt | model-tracing requirements.txt | 要求 |
|------|-------------------|-------------------------------|------|
| openai | ≥1.0.0 | ≥1.0.0 | — |
| litellm[proxy] | **≥1.84.0** | **≥1.84.0**（已统一） | glm-5.1 需 ≥1.84.0 |
| langfuse | ≥2.0.0 | ≥2.0.0 | — |
| python-dotenv | ≥1.0.0 | ≥1.0.0 | — |
| requests | ≥2.31.0 | — | create_keys.py 使用 |

---

## 六、已知问题

| # | 问题 | 影响 | 严重度 | 状态 |
|---|------|------|--------|------|
| 1 | `model-task/` 与 `model-tracing/` 代码高度重复 | 维护负担，两者关系不明确 | 中 | 待处理 |
| ~~2~~ | ~~`model-tracing/config.yaml` 仍配 OpenAI/Claude~~ | ~~main.py 调 minimax-m2-5 但 config 里没注册~~ | ~~高~~ | ✅ 已修复 |
| ~~3~~ | ~~`model-tracing/requirements.txt` 版本过低（1.40.0）~~ | ~~glm-5.1 调用会失败~~ | ~~高~~ | ✅ 已修复 |
| ~~4~~ | ~~`model-task/` 未适配根 `.env`~~ | ~~独立 .env.example 与统一配置策略矛盾~~ | ~~中~~ | ✅ 已修复 |
| ~~5~~ | ~~SmartRouteTask 默认路由规则硬编码 gpt-4o/claude~~ | ~~无国产模型路由规则，实际使用时全部 fallback 到默认~~ | ~~中~~ | ✅ 已修复 |
| 6 | SpanData 写入 Langfuse 缺少 input/output_tokens 分离 | 追踪数据 token 维度不完整 | 中 | ✅ 已修复 |

> **已修复项**（2026-05-17）：
> - 问题 2：`model-tracing/config.yaml` 已同步为国产模型（minimax-m2-5/7, deepseek-v4-flash/pro, glm-5-1），超时从 60s→120s，新增 `drop_params: true`
> - 问题 3：`model-tracing/requirements.txt` 中 litellm 版本从 1.40.0 升至 1.84.0
> - 问题 4：`model-task/` 已适配根 `.env`（load_dotenv 指向父目录）、langfuse_tracer.py 升级 v4 API、config.yaml 同步国产模型、main.py 端口 4800 + 国产模型
> - 问题 5：SmartRouteTask 路由规则改为国产模型（deepseek-v4-pro/glm-5-1/minimax-m2-5/deepseek-v4-flash），新增 SIMPLE_QA，保留国外模型注释模板便于后续接入
> - 问题 6：StepResult 增加 input_tokens/output_tokens，三种任务 _record() 均传递至 SpanData

---

## 七、建议方向

1. **明确 `model-task` 定位**：废弃或与 model-tracing 合并，消除代码重复
2. ~~**同步 `model-tracing/config.yaml`**：将模型列表更新为与 `model-platform/config.yaml` 一致的国产模型~~ ✅ 已完成
3. ~~**统一 requirements.txt 版本**：子模块应与根目录保持一致（≥1.84.0）~~ ✅ 已完成
4. ~~**SmartRouteTask 增加国产模型路由规则**：代码任务 → deepseek-v4-pro，分析推理 → glm-5-1，翻译/摘要 → minimax-m2-5 等~~ ✅ 已完成
5. ~~**model-task 的 .env 加载方式统一**：改为加载根 `.env`~~ ✅ 已完成
