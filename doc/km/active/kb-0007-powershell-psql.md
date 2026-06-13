---
id: kb-0007
title: PowerShell 中执行 psql SQL 查询的坑
category: 故障排查
tags: [PowerShell, PostgreSQL, psql, SQL, 引号转义]
platform: Windows
arch: x86_64
status: active
version: "PostgreSQL 15, PowerShell 5.1"
created_at: 2026-06-06
updated_at: 2026-06-06
author: Qoder
related: [kb-0003]
source: "实际排查 LiteLLM SpendLogs 数据时踩坑"
---

# PowerShell 中执行 psql SQL 查询的坑

> 在 Windows PowerShell 中通过 psql.exe 执行 SQL 时，双引号被 PowerShell 吞掉、引号嵌套冲突、stderr 触发 NativeCommandError 等问题，导致查询失败或报错。本文汇总所有踩坑及对应的解决方案。

## 环境信息

- **操作系统**：Windows 22H2
- **硬件架构**：x86_64
- **依赖版本**：PostgreSQL 15, PowerShell 5.1（Windows 自带版本，不支持 `&&`）

## 正文内容

### 问题一：双引号被 PowerShell 吞掉

**问题现象**：PostgreSQL 的表名如果包含大写字母（如 `"LiteLLM_SpendLogs"`），必须用双引号包裹。但 PowerShell 把双引号当作字符串定界符，传递给 psql 时引号丢失。

```powershell
# 尝试用 -c 传 SQL
& psql.exe -U litellm -d litellm -c 'SELECT * FROM "LiteLLM_SpendLogs"'
# 结果：psql 收到的是 SELECT * FROM LiteLLM_SpendLogs（双引号没了）
# 报错：关系 "litellm_spendlogs" 不存在（PG 自动转小写，找不到大写表名）
```

**原因分析**：PowerShell 的单引号字符串不会展开变量，但传给外部程序时，内部的双引号仍可能被外层解析吞掉。

**解决方案**：用 `-f` 参数读取 SQL 文件，彻底绕过命令行引号问题。

```powershell
# 推荐做法：写临时 SQL 文件，用 -f 执行
$sqlFile = "$env:TEMP\query.sql"
@"
SELECT model, COUNT(*) AS cnt
FROM "LiteLLM_SpendLogs"
GROUP BY model;
"@ | Set-Content $sqlFile -Encoding UTF8
& 'd:\Desktop\Test\MultiModel\pg15\pgsql\bin\psql.exe' `
    -U litellm -d litellm -h localhost -p 5432 `
    -f $sqlFile 2>&1 | Out-String
```

---

### 问题二：psql stderr 触发 PowerShell NativeCommandError

**问题现象**：即使 SQL 执行成功，psql 的 stderr 输出也会被 PowerShell 当作错误。

```powershell
# SQL 本身没问题，但 PowerShell 报错
& psql.exe -U litellm -d litellm -c "SELECT 1"
# 输出：psql.exe : 错误: ... NativeCommandError
#       FullyQualifiedErrorId: NativeCommandError
```

**原因分析**：PowerShell 把外部程序 stderr 的任何输出都当作错误流处理。psql 的提示信息（如中文编码乱码、连接提示）都会触发。

**解决方案**：用 `2>&1` 合并流 + `Out-String` 捕获完整输出。

```powershell
& psql.exe -U litellm -d litellm -f $sqlFile 2>&1 | Out-String
```

---

### 问题三：PowerShell 不支持 `&&`

**问题现象**：多条命令用 `&&` 连接报错。

```powershell
cd d:\Desktop\Test\MultiModel && py scripts\update_cost_map.py
# 报错：&& 运算符未在 PowerShell 5.1 中实现
```

**原因分析**：`&&` 是 PowerShell 7+ 的特性，Windows 自带的 5.1 不支持。

**解决方案**：用分号 `;` 分隔。

```powershell
cd d:\Desktop\Test\MultiModel; py scripts\update_cost_map.py
```

---

### 问题四：表名列名大小写混乱

**问题现象**：LiteLLM 的表名用 PascalCase（如 `LiteLLM_SpendLogs`），列名用 camelCase（如 `startTime`）。直接写 SQL 时容易搞混。

```sql
-- 错误写法（不加引号，PG 自动转小写）
SELECT start_time FROM LiteLLM_SpendLogs;
-- 报错：字段 "start_time" 不存在
-- 提示：也许您想要引用列"LiteLLM_SpendLogs.startTime"?
```

**原因分析**：PostgreSQL 对未加引号的标识符自动转小写。但 LiteLLM 建表时用了引号保护大小写，所以查询时也必须加引号。

**解决方案**：记住 LiteLLM 的命名规则。

| 类型 | 规则 | 示例 |
|------|------|------|
| 表名 | PascalCase，需双引号 | `"LiteLLM_SpendLogs"` |
| 列名 | camelCase，需双引号 | `"startTime"` |
| SQL 关键字 | 不加引号 | `SELECT`, `WHERE`, `COUNT(*)` |

---

### 问题五：CMD 调用转义地狱

**问题现象**：尝试用 `cmd /c` 包裹 psql 命令，遇到多层引号转义地狱。

```powershell
# 尝试用 cmd 转义
cmd /c "psql -c ""SELECT * FROM \""LiteLLM_SpendLogs\"""""
# 结果：引号嵌套混乱，报错或被安全策略拦截
```

**解决方案**：不要用 `cmd /c`，直接用 `-f` 文件方式。

---

## 推荐做法汇总

### 万能模板：用 SQL 文件执行

```powershell
# 1. 准备 SQL（here-string 里随便写，不用担心引号）
$sqlFile = "$env:TEMP\query.sql"
@'
SELECT
  model,
  COUNT(*) AS total_requests,
  SUM(prompt_tokens) AS total_input,
  SUM(completion_tokens) AS total_output,
  SUM(prompt_tokens + completion_tokens) AS total_tokens
FROM "LiteLLM_SpendLogs"
GROUP BY model
ORDER BY total_requests DESC;
'@ | Set-Content $sqlFile -Encoding UTF8

# 2. 执行（注意 psql.exe 路径换成自己的）
& 'd:\Desktop\Test\MultiModel\pg15\pgsql\bin\psql.exe' `
    -U litellm -d litellm -h localhost -p 5432 `
    -f $sqlFile 2>&1 | Out-String
```

### 速查：PowerShell 调用 psql 的正确姿势

| 场景 | 用法 |
|------|------|
| 执行 SQL 文件 | `& psql.exe -f $sqlFile 2>&1 \| Out-String` |
| 命令行传简单 SQL（无大写标识符） | `& psql.exe -c 'SELECT 1' 2>&1 \| Out-String` |
| 命令行传含引号的 SQL | **不要用 -c，用 -f 文件方式** |
| 多条命令连接 | 用 `;` 不用 `&&` |

---

## 常见问题

**Q：为什么不用 `psql` 的交互模式？**
A：PowerShell 与 psql 交互模式兼容性差（中文乱码、控制台编码冲突），非交互式 `-f` 更可靠。

**Q：为什么要用 `&` 调用 psql.exe？**
A：PowerShell 中执行路径含特殊字符或扩展名的程序时，需要用调用运算符 `&`。

**Q：SQL 文件编码有要求吗？**
A：用 `Set-Content -Encoding UTF8` 写入即可，psql 能正确识别。

## 相关词条

- [[kb-0003]] PowerShell 常用命令

## 变更记录

| 日期 | 变更内容 | 作者 |
|---|---|---|
| 2026-06-06 | 创建 | Qoder |
