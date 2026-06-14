-- LiteLLM 缺失视图创建脚本
-- 从 create_views.py 提取，手动执行以绕过中文 locale 匹配问题

-- 1. VerificationTokenView（核心：Key 验证依赖此视图）
CREATE VIEW "LiteLLM_VerificationTokenView" AS
SELECT
v.*,
t.spend AS team_spend,
t.max_budget AS team_max_budget,
t.tpm_limit AS team_tpm_limit,
t.rpm_limit AS team_rpm_limit,
p.project_alias AS project_alias
FROM "LiteLLM_VerificationToken" v
LEFT JOIN "LiteLLM_TeamTable" t ON v.team_id = t.team_id
LEFT JOIN "LiteLLM_ProjectTable" p ON v.project_id = p.project_id;

-- 2. MonthlyGlobalSpend
CREATE OR REPLACE VIEW "MonthlyGlobalSpend" AS
SELECT
DATE("startTime") AS date,
SUM("spend") AS spend
FROM
"LiteLLM_SpendLogs"
WHERE
"startTime" >= (CURRENT_DATE - INTERVAL '30 days')
GROUP BY
DATE("startTime");

-- 3. Last30dKeysBySpend
CREATE OR REPLACE VIEW "Last30dKeysBySpend" AS
SELECT
L."api_key",
V."key_alias",
V."key_name",
SUM(L."spend") AS total_spend
FROM
"LiteLLM_SpendLogs" L
LEFT JOIN
"LiteLLM_VerificationToken" V
ON
L."api_key" = V."token"
WHERE
L."startTime" >= (CURRENT_DATE - INTERVAL '30 days')
GROUP BY
L."api_key", V."key_alias", V."key_name"
ORDER BY
total_spend DESC;

-- 4. Last30dModelsBySpend
CREATE OR REPLACE VIEW "Last30dModelsBySpend" AS
SELECT
"model",
SUM("spend") AS total_spend
FROM
"LiteLLM_SpendLogs"
WHERE
"startTime" >= (CURRENT_DATE - INTERVAL '30 days')
AND "model" != ''
GROUP BY
"model"
ORDER BY
total_spend DESC;

-- 5. MonthlyGlobalSpendPerKey
CREATE OR REPLACE VIEW "MonthlyGlobalSpendPerKey" AS
SELECT
DATE("startTime") AS date,
SUM("spend") AS spend,
api_key as api_key
FROM
"LiteLLM_SpendLogs"
WHERE
"startTime" >= (CURRENT_DATE - INTERVAL '30 days')
GROUP BY
DATE("startTime"),
api_key;

-- 6. MonthlyGlobalSpendPerUserPerKey
CREATE OR REPLACE VIEW "MonthlyGlobalSpendPerUserPerKey" AS
SELECT
DATE("startTime") AS date,
SUM("spend") AS spend,
api_key as api_key,
"user" as "user"
FROM
"LiteLLM_SpendLogs"
WHERE
"startTime" >= (CURRENT_DATE - INTERVAL '30 days')
GROUP BY
DATE("startTime"),
"user",
api_key;

-- 7. DailyTagSpend
CREATE OR REPLACE VIEW "DailyTagSpend" AS
SELECT
    jsonb_array_elements_text(request_tags) AS individual_request_tag,
    DATE(s."startTime") AS spend_date,
    COUNT(*) AS log_count,
    SUM(spend) AS total_spend
FROM "LiteLLM_SpendLogs" s
GROUP BY individual_request_tag, DATE(s."startTime");

-- 8. Last30dTopEndUsersSpend
CREATE VIEW "Last30dTopEndUsersSpend" AS
SELECT end_user, COUNT(*) AS total_events, SUM(spend) AS total_spend
FROM "LiteLLM_SpendLogs"
WHERE end_user <> '' AND end_user <> user
AND "startTime" >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY end_user
ORDER BY total_spend DESC
LIMIT 100;
