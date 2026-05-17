"""
run_eval.py

代码生成评测主入口。
用法：
    # 完整评测（需 LiteLLM Proxy + Langfuse 运行中）
    python run_eval.py

    # 指定模型
    python run_eval.py --models deepseek-v4-pro deepseek-v4-flash

    # 指定数据集
    python run_eval.py --dataset datasets/code_gen_v1.json

    # 仅跑 L1 语法检查（不调用模型，用参考答案测试评测器）
    python run_eval.py --dry-run
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录 .env
load_dotenv(Path(__file__).parent.parent / ".env")

from core.schema import EvalItem, EvalResult, EvalScore
from core.evaluator import check_syntax, run_tests, evaluate
from langfuse_dataset import load_items_from_json, create_dataset_from_json, run_experiment

# 默认评测模型列表
DEFAULT_MODELS = ["minimax-m2-5", "minimax-m2-7", "deepseek-v4-flash"]

# 默认数据集路径
DEFAULT_DATASET = str(Path(__file__).parent / "datasets" / "code_gen_v1.json")


def make_model_fn(model: str):
    """构造模型调用函数（同步包装）。"""
    from openai import OpenAI

    base_url = os.getenv("LITELLM_BASE_URL", "http://localhost:4800")
    api_key = os.getenv("LITELLM_MASTER_KEY", "sk-my-master-key-1234")
    client = OpenAI(base_url=base_url, api_key=api_key)

    def model_fn(inp: dict) -> str:
        instruction = inp.get("instruction", "")
        language = inp.get("language", "python")
        granularity = inp.get("granularity", "function")
        context = inp.get("context", "")

        # 构造 system prompt，引导模型只输出代码
        system_prompt = (
            f"你是一个代码生成助手。请根据用户需求生成{language}代码。\n"
            f"粒度：{granularity}\n"
            "要求：\n"
            "- 只输出代码，不要解释\n"
            "- 不要用 markdown 代码块包裹\n"
            "- 确保代码可直接执行\n"
        )

        user_prompt = instruction
        if context:
            user_prompt = f"已有上下文：\n{context}\n\n需求：{instruction}"

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2048,
            )
            code = response.choices[0].message.content.strip()
            # 去除可能的 markdown 代码块包裹
            if code.startswith("```"):
                lines = code.split("\n")
                # 去掉首尾 ``` 行
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                code = "\n".join(lines)
            return code
        except Exception as e:
            print(f"  [ModelCall] {model} 调用失败: {e}")
            return ""

    return model_fn


def dry_run(json_path: str):
    """仅用参考答案测试 L1+L2 评测器，不调用模型。"""
    items = load_items_from_json(json_path)
    print(f"\n{'='*60}")
    print(f"DRY RUN — 测试评测器（{len(items)} 条样本）")
    print(f"{'='*60}")

    for item in items:
        ref = item.expected_output.reference_solution
        if not ref:
            print(f"  [SKIP] {item.id:20s} — 无参考答案")
            continue

        scores = evaluate(ref, item.input.language, item.expected_output.test_cases)
        status = "PASS" if scores.syntax_valid > 0 else "FAIL"
        print(f"  [{status}] {item.id:20s} | L1={scores.syntax_valid:.0f} L2={scores.test_pass_rate:.2f}")

    print()


def print_summary(all_results: dict[str, list[EvalResult]]):
    """打印模型对比汇总表。"""
    print(f"\n{'='*70}")
    print(f"{'评测汇总':^70}")
    print(f"{'='*70}")
    print(f"{'模型':<25s} {'平均L1':>8s} {'平均L2':>8s} {'样本数':>8s}")
    print(f"{'-'*70}")

    for model_name, results in all_results.items():
        if not results:
            continue
        avg_l1 = sum(r.scores.syntax_valid for r in results) / len(results)
        avg_l2 = sum(r.scores.test_pass_rate for r in results) / len(results)
        print(f"{model_name:<25s} {avg_l1:>8.2f} {avg_l2:>8.2f} {len(results):>8d}")

    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="代码生成评测")
    parser.add_argument(
        "--models", nargs="+", default=DEFAULT_MODELS,
        help=f"评测模型列表（默认: {DEFAULT_MODELS}）",
    )
    parser.add_argument(
        "--dataset", default=DEFAULT_DATASET,
        help=f"评测样本 JSON 路径（默认: datasets/code_gen_v1.json）",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="仅测试评测器，不调用模型",
    )
    parser.add_argument(
        "--skip-upload", action="store_true",
        help="跳过上传 Dataset 到 Langfuse（已有数据集时使用）",
    )
    args = parser.parse_args()

    # dry-run 模式
    if args.dry_run:
        dry_run(args.dataset)
        return

    # 1. 上传 Dataset 到 Langfuse
    dataset_name = "code-gen-v1"
    if not args.skip_upload:
        print("[Step 1] 上传 Dataset 到 Langfuse...")
        create_dataset_from_json(
            dataset_name=dataset_name,
            json_path=args.dataset,
            description="代码生成评测集 - 多语言混合粒度",
        )
    else:
        print("[Step 1] 跳过上传，使用已有 Dataset")

    # 2. 逐模型跑 Experiment
    all_results = {}
    for model in args.models:
        print(f"\n[Step 2] 评测模型: {model}")
        model_fn = make_model_fn(model)
        results = run_experiment(
            dataset_name=dataset_name,
            run_name=f"{model}-eval",
            model_fn=model_fn,
        )
        all_results[model] = results

    # 3. 打印汇总
    print_summary(all_results)


if __name__ == "__main__":
    main()
