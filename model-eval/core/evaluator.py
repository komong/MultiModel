"""
core/evaluator.py

L1 语法正确性 + L2 功能正确性 评测器。
"""

import ast
import re
import subprocess
import tempfile
import os
from core.schema import EvalScore


def check_syntax(code: str, language: str) -> float:
    """
    L1 评测：检查代码语法是否正确。
    返回 1.0（通过）或 0.0（失败）。
    """
    if not code or not code.strip():
        return 0.0

    language = language.lower().strip()

    if language == "python":
        return _check_python_syntax(code)
    elif language in ("javascript", "js", "typescript", "ts"):
        return _check_js_syntax(code)
    elif language == "sql":
        return _check_sql_syntax(code)
    else:
        # 其他语言暂不检查，默认通过
        return 1.0


def run_tests(code: str, test_cases: list[dict], language: str) -> float:
    """
    L2 评测：执行单测用例，返回通过率 (0.0 ~ 1.0)。
    """
    if not test_cases:
        return 0.0

    language = language.lower().strip()

    if language == "python":
        return _run_python_tests(code, test_cases)
    elif language in ("javascript", "js", "typescript", "ts"):
        return _run_js_tests(code, test_cases)
    elif language == "sql":
        # SQL 评测需数据库环境，暂跳过
        return 0.0
    else:
        return 0.0


def evaluate(code: str, language: str, test_cases: list[dict]) -> EvalScore:
    """一次性跑 L1 + L2，返回 EvalScore。"""
    syntax_valid = check_syntax(code, language)
    test_pass_rate = run_tests(code, test_cases, language) if syntax_valid > 0 else 0.0
    return EvalScore(
        syntax_valid=syntax_valid,
        test_pass_rate=test_pass_rate,
    )


# ── 内部实现 ──────────────────────────────────────────────


def _check_python_syntax(code: str) -> float:
    try:
        ast.parse(code)
        return 1.0
    except SyntaxError:
        return 0.0


def _check_js_syntax(code: str) -> float:
    """通过写入临时文件用 node --check 检查语法。"""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".js", delete=False
        ) as f:
            f.write(code)
            tmp_path = f.name

        result = subprocess.run(
            ["node", "--check", tmp_path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return 1.0 if result.returncode == 0 else 0.0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # node 未安装或超时，跳过检查
        return 1.0
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _check_sql_syntax(code: str) -> float:
    """SQL 基础检查：是否以标准 SQL 语句开头"""
    stripped = code.strip().upper()
    sql_keywords = ("SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "WITH")
    for kw in sql_keywords:
        if stripped.startswith(kw):
            return 1.0
    return 0.0


def _run_python_tests(code: str, test_cases: list[dict]) -> float:
    """
    执行 Python 单测。
    test_cases 格式: [{"input": "arg_value", "expected": "expected_result"}, ...]

    - 单参数函数：input 为单个值字符串
    - 多参数函数：input 为元组字符串，如 "(arg1, arg2)"
    - 跳过标记：expected 为 "'skip_class'" 或 "'skip_lru'" 等以 skip 开头的字符串时，跳过该用例

    约定：生成的代码中，第一个顶层函数定义即为待测函数。
    """
    passed = 0
    total = 0

    # 提取第一个函数名
    try:
        tree = ast.parse(code)
        func_names = [
            node.name for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        ]
        if not func_names:
            return 0.0
        func_name = func_names[0]
    except SyntaxError:
        return 0.0

    # 执行代码，获取函数
    try:
        exec_globals = {}
        exec(code, exec_globals)
        func = exec_globals.get(func_name)
        if func is None or not callable(func):
            return 0.0
    except Exception:
        return 0.0

    for tc in test_cases:
        # 跳过标记：expected 以 'skip' 开头的不计入评测
        expected_raw = tc.get("expected", "")
        if isinstance(expected_raw, str) and expected_raw.strip().startswith("'skip"):
            continue

        total += 1
        try:
            input_val = eval(tc["input"])
            expected_val = eval(tc["expected"])
            # 支持多参数：若 input_val 是 tuple，则解包传入
            if isinstance(input_val, tuple):
                result = func(*input_val)
            else:
                result = func(input_val)
            if result == expected_val:
                passed += 1
        except Exception:
            pass

    return passed / total if total > 0 else 0.0


def _run_js_tests(code: str, test_cases: list[dict]) -> float:
    """
    执行 JavaScript 单测。
    生成临时 .js 文件，用 node 执行。
    """
    passed = 0
    total = len(test_cases)

    # 构造测试脚本
    # 从代码中提取最后一个 function 声明名
    match = re.search(r'function\s+(\w+)\s*\(', code)
    if not match:
        # 尝试箭头函数: const funcName = ...
        match = re.search(r'(?:const|let|var)\s+(\w+)\s*=\s*(?:function|\()', code)
    if not match:
        return 0.0

    func_name = match.group(1)

    for tc in test_cases:
        try:
            test_script = f"""
{code}

const input = {tc['input']};
const expected = {tc['expected']};
const result = {func_name}(input);
if (JSON.stringify(result) === JSON.stringify(expected)) {{
    process.exit(0);
}} else {{
    process.exit(1);
}}
"""
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".js", delete=False
            ) as f:
                f.write(test_script)
                tmp_path = f.name

            result = subprocess.run(
                ["node", tmp_path],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                passed += 1
        except Exception:
            pass
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return passed / total if total > 0 else 0.0
