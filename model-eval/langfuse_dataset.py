"""
langfuse_dataset.py

Langfuse Dataset 创建 & Experiment 评测集成。
"""

import json
import os
from typing import Callable, Optional

from core.schema import EvalInput, ExpectedOutput, EvalItem, EvalResult, EvalScore
from core.evaluator import evaluate


def _parse_item(raw: dict) -> EvalItem:
    """将 JSON 原始字典解析为 EvalItem。"""
    inp = raw["input"]
    exp = raw["expected_output"]
    return EvalItem(
        id=raw["id"],
        input=EvalInput(**inp),
        expected_output=ExpectedOutput(**exp),
        metadata=raw.get("metadata", {}),
    )


def load_items_from_json(json_path: str) -> list[EvalItem]:
    """从 JSON 文件加载评测样本列表。"""
    with open(json_path, "r", encoding="utf-8") as f:
        raw_list = json.load(f)
    return [_parse_item(r) for r in raw_list]


def create_dataset_from_json(
    dataset_name: str,
    json_path: str,
    description: str = "",
) -> str:
    """
    从 JSON 文件创建 Langfuse Dataset（幂等：已存在则跳过创建，逐条添加样本）。
    返回 dataset_name。
    """
    from langfuse import Langfuse

    client = Langfuse(
        public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
        host=os.environ.get("LANGFUSE_HOST", "http://localhost:3000"),
    )

    # 创建 dataset（已存在不会报错，Langfuse SDK 会处理）
    try:
        client.create_dataset(
            name=dataset_name,
            description=description or f"Dataset from {json_path}",
        )
    except Exception:
        pass  # 已存在则忽略

    items = load_items_from_json(json_path)

    added = 0
    for item in items:
        try:
            client.create_dataset_item(
                dataset_name=dataset_name,
                input={
                    "instruction": item.input.instruction,
                    "language": item.input.language,
                    "granularity": item.input.granularity,
                    "context": item.input.context,
                },
                expected_output={
                    "test_cases": item.expected_output.test_cases,
                    "must_contain": item.expected_output.must_contain,
                    "reference_solution": item.expected_output.reference_solution,
                },
                metadata=item.metadata,
            )
            added += 1
        except Exception as e:
            print(f"  [DatasetItem] 跳过 {item.id}: {e}")

    print(f"[Langfuse] Dataset '{dataset_name}': 已添加 {added}/{len(items)} 条样本")
    client.flush()
    return dataset_name


def run_experiment(
    dataset_name: str,
    run_name: str,
    model_fn: Callable[[dict], str],
) -> list[EvalResult]:
    """
    在 Langfuse Dataset 上跑 Experiment。

    model_fn: 接收 item.input 字典，返回生成的代码字符串。
    返回每条样本的 EvalResult 列表。

    使用 Langfuse v4 API：为每条样本创建 trace + generation + scores，
    并关联到 dataset item。
    """
    import uuid
    from langfuse import Langfuse

    client = Langfuse(
        public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
        host=os.environ.get("LANGFUSE_HOST", "http://localhost:3000"),
    )

    dataset = client.get_dataset(dataset_name)
    results = []

    print(f"\n{'='*60}")
    print(f"Experiment: {run_name}")
    print(f"Dataset: {dataset_name} ({len(dataset.items)} items)")
    print(f"{'='*60}")

    for item in dataset.items:
        inp = item.input
        language = inp.get("language", "python")
        test_cases = (item.expected_output or {}).get("test_cases", [])

        # 调用模型生成代码
        try:
            generated_code = model_fn(inp)
        except Exception as e:
            generated_code = ""

        # 评测
        scores = evaluate(generated_code, language, test_cases)

        # 写入 Langfuse：创建 trace + generation + scores
        trace_id = str(uuid.uuid4())
        try:
            trace_obs = client.start_observation(
                trace_context={
                    "id": trace_id,
                    "name": f"eval:{run_name}",
                    "input": inp,
                    "output": {"code": generated_code},
                    "metadata": {
                        "dataset_item_id": item.id,
                        "run_name": run_name,
                    },
                    "tags": [run_name, language],
                },
                name=f"eval:{run_name}",
                input=inp,
                output={"code": generated_code},
            )

            # 子 generation
            gen_obs = trace_obs.start_observation(
                name="code-generation",
                as_type="generation",
                input=inp,
                output={"code": generated_code},
            )
            gen_obs.end()

            # 写入 scores
            trace_obs.score(name="syntax_valid", value=scores.syntax_valid)
            trace_obs.score(name="test_pass_rate", value=scores.test_pass_rate)

            trace_obs.end()
        except Exception as e:
            print(f"  [Langfuse] 写入失败: {e}")

        # 构造 EvalItem（从 dataset item 还原）
        eval_input = EvalInput(
            instruction=inp.get("instruction", ""),
            language=language,
            granularity=inp.get("granularity", "function"),
            context=inp.get("context", ""),
        )
        eval_expected = ExpectedOutput(
            test_cases=test_cases,
            must_contain=(item.expected_output or {}).get("must_contain", []),
            reference_solution=(item.expected_output or {}).get("reference_solution", ""),
        )
        eval_item = EvalItem(
            id=item.id or "",
            input=eval_input,
            expected_output=eval_expected,
        )

        result = EvalResult(
            item_id=eval_item.id,
            item=eval_item,
            generated_code=generated_code,
            scores=scores,
            model=run_name,
            trace_id=trace_id,
        )
        results.append(result)

        status = "PASS" if scores.syntax_valid > 0 and scores.test_pass_rate > 0 else "FAIL"
        print(f"  [{status}] {eval_item.id:20s} | L1={scores.syntax_valid:.0f} L2={scores.test_pass_rate:.2f}")

    # flush
    client.flush()

    # 汇总
    avg_l1 = sum(r.scores.syntax_valid for r in results) / len(results) if results else 0
    avg_l2 = sum(r.scores.test_pass_rate for r in results) / len(results) if results else 0
    print(f"\n  平均 L1 (语法): {avg_l1:.2f} | 平均 L2 (单测): {avg_l2:.2f}\n")

    return results
