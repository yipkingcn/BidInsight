# BidInsight — 招采情报平台（BS 架构）

BidInsight 是一套面向多源公共门户的招标/采购信息采集、标准化、存储与分析平台。通过规则驱动的采集与清洗，构建可审计、可搜索、可视化的招采数据资产，支持市场扫描、行业对标、采购方画像与竞争对手监测，贴合政企业务场景。本 README 现已针对「广东移动客户经理」角色做了学习导向设计，可作为系统性学习资料。

> 目标：低运维成本、可持续运行、可观测、合规模块化设计；同时让业务同学能按 Learning Path 循序渐进掌握招采数据采集技能。

---

## 学习目标与角色背景

- **角色定位**：广东移动政企客户经理，需要掌握省市公共资源交易、央企集采等门户的公告获取方式，为客户拜访和商机挖掘提供数据支持。
- **核心诉求**
  - 快速理解国内主要招标门户结构、开放程度与反爬规则。
  - 从零搭建可运行的爬虫脚本，优先聚焦广东区域、通信/ICT 类招标。
  - 学会将数据清洗、去重、入库，并产出基础分析看板。
- **达成标准**
  1. 能独立编写并调试至少 1 个目标站点的采集脚本。
  2. 能解释采集→清洗→入库→分析的端到端流程。
  3. 能输出一份包含来源、时间、金额、采购人等字段的周度情报报告。

---

## 学习路线概览（Step-by-step）

| 阶段 | 关键词 | 产出 | 推荐学习时长 |
| --- | --- | --- | --- |
| 阶段 0 | 行业与站点映射 | 自己的站点清单、优先级矩阵 | 0.5 天 |
| 阶段 1 | 环境搭建 & 第一个爬虫 | 可运行的样例爬虫 + 抓取日志 | 1 天 |
| 阶段 2 | 反爬与稳健性 | 支持翻页、断点续跑的采集任务 | 1.5 天 |
| 阶段 3 | 清洗与模型 | 标准化字段 + 去重策略 | 1 天 |
| 阶段 4 | 存储与分析 | 可检索数据库 + 基础统计报表 | 1 天 |
| 阶段 5 | 可视化与运维 | 看板原型 + 调度监控方案 | 1 天 |

> 建议配合 `docs/learning/`（可自行新增）记录过程，每阶段完成后复盘「会了什么、卡在哪」。

---

## 阶段化学习笔记

### 阶段 0：行业与站点认知

- **目标**：搞清楚要采的门户、数据结构与发布节奏，为后续开发确定优先级。
- **关键实践**
  1. 列出广东省级（如广东省公共资源交易中心）、地市级（广州、深圳等）、央企（中国移动采购与招标网、中国政府采购网）等站点 URL。
  2. 观察列表页与详情页结构，记录分页参数、公告字段、附件格式。
  3. 分析 robots / 访问门槛，标注是否需要登录、验证码。
- **输出**：`docs/site_matrix.xlsx`（或 Notion），包含站点、行业、优先级（高/中/低）、难度、反爬要点。

### 阶段 1：环境搭建与第一个爬虫

- **目标**：本地跑通一个采集脚本，熟悉代码结构。
- **关键实践**
  1. 按 “快速开始” 小节准备 Python/Node/Postgres 环境，创建 `.env`。
  2. 在 `crawlers/sites/` 下新增 `gd_prc.py`（示例名称），实现：
     - 获取最新一页列表；
     - 解析标题、公告时间、预算、采购人；
     - 打印/保存 JSON。
  3. 使用 `python -m sites.gd_prc list --since "2024-01-01"` 验证输出，观察日志。
- **建议资料**
  - requests/httpx 官方文档
  - Playwright Python 快速上手（若站点大量 JS 渲染）
- **阶段完成标志**：命令可稳定返回至少 20 条结构化记录，并附上 `notes/stage1.md` 记录经验。

### 阶段 2：反爬策略与稳健采集

- **目标**：让爬虫具备翻页、重试、断点续跑能力，面对轻度反爬仍可运行。
- **关键实践**
  1. 引入 `crawlers/pipelines/common.py` 中的限流、重试组件（如尚未实现可根据 README 自建）。
  2. 实现分页循环，支持 `--max-pages`、`--resume-from` 等参数。
  3. 为易变 DOM 的站点准备多套 CSS/XPath 选择器，实验 UA 列表、随机等待。
  4. 日志落盘（`logs/crawl.log`），记录成功/失败、响应时间。
