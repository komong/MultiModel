"""
core/llm_client.py

统一的 LLM 调用客户端，封装对 LiteLLM Proxy 的调用。
所有任务模式都通过这个客户端发请求。
"""

import time
import asyncio
from dataclasses import dataclass, field
from typing import Optional
from openai import AsyncOpenAI


@dataclass
class LLMResponse:
    """统一的模型响应结构"""
    model: str
    content: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: float
    success: bool
    error: Optional[str] = None


# 推理模型：思考链消耗大量 token，需要更高的 max_tokens
REASONING_MODELS = {"minimax-m2-7", "deepseek-v4-flash", "deepseek-v4-pro", "glm-5-2"}

# GLM 推理模型：默认开启思考链，需禁用以避免空响应
GLM_REASONING_MODELS = {"glm-5-2"}


class LLMClient:
    """
    封装对 LiteLLM Proxy 的调用。
    上层的任务模块只需要用这个 client，不感知底层模型差异。
    """

    def __init__(
        self,
        base_url: str = "http://localhost:4800",
        api_key: str = "sk-my-master-key-1234",
    ):
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def call(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        metadata: Optional[dict] = None,
    ) -> LLMResponse:
        """
        调用指定模型，返回标准化的 LLMResponse。
        失败时不抛异常，而是在 response 里标记 success=False。
        """
        start = time.time()
        try:
            extra_body = {}
            if metadata:
                # LiteLLM 支持通过 metadata 透传追踪信息（接 Langfuse 时用）
                extra_body["metadata"] = metadata

            # 推理模型自动提升 max_tokens
            effective_max_tokens = max_tokens
            if model in REASONING_MODELS and max_tokens <= 2048:
                effective_max_tokens = 8192

            # GLM 推理模型：禁用思考链，避免空响应
            if model in GLM_REASONING_MODELS:
                extra_body["thinking"] = {"type": "disabled"}
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=effective_max_tokens,
                extra_body=extra_body if extra_body else None,
            )
            latency_ms = (time.time() - start) * 1000

            return LLMResponse(
                model=model,
                content=response.choices[0].message.content,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                latency_ms=round(latency_ms, 2),
                success=True,
            )

        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return LLMResponse(
                model=model,
                content="",
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                latency_ms=round(latency_ms, 2),
                success=False,
                error=str(e),
            )
