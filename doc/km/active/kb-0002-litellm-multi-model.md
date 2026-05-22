---
id: kb-0002
title: LiteLLM 多模型配置
category: 软件配置
tags: [LiteLLM, MiniMax, DeepSeek, 智谱, 模型配置]
platform: 跨平台
arch: x86_64
status: active
version: ""
created_at: 2026-05-21
updated_at: 2026-05-21
author: Qoder
related: [kb-0001]
source: ""
---

# LiteLLM 多模型配置

> 在 LiteLLM 中配置 MiniMax、DeepSeek、智谱等多模型的 OpenAI 兼容模式。

## 环境信息

- **操作系统**：跨平台
- **硬件架构**：x86_64
- **依赖版本**：litellm >= 1.84.0

## 正文内容

### 模型列表

| 模型名 | 底层模型 | API 来源 | 类型 | max_tokens |
|--------|---------|----------|------|-----------|
| minimax-m2-5 | openai/MiniMax-M2.5 | minimaxi.com | 普通对话 | 2048 |
| minimax-m2-7 | openai/MiniMax-M2.7 | minimaxi.com | 推理模型 | 8192 |
| deepseek-v4-flash | deepseek/deepseek-v4-flash | deepseek.com | 推理模型 | 8192 |
| deepseek-v4-pro | deepseek/deepseek-v4-pro | deepseek.com | 推理模型 | 8192 |
| glm-5-1 | openai/glm-5.1 | z.ai | 普通对话 | 2048 |

### 配置文件

`model-platform/config.yaml` 示例：

```yaml
model_list:
  - model_name: minimax-m2-5
    litellm_params:
      model: openai/MiniMax-M2.5
      api_key: os.environ/MINIMAX_API_KEY
      api_base: https://api.minimax.chat/v1
      request_timeout: 120

  - model_name: minimax-m2-7
    litellm_params:
      model: openai/MiniMax-M2.7
      api_key: os.environ/MINIMAX_API_KEY
      api_base: https://api.minimax.chat/v1
      request_timeout: 120

  - model_name: deepseek-v4-flash
    litellm_params:
      model: deepseek/deepseek-v4-flash
      api_key: os.environ/DEEPSEEK_API_KEY
      request_timeout: 120

  - model_name: glm-5-1
    litellm_params:
      model: openai/glm-5.1
      api_key: os.environ/ZAI_API_KEY
      api_base: https://open.bigmodel.cn/api/paas/v4
      request_timeout: 120
```

### 推理模型 token 配置

推理模型（minimax-m2-7, deepseek-v4-flash, deepseek-v4-pro）的 reasoning_content 与 content 共享 max_tokens 上限，需要设置为 8192：

```python
REASONING_MODELS = {"minimax-m2-7", "deepseek-v4-flash", "deepseek-v4-pro"}
max_tokens = 8192 if model in REASONING_MODELS else 2048
```

### 环境变量

```env
MINIMAX_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
ZAI_API_KEY=...
```

---

## 常见问题

**Q：glm-5-1 调用报 `Model not found`？**
A：需要 litellm >= 1.84.0，且必须使用 `zai/` provider 或正确的 api_base。

**Q：推理模型返回空 content？**
A：max_tokens 设置过低，推理模型的思考链消耗了大量 token，需设置为 8192。

---

## 相关词条

- [[kb-0001]] LiteLLM Proxy 启动与验证

## 变更记录

| 日期 | 变更内容 | 作者 |
|---|---|---|
| 2026-05-21 | 创建 | Qoder |