- **阶段完成标志**：一次运行可抓取近 7 天数据（>=200 条），失败率 <5%，并能讲清楚你使用的反爬策略。

### 阶段 3：标准化清洗与去重

- **目标**：把原始字段映射到统一 schema，解决重复公告问题。
- **关键实践**
  1. 在 `crawlers/pipelines/clean.py`（或新建）实现字段标准化：标题清洗、时间格式化（统一 ISO8601）、金额识别（正则 + 单位换算）。
  2. 设计 `hash_key = hash(normalize(title) + publish_date + purchaser)` 并在入库前判断是否已存在。
  3. 记录血缘：来源站点、抓取时间、解析规则版本。
- **阶段完成标志**：导出样例 CSV（`exports/sample_clean.csv`），字段齐全且无明显重复。

### 阶段 4：存储、检索与分析

- **目标**：搭建可用的数据库与查询 API，为业务检索和统计准备。
- **关键实践**
  1. 参考 “数据模型” 小节创建 `tenders`、`purchasers` 等表，使用 Alembic 生成迁移。
  2. 在 FastAPI (`apps/api`) 中实现 `GET /api/tenders`、`GET /api/stats/trend` 等接口。
  3. 编写 `notebooks/analysis.ipynb`（可新增）计算周度数量、预算区间、Top 采购人。
- **阶段完成标志**：可通过 API 查询到阶段 3 生成的数据，并附带基础统计截图。

### 阶段 5：可视化与运维

- **目标**：把数据搬到看板并具备调度、告警方案。
- **关键实践**
  1. 前端 `apps/web` 使用 Ant Design + ECharts 构建列表检索、仪表盘原型。
  2. 配置 APScheduler / Celery 实现 cron 式增量采集，设置失败重试与告警（邮件/企业微信）。
  3. 编写运维脚本（`scripts/backup_db.sh`、`scripts/replay_failed_jobs.py`）确保可恢复性。
- **阶段完成标志**：展示 Demo（本地或内网），并有“调度日历 + 告警说明”文档。

> **建议学习顺序**：阶段 0 → 1 → 2（重点）→ 3 → 4 → 5。若时间有限，先完成阶段 0-3，即可具备稳定抓取与清洗能力。

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

## 快速开始

1) 环境依赖
- Python 3.10+
- Node.js 18+ (可选，用于前端)
- PostgreSQL 13+ (可选，用于后续存储)

2) 克隆仓库 & 安装依赖
```bash
git clone https://github.com/<your-org>/bidinsight.git
cd bidinsight

# 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装项目依赖
pip install -r requirements.txt
```

3) 运行爬虫（实战）

**场景 A：南方电网供应链（批量采集）**
读取 `configs/keywords/csg_units.txt` 中的单位列表，抓取近 7 天的招标/非招标公告，并生成 CSV 报表：
```bash
python crawlers/sites/csg_bidding.py \
  --keywords-file configs/keywords/csg_units.txt \
  --since 2024-11-15 \
  --max-pages 5 \
  --with-detail
```
> 结果自动保存在 `data_csv/` 目录下，文件名为 `YYYYMMDD_HHMMSS.csv`。

**场景 B：南方电网供应链（单点验证）**
```bash
python crawlers/sites/csg_bidding.py \
  --keyword "南方电网数字电网集团有限公司" \
  --with-detail
```

**场景 C：国网新一代电子商务平台**
```bash
python crawlers/sites/sgcc_supply.py \
  --max-pages 1 \
  --with-detail \
  --standardize \
  --output exports/sgcc_sample.jsonl
```

4) AI 智能分析（新功能）✨

**前置条件：配置 Kimi API（推荐）**
```bash
# 1. 获取 API Key
# 访问 https://platform.moonshot.cn/console/api-keys

# 2. 复制配置模板
cp env.example .env

# 3. 编辑 .env 文件，填入你的 API Key
# OPENAI_API_KEY=sk-your-kimi-key
# OPENAI_BASE_URL=https://api.moonshot.cn/v1
```

