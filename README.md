# BidInsight — 招采情报平台（BS 架构）

BidInsight 是一套面向多源公共门户的招标/采购信息采集、标准化、存储与分析平台。通过规则驱动的采集与清洗，构建可审计、可搜索、可视化的招采数据资产，支持市场扫描、行业对标、采购方画像与竞争对手监测，贴合政企业务场景。

> 目标：低运维成本、可持续运行、可观测、合规模块化设计。

---

## 核心能力

- 多源采集
  - 省市公共资源交易平台、行业与央企平台
  - 翻页、列表/详情解析、增量更新、断点续跑
- 反爬与稳健性
  - UA 随机、限流重试、代理池、抖动控制
  - 多选择器冗余与回退，容忍轻微 DOM 变动
- 标准化清洗
  - 标题/正文/预算/币种/采购人/代理/截止/区域/行业
  - 噪声去除、时间归一化、金额抽取（默认 CNY 映射）
- 去重与关联
  - 基于哈希的软去重（URL+标题+日期），跨批次关联
- 分析就绪
  - 时间趋势、区域/行业分布、预算分档
  - 采购方与供应商画像、关键词热点
- Web 看板（BS 架构）
  - 搜索/筛选/导出；趋势与分布图表、地图、Top-N
- 调度与监控
  - 类 Cron 调度、任务状态、失败告警（邮件/IM）
- 规则可扩展
  - 以 YAML/JSON 规则 + 站点适配器扩展新来源；爬取/解析/ETL 解耦

---

## 技术栈

- 前端：React + Vite + Ant Design（或可选 Vue）
- 后端：Python FastAPI（可选 NestJS）
- 采集：HTTPX/Requests + Playwright（按需无头浏览器）
- 调度：APScheduler / Celery（可选 Redis）
- 存储：PostgreSQL（推荐）或 MySQL
- 缓存/限流/队列：Redis（可选）
- 容器化：Docker / Docker Compose
- 日志与可观测：结构化 JSON 日志；可选 OpenTelemetry
- 鉴权：JWT，可对接企业 SSO

架构（高层）
- Web UI → API（认证/查询/导出）
- Crawler 工作者 → 清洗/去重 → DB
- Scheduler 触发任务
- 监控与告警 → Email/IM

---

## 目录结构（建议）

```
bidinsight/
├─ apps/
│  ├─ web/                # 前端（React）
│  └─ api/                # 后端（FastAPI）
├─ crawlers/              # 爬虫与站点适配
│  ├─ sites/              # 站点规则与解析器
│  ├─ pipelines/          # 清洗/去重/入库
│  └─ scheduler/          # 调度与编排
├─ configs/               # 全局配置与站点 YAML/JSON
├─ db/
│  ├─ migrations/         # 数据库迁移
│  └─ seeds/              # 初始化数据
├─ scripts/               # 运维脚本（备份、重建索引）
├─ docs/                  # 文档与接口规范
└─ docker/                # Docker 与 compose
```

---

## 快速开始

1) 环境依赖
- Python 3.10+
- Node.js 18+
- PostgreSQL 13+（或 MySQL 8）
- Redis（可选）
- Docker（可选）

2) 克隆仓库
```
git clone https://github.com/<your-org>/bidinsight.git
cd bidinsight
```

3) 后端（API）
```
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# 配置 .env（参考 .env.example）
alembic upgrade head
uvicorn main:app --reload
```

4) 前端（Web）
```
cd apps/web
pnpm i
pnpm dev
```

5) 爬虫与调度
```
cd crawlers
pip install -r requirements.txt
# 启动开发环境调度
python -m scheduler.run
# 调试单站点
python -m sites.sample_portal detail --since "2024-01-01"
```

6) Docker（可选）
```
docker compose up -d
```

---

## 数据模型（简化）

