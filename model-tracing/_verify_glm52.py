"""GLM-5.2 接入验证脚本（临时）"""
import sys
sys.path.insert(0, '.')

from tasks.smart_route_task import SmartRouteTask, TaskType
from core.llm_client import REASONING_MODELS, GLM_REASONING_MODELS

print("=== 智能路由验证 ===")
task = SmartRouteTask(client=None)

prompts = [
    ("分析一下这个方案的优缺点", "ANALYSIS"),
    ("compare A and B", "ANALYSIS"),
]
for prompt, expected_type in prompts:
    ttype, model, desc = task.classify(prompt)
    ok = (ttype == TaskType[expected_type] and model == "glm-5-2")
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] \"{prompt[:20]}\" -> model={model}, type={ttype.value}")
    assert ok, f"期望 glm-5-2, 实际 {model}"

# 验证 glm-5-1 fallback 规则
rules_glm51 = [r for r in task.rules if r.model == "glm-5-1" and r.task_type == TaskType.ANALYSIS]
assert len(rules_glm51) == 1, "glm-5-1 fallback 规则缺失"
print(f"  [PASS] glm-5-1 fallback 规则存在 (priority={rules_glm51[0].priority})")

print("\n=== REASONING_MODELS 验证 ===")
print(f"  REASONING_MODELS = {REASONING_MODELS}")
assert "glm-5-2" in REASONING_MODELS, "glm-5-2 不在 REASONING_MODELS"
print("  [PASS] glm-5-2 在 REASONING_MODELS 中")

print(f"\n=== GLM_REASONING_MODELS 验证 ===")
print(f"  GLM_REASONING_MODELS = {GLM_REASONING_MODELS}")
assert "glm-5-2" in GLM_REASONING_MODELS, "glm-5-2 不在 GLM_REASONING_MODELS"
print("  [PASS] glm-5-2 在 GLM_REASONING_MODELS 中")

print("\n=== 全部验证通过 ===")
