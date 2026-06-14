# LiteLLM 本地多模型统一接入

## 项目简介
通过 LiteLLM Proxy 将 MiniMax、DeepSeek、智谱三家模型统一为 OpenAI 兼容接口，业务方只需一份代码即可调用所有模型。

## 环境信息
- **LiteLLM 版本**：1.87.0
- **Python**：3.13
- **Proxy 端口**：4800
- **Master Key**：`sk-my-master-key-1234`（config.yaml 中 `general_settings.master_key`）
- **数据库**：PostgreSQL 15，`localhost:5432/litellm`，128 个迁移已应用，8 个系统视图已创建
- **数据库连接**：`config.yaml` 中 `database_url` 已启用，Proxy 启动时自动执行 `prisma migrate deploy`

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
| `config.yaml` | LiteLLM 模型配置 + 代理设置 + database_url（已启用） |
| `start_proxy.py` | 启动脚本，自动加载 `.env`、补丁 Prisma CLI、启动 proxy |
| `test_call.py` | 虚拟 Key 自动化测试（7 步流程：连通性→生成→隔离→查询→更新→吊销→清理） |
| `test_glm.py` | 单独测试 GLM-5.1（含 `thinking: disabled` 参数） |
| `create_keys.py` | 虚拟 Key 管理工具（5 个子命令，见下文） |
| `setup_litellm_db.py` | 数据库初始化脚本（本地 PostgreSQL 方式） |
| `create_views.sql` | 8 个 LiteLLM 系统视图 SQL 定义 |

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
    base_url="http://localhost:4800/v1",
)

response = client.chat.completions.create(
    model="glm-5-1",          # 使用 config.yaml 中的 model_name
    messages=[{"role": "user", "content": "你好"}],
    max_tokens=50,
)
```

## 虚拟 Key 管理

`create_keys.py` 支持 5 个子命令：

| 子命令 | 用法 | 说明 |
|--------|------|------|
| `generate` | `py create_keys.py generate` | 预定义模板批量生成 / `--name --models --budget` 自定义生成 |
| `list` | `py create_keys.py list` | 列出所有虚拟 Key |
| `info` | `py create_keys.py info <key>` | 查询单个 Key 详情（用量、过期、模型范围） |
| `delete` | `py create_keys.py delete <key>` | 吊销 Key（支持 `--yes` 跳过确认） |
| `update` | `py create_keys.py update <key> --models ... --budget N` | 更新 Key 的模型范围或预算 |

预定义模板：
- **system-a**：仅 MiniMax，月预算 $10
- **system-b**：仅 DeepSeek，月预算 $20
- **system-c**：全部模型，无预算限制

> 注意：LiteLLM 1.87 的 API 与旧版有差异，`create_keys.py` 已适配 `/v2/key/info` 端点和 token 哈希列表格式。

## 已知问题

1. **线程警告**：关闭 Proxy 时可能出现 threading shutdown 异常，非关键问题。
2. **智谱模型**：使用 `openai/` provider + z.ai 端点（OpenAI 兼容模式），非 `zai/` native provider。如需切换 native 模式需改 `config.yaml`。
3. **Cost Map**：已通过 `.env` 中 `LITELLM_LOCAL_MODEL_COST_MAP=True` 启用本地 cost map，消除远程获取警告。
4. **Windows Prisma 兼容**：`start_proxy.py` 自动补丁 LiteLLM 源码中的 `subprocess.run` 调用（添加 `shell=True`），解决 Windows 下 `.cmd` 文件找不到的问题。
