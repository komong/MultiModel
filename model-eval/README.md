# model-eval — 代码生成评测模块

多语言 + 混合粒度的代码生成质量自动评测体系，集成 Langfuse Dataset/Experiment 面板对比。

---

## 目录结构

```
model-eval/
├── core/
│   ├── __init__.py            # 导出核心数据类
│   ├── schema.py              # 数据结构定义
│   └── evaluator.py           # L1 语法检查 + L2 单测执行
├── datasets/
│   └── code_gen_v1.json       # 首批 20 条评测样本
├── langfuse_dataset.py        # Langfuse Dataset 创建 & Experiment 评测
├── run_eval.py                # 主入口
└── requirements.txt
```

---

## 前置条件

| 依赖 | 用途 | 是否必需 |
|------|------|----------|
| LiteLLM Proxy (`localhost:4800`) | 调用模型生成代码 | 完整评测必需 |
| Langfuse (`localhost:3000`) | Dataset/Experiment 面板 | 完整评测必需 |
| Node.js | JS 语法检查 + 单测执行 | JS 样本必需，无则跳过 |
| `.env`（项目根目录） | API Keys、Langfuse 配置 | 必需 |

环境变量（已在项目根 `.env` 中配置，模块自动加载）：

```
LITELLM_BASE_URL=http://localhost:4800
LITELLM_MASTER_KEY=sk-my-master-key-1234
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000
```

---

## 快速验证（无需启动任何服务）

```bash
cd model-eval
python run_eval.py --dry-run
```

此命令用数据集中的 `reference_solution`（参考答案）跑 L1+L2 评测，验证评测器本身是否正常。不调用模型，不连接 Langfuse。

---

## 运行完整评测

```bash
# 确保 LiteLLM Proxy + Langfuse 已启动，然后：
cd model-eval
python run_eval.py
```

完整流程：上传 Dataset → 逐模型调用生成代码 → L1+L2 评分 → 写入 Langfuse → 打印汇总。

---

## 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--models` | deepseek-v4-pro deepseek-v4-flash minimax-m2-5 glm-5-1 | 评测模型列表 |
| `--dataset` | `datasets/code_gen_v1.json` | 评测样本 JSON 路径 |
| `--dry-run` | false | 仅测试评测器，不调用模型 |
| `--skip-upload` | false | 跳过上传 Dataset（已有数据集时用） |

示例：

```bash
# 只评测两个模型
python run_eval.py --models deepseek-v4-pro minimax-m2-5

# 数据集已上传过，跳过重复上传
python run_eval.py --skip-upload

# 用自定义数据集
python run_eval.py --datasets my_dataset.json
```

---

## 评测维度

| 层级 | 维度 | 评测方式 | 当前状态 |
|------|------|----------|----------|
| L1 | 语法正确性 | AST / node --check / 正则 | 已实现 |
| L2 | 功能正确性 | exec 单测 / node 单测 | 已实现 |
| L3 | 需求完整性 | LLM-as-Judge | 未实现 |
| L4 | 代码质量 | LLM-as-Judge | 未实现 |

### L1 语法检查

| 语言 | 实现方式 | 备注 |
|------|----------|------|
| Python | `ast.parse()` | 无外部依赖 |
| JavaScript | `node --check` 临时文件 | 需本地安装 node，未安装则跳过（返回 1.0） |
| SQL | 正则检查是否以 SELECT/INSERT 等开头 | 基础检查，无外部依赖 |
| 其他 | 默认通过 | — |

### L2 单测执行

| 语言 | 实现方式 | 备注 |
|------|----------|------|
| Python | `exec()` 提取函数 → 逐条执行 test_case → 比对结果 | 无外部依赖 |
| JavaScript | 生成临时 .js → `node` 执行 → exit code 判断 | 需本地安装 node |
| SQL | 跳过 | 需数据库环境，后续扩展 |

---

## 数据结构

### 样本结构（JSON）

```json
{
  "id": "py-simple-001",
  "input": {
    "instruction": "写一个函数，输入整数列表，返回去重后排序的结果",
    "language": "python",
    "granularity": "function",
    "context": ""
  },
  "expected_output": {
    "test_cases": [
      {"input": "[3, 1, 2, 1]", "expected": "[1, 2, 3]"},
      {"input": "[]", "expected": "[]"}
    ],
    "must_contain": ["set", "sorted"],
    "reference_solution": "def dedup_sorted(lst):\n    return sorted(set(lst))"
  },
  "metadata": {
    "difficulty": "easy",
    "tags": ["list", "dedup", "sort"],
    "source": "manual"
  }
}
```

### test_cases 约定

- **单参数函数**：`"input": "[3,1,2,1]"` — eval 后直接传入
- **多参数函数**：`"input": "(dict1, dict2)"` — eval 为 tuple，自动解包 `func(*args)`
- **类级别/无法自动测试**：`"expected": "'skip_class'"` — 以 `skip` 开头则跳过，不计入 L2 通过率

### 核心数据类（core/schema.py）

| 类名 | 用途 |
|------|------|
| `EvalInput` | 评测输入：instruction, language, granularity, context |
| `ExpectedOutput` | 期望输出：test_cases, must_contain, reference_solution |
| `EvalItem` | 单条样本：id + input + expected_output + metadata |
| `EvalScore` | 评分结果：syntax_valid (0/1), test_pass_rate (0~1) |
| `EvalResult` | 评测结果：item + generated_code + scores + model |

---

## Langfuse 集成

### Dataset 名称

默认：`code-gen-v1`

### Experiment 命名规则

`{model_name}-eval`，例如 `deepseek-v4-pro-eval`

### Langfuse 中的数据

每条评测样本在 Langfuse 中记录：
- **input**：instruction + language + granularity
- **output**：模型生成的代码
- **scores**：`syntax_valid`（0/1）、`test_pass_rate`（0~1）

在 Langfuse UI (`http://localhost:3000`) → Datasets → 选择 `code-gen-v1` → Experiments 面板可对比不同模型的评分。

---

## 首批数据集分布

| 类别 | 数量 | 语言 | ID 范围 |
|------|------|------|---------|
| 简单函数 | 5 | Python | py-simple-001 ~ 005 |
| 简单函数 | 3 | JavaScript | js-simple-001 ~ 003 |
| SQL 查询 | 3 | SQL | sql-simple-001 ~ 003 |
| 中等函数 | 5 | Python | py-medium-001 ~ 005 |
| 类/模块级 | 4 | Python | py-class-001 ~ 004 |

---

## 添加新样本

1. 编辑 `datasets/code_gen_v1.json`，追加新样本（保持相同结构）
2. 或创建新 JSON 文件，用 `--dataset` 指定路径
3. 类级别样本：`test_cases` 设为 `[{"input": "None", "expected": "'skip_class'"}]`，L2 自动跳过

---

## 扩展方向

- **L3 需求完整性**：用 LLM-as-Judge 对比 instruction 与生成代码，检查是否覆盖所有需求点
- **L4 代码质量**：用 LLM-as-Judge 评分可读性、健壮性、风格
- **SQL L2 评测**：嵌入 SQLite 内存数据库，自动执行 SQL 并比对结果
- **类级别 L2**：自动生成类的测试脚本（实例化 → 调用方法 → 断言）
- **更多语言**：Java（javac 编译检查）、Go 等