> 💡 **为什么选择 Kimi？** 国内访问稳定快速，价格优惠，中文理解优秀。详见 [Kimi 配置指南](docs/KIMI_SETUP.md)

**场景 D：批量分析项目内容**
对已采集的 CSV 文件进行 AI 分析，提取建设内容和金额：
```bash
# 设置环境变量（或在 .env 中配置）
export OPENAI_API_KEY="sk-your-kimi-key"
export OPENAI_BASE_URL="https://api.moonshot.cn/v1"

# 分析所有项目
python analyze_projects.py data_csv/20251126_215926.csv

# 仅分析前 5 条（测试用）
python analyze_projects.py data_csv/20251126_215926.csv -n 5

# 指定输出路径
python analyze_projects.py data_csv/20251126_215926.csv -o results/analyzed.csv
```

**场景 E：快速测试分析器**
```bash
python test_analyzer.py
```

5) 前端与后端（开发中）
*详见 `apps/` 目录下的说明*

---

## 当前功能 (v0.2)

### 1. 南方电网供应链爬虫 (`csg_bidding.py`)
- **数据源**: [bidding.csg.cn](https://www.bidding.csg.cn)
- **核心特性**:
  - **批量采集**: 支持从文件读取多个关键词循环采集。
  - **智能解析**: 自动识别"招标公告"与"非招标公告"，提取项目编号、招标人、预算、关键时间节点。
  - **数据清洗**: 自动去除"中标公示"等冗余数据，统一日期格式为 `YYYY-MM-DD`。
  - **抗干扰**: 内置指数退避重试机制与随机延迟，模拟真实浏览器行为。
  - **CSV 导出**: 自动生成业务所需的 9 列标准报表（招标人、项目单位、项目名称、项目编号、采购方式等）。

### 2. 国网电子商务平台爬虫 (`sgcc_supply.py`)
- **数据源**: [ecsg.com.cn](https://ecsg.com.cn)
- **核心特性**:
  - 基于 JSON API 的高效采集。
  - 支持详情页正文与附件元数据提取。
  - 标准化 JSONL 输出。

### 3. AI 项目内容分析器 (`analyze_projects.py`) ✨ 新增
- **核心能力**: 使用 LangChain + OpenAI GPT 对招标项目进行智能分析
- **核心特性**:
  - **智能提取**: 自动从"2. 项目概况和招标/采购范围"中提取建设内容概述。
  - **金额归一化**: 智能识别并转换"元"、"千元"、"万元"、"亿元"为统一的万元单位。
  - **分包识别**: 自动识别并提取多个标包的详细信息（包名、内容、金额）。
  - **批量处理**: 可批量分析已采集的 CSV 文件中的所有项目。
  - **增强输出**: 在原 CSV 基础上新增"整体建设内容"、"整体金额（万元）"、"是否有分包"、"分包数量"、"分包详情"等列。
- **使用场景**: 快速了解项目核心内容和预算规模，辅助商机判断和投标决策。

---

## 目录结构

```
bidinsight/
├─ analyzers/             # AI 分析模块 ✨ 新增
│  ├─ __init__.py
│  └─ project_analyzer.py # [核心] LangChain 项目内容分析器
├─ apps/                  # (预留) 前后端应用
├─ configs/               # 配置文件
│  └─ keywords/           # 关键词列表
│     └─ csg_units.txt    # 南网重点单位清单
├─ crawlers/              # 爬虫核心代码
│  └─ sites/
│     ├─ csg_bidding.py   # [核心] 南网爬虫
│     └─ sgcc_supply.py   # [核心] 国网爬虫
├─ data_csv/              # [自动生成] CSV 结果输出目录
├─ exports/               # [自动生成] JSONL/调试数据输出目录
├─ docs/                  # 文档
├─ notes/                 # 开发日志
│  └─ stage1.md           # 阶段 1 详细操作指南
├─ analyze_projects.py    # [工具] AI 批量分析脚本 ✨ 新增
├─ test_analyzer.py       # [工具] 分析器测试脚本 ✨ 新增
├─ env.example            # 环境变量配置模板 ✨ 新增
├─ .gitignore
├─ requirements.txt
└─ README.md
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
