# LiteLLM Cost Map 机制与告警消除方案

## 一、Cost Map 是什么

LiteLLM 维护一个 `model_prices_and_context_window.json`，包含所有支持模型的定价（input/output cost per token）和上下文窗口信息。该文件仅在 LLM 响应返回后、在 `try/catch` 块内用于**计算花费**，不在请求路径上，永远不会阻塞 LLM 调用。

## 二、加载机制

```
import litellm
  └─ get_model_cost_map(url)
       ├─ LITELLM_LOCAL_MODEL_COST_MAP=True? ───→ 使用本地备份（无警告）
       └─ 否则
            ├─ fetch_remote_model_cost_map(url) ───→ 成功：使用远程版本
            └─ 失败 ───→ WARNING + 回退本地备份
```

- **远程 URL**：`https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json`
- **本地备份**：`site-packages/litellm/model_prices_and_context_window_backup.json`（随 pip 包发布）

源码位置：`litellm/litellm_core_utils/get_model_cost_map.py`（v1.84.0）

## 三、警告产生原因

```
LiteLLM:WARNING: Failed to fetch remote model cost map from
https://raw.githubusercontent.com/...: [Errno 11004] getaddrinfo failed.
Falling back to local backup.
```

| 触发条件 | 典型场景 |
|----------|----------|
| `getaddrinfo failed` | 网络不通 / DNS 不可达 GitHub |
| `JSONDecodeError` | 远程 JSON 格式损坏（上游错误） |
| 完整性校验失败 | 远程版本模型数显著缩水 |

回退到本地备份后，**功能完全正常**，仅缺失包版本之后新增模型的定价数据（cost=0）。

## 四、解决方案

本方案采用 **手动更新本地备份 + 跳过远程 fetch** 的策略，一劳永逸消除警告。

### 4.1 环境变量

`.env` 中已配置：

```
LITELLM_LOCAL_MODEL_COST_MAP=True
```

此变量指示 LiteLLM 完全跳过远程 fetch，直接使用本地备份文件。**该路径不会产生任何 WARNING 日志**。

### 4.2 手动更新脚本

`scripts/update_cost_map.py` 用于保持本地备份文件与上游同步。

```powershell
# 下载最新 JSON 并更新本地备份
python scripts/update_cost_map.py

# 仅下载校验，不写入（测试用）
python scripts/update_cost_map.py --dry-run

# 从 .bak 恢复原始备份
python scripts/update_cost_map.py --restore
```

**脚本行为**：

1. 自动检测系统代理（优先 `HTTPS_PROXY` 环境变量，否则探测本地 7897/10808 端口）
2. 从 GitHub raw URL 下载最新 JSON
3. 校验合法性（dict 类型、非空、模型数 ≥ 100）
4. 备份原文件为 `.bak`
5. 写入目标文件

### 4.3 更新频率

按需执行即可。建议：
- 升级 `litellm` pip 包后执行一次（新版包内置的备份可能更新）
- 需要最新模型定价时执行

> pip 升级 litellm 会覆盖本地备份文件为包内置版本，之后需重新运行脚本。

## 五、涉及文件

| 文件 | 作用 |
|------|------|
| `.env` | `LITELLM_LOCAL_MODEL_COST_MAP=True` 跳过远程 fetch |
| `scripts/update_cost_map.py` | 手动下载最新 JSON，覆盖本地备份 |
| `site-packages/litellm/model_prices_and_context_window_backup.json` | 被更新目标 |
| `site-packages/litellm/model_prices_and_context_window_backup.json.bak` | 更新前自动备份 |

## 六、常见问题

**Q：设置了 `LITELLM_LOCAL_MODEL_COST_MAP=True` 后 cost 计算会不准吗？**

A：只要本地备份文件包含对应模型的数据，cost 计算完全准确。只有备份中不存在的**新模型**才会 cost=0。定期运行 `update_cost_map.py` 即可保持同步。

**Q：脚本下载失败怎么办？**

A：脚本会自动保留原文件，不会损坏现有备份。如果代理不可用，可以手动从 GitHub 下载 JSON 放到对应路径。

**Q：这个警告在其他模块（model-tracing、model-eval）也会出现吗？**

A：只要 `import litellm` 就会触发，`.env` 中的环境变量对项目内所有模块生效。
