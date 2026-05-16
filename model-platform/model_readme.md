# LiteLLM 本地多模型统一接入

## 项目简介
通过 LiteLLM Proxy 将 MiniMax、DeepSeek、智谱三家模型统一为 OpenAI 兼容接口，业务方只需一份代码即可调用所有模型。

## 环境信息
- **LiteLLM 版本**：1.84.0（最低要求 1.84.0，否则 智谱 GLM-5.1 无法使用）
- **Python**：3.13
- **Proxy 端口**：4000
- **Master Key**：`sk-my-master-key-1234`（config.yaml 中 `general_settings.master_key`）

## 已接入模型

| 厂商 | model_name（调用用） | LiteLLM 标识 | API Base | 状态 |
|------|---------------------|-------------|----------|------|
| MiniMax | `minimax-m2-5` | `openai/MiniMax-M2.5` | `https://api.minimaxi.com/v1` | ✅ |
| MiniMax | `minimax-m2-7` | `openai/MiniMax-M2.7` | `https://api.minimaxi.com/v1` | ✅ |
| DeepSeek | `deepseek-v4-flash` | `deepseek/deepseek-v4-flash` | 默认 | ✅ |
| DeepSeek | `deepseek-v4-pro` | `deepseek/deepseek-v4-pro` | 默认 | ✅ |
| 智谱 | `glm-5-1` | `openai/glm-5.1` | `https://api.z.ai/api/paas/v4/` | ✅ 已验证 2026-05-16 |

## 文件说明

| 文件 | 用途 |
|------|------|
| `.env` | API Key 存放（MINIMAX_API_KEY / DEEPSEEK_API_KEY / ZAI_API_KEY），已填入真实 key |
| `config.yaml` | LiteLLM 模型配置 + 代理设置（重试3次、超时120s、master key） |
| `start_proxy.py` | 启动脚本，自动加载 `.env` 后启动 proxy |
| `test_call.py` | 一键测试全部 5 个模型 |
| `test_glm.py` | 单独测试 GLM-5.1（含 `thinking: disabled` 参数） |
| `create_keys.py` | 虚拟 Key 管理：为不同业务系统生成限模型/限预算的 key |

## 启动方式

```bash
cd model-platform
python start_proxy.py
```

## 调用示例

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-my-master-key-1234",
    base_url="http://localhost:4000/v1",
)

response = client.chat.completions.create(
    model="glm-5-1",          # 使用 config.yaml 中的 model_name
    messages=[{"role": "user", "content": "你好"}],
    max_tokens=50,
)
```

## 虚拟 Key 管理

Proxy 启动后运行 `python create_keys.py`，自动为三个模拟业务系统生成 key：
- **system-a**：仅 MiniMax，月预算 $10
- **system-b**：仅 DeepSeek，月预算 $20
- **system-c**：全部模型，无预算限制

生成的 key 可通过 LiteLLM 的 `/key/generate` API 管理。

## 已知问题

1. **网络限制**：Proxy 启动时有 `Failed to fetch remote model cost map` 警告（无法访问 GitHub），不影响功能，仅缺失 cost 统计。
2. **线程警告**：关闭 Proxy 时可能出现 threading shutdown 异常，非关键问题。
3. **智谱模型**：使用 `openai/` provider + z.ai 端点（OpenAI 兼容模式），非 `zai/` native provider。如需切换 native 模式需改 `config.yaml`。
