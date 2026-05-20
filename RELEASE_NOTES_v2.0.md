# MultiModel v2.0 - 多模型评测与追踪系统

## 发布说明

### 主要更新

#### 1. 评测系统增强
- **评测结果持久化**: 新增JSON格式保存，包含单模型详细结果和汇总对比
- **推理模型适配**: 自动识别推理模型(minimax-m2-7, deepseek-v4-flash, deepseek-v4-pro)，动态提升max_tokens至8192，防止思考链截断
- **Langfuse超时优化**: 将SDK超时从默认改为120秒，提升网络不稳定环境下的稳定性

#### 2. 多模块LLM客户端统一升级
- 统一端口配置: `http://localhost:4800`
- 推理模型自动max_tokens提升逻辑复用

#### 3. 文档与工具
- 新增LiteLLM启动文档 (`doc/litellm_startup.md`)
- 新增MiniMax追踪测试脚本

### 文件变更

```
model-eval/
├── run_eval.py          (+76行) 新增结果持久化、推理模型适配
└── langfuse_dataset.py  (+2行)  超时优化

model-task/core/llm_client.py (+13行) 推理模型max_tokens自动提升
model-tracing/core/llm_client.py (+13行) 同上
model-platform/test_call.py (-1行) 端口更新

doc/litellm_startup.md    (新增) LiteLLM启动指南
model-tracing/test_minimax_trace.py (新增) 追踪测试脚本
langfuse_homepage.png (新增) 截图
model-eval/results/ (新增) 评测结果目录
```

### 技术细节

**推理模型识别机制:**
```python
REASONING_MODELS = {"minimax-m2-7", "deepseek-v4-flash", "deepseek-v4-pro"}

# 调用时自动调整
effective_max_tokens = 8192 if model in REASONING_MODELS else max_tokens
```

**评测结果保存格式:**
```json
{
  "minimax-m2-5": {
    "avg_l1": 0.95,
    "avg_l2": 0.82,
    "sample_count": 50,
    "detail_file": "20260520_xxxx_minimax-m2-5.json"
  }
}
```

### 向后兼容

- 端口变更需更新本地LiteLLM代理配置
- 推理模型max_tokens调整仅在原值≤2048时生效

### 下一步计划

- [ ] 完善评测数据集多语言覆盖
- [ ] 支持更多推理模型
- [ ] 评测结果可视化对比
