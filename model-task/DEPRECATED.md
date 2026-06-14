# ⚠️ 此模块已废弃 (DEPRECATED)

> 废弃日期: 2026-06-14

## 说明

`model-task` 模块已废弃，所有功能已迁移至 `model-tracing/` 目录。

`model-tracing` 是 `model-task` 的升级版本，包含以下改进：
- 新增 3 个测试文件（`test_langfuse_write.py`、`test_minimax_e2e.py`、`test_minimax_trace.py`）
- `core/task.py` 代码完全一致
- `main.py` 有少量适配性修改
- 配置文件 `config/config.yaml` 略有调整

## 迁移指引

请使用 `model-tracing/` 目录下的代码，不要再修改或使用本目录。

```bash
# 正确的使用方式
cd model-tracing
python main.py
```

## 保留原因

不直接删除是为了保留 git 历史可追溯性。此目录不再维护，不再接收任何更新。