- tenders
  - id, source_site, source_url, title, notice_type
  - purchaser, agency, budget_amount, currency
  - province, city, industry, publish_time, deadline
  - content_text, attachments(json), hash_key, created_at, updated_at
- purchasers
- suppliers
- crawl_logs（状态、错误码、耗时、重试次数）
- tasks（作业记录与心跳）
- keywords_index（搜索/分析）

去重策略
- hash_key = hash(normalize(title) + publish_date + purchaser)
- 同步时软去重，保留最早记录并保留血缘

---

## 站点适配与解析

- 规则优先：configs/sites/*.yaml 定义列表入口、分页与详情选择器
- 代码回退：对 JS 重页面使用 Playwright
- 抽取策略
  - 标题：h1/h2 → meta og:title → 首段
  - 时间：正则 yyyy-mm-dd / yyyy年mm月dd日 → ISO8601
  - 金额：数值 + 默认 CNY，币种映射
  - 附件：绝对路径规范化与文件名清洗

反爬与韧性
- 限流 + 随机抖动（0.5–2.0s）
- UA 池、Accept-Language、时区提示
- 可选代理池；指数退避
- 多选择器回退 + 规则版本化

---

## 分析与可视化

- 时间趋势：按日/周公告数量与预算总额
- 区域：省/市 Top-N（数量/预算）
- 行业：建筑/软件/通信/安防等
- 采购方画像：频率与年度预算规模
- 关键词热点：TF-IDF/LLM 辅助主题标签
- 供应商监测（可选扩展）

前端页面
- 列表检索：关键词、日期范围、区域、预算、行业
- 详情页：正文/附件/来源/原文链接/相似项
- 仪表盘：ECharts/Recharts
- 导出：CSV/Excel（分页流式）

---

## API 示例（FastAPI）

- GET /api/tenders
  - q, start_date, end_date, province, industry, min_budget, max_budget, page, size
- GET /api/tenders/{id}
- POST /api/export
- GET /api/stats/trend
- GET /api/stats/distribution?dim=province|industry
- GET /api/health

认证（可选）
- POST /api/auth/login → JWT
- 导出与写操作需鉴权

---

## 运维与 SRE

- 调度：APScheduler Cron（如每 30 分钟增量）
- 监控：crawl_logs + 失败率阈值告警
- 重试：指数退避（1s/4s/16s，最多 3 次）
- 审计：解析记录规则 rule_id 与版本
- 备份：每日 DB dump；附件入对象存储

脚本示例
- scripts/backup_db.sh
- scripts/reindex_keywords.py
- scripts/deduplicate_tenders.py
- scripts/migrate_site_rules.py

---

## 合规与风险提示

- 尊重 robots 与站点条款，仅采集公开可访问内容
- 标注原始来源链接，避免对原文全文商业再分发
- 涉及个人信息时进行脱敏处理
- 温和抓取速率，避免对网站造成影响
- 企业部署建议：IP 白名单与操作审计

---

## 路线图

- v0.1：采集 + 标准化 + 入库 + 列表检索
- v0.2：可视化看板、导出、调度与告警
- v0.3：相似聚类与主题模型
- v0.4：采购方/供应商画像与竞品监测
- v0.5：LLM 摘要与意图标签（离线可选）

---

## 开发约定（Vibe 风格）

- 配置中心化：不在代码中硬编码站点规则，由 configs/sites 管理
- 模块解耦：crawl/parse/clean/load/analytics 分层
- 可观测：结构化日志 + trace_id
- 幂等：作业最小单元 = 站点 + 时间片
- 数据契约：OpenAPI + JSON Schema
- 可测试：解析与清洗单元测试
- 版本化：规则与解析器版本可回滚

---

## 许可证

BidInsight 采用 Apache License 2.0 开源。详见仓库 LICENSE 文件。
说明：第三方依赖遵循其各自许可证。

---

## 致谢与联系

- 维护方：<Yip King>
- 邮箱：<yejingcn@hotmail.com>
