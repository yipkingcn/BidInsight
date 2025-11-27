# Stage 1 — 南网站点采集笔记

## 日常操作指南（必读）

### 0. 准备工作
每次打开新终端窗口运行脚本前，**必须先进入虚拟环境**：
```bash
source .venv/bin/activate
```
*成功标志：命令行开头出现 `(.venv)` 字样。*

### 1. 运行采集的两种方式

**方式一：批量采集（推荐）**
读取 `configs/keywords/csg_units.txt` 中的 17 家单位名单进行采集：
```bash
python crawlers/sites/csg_bidding.py \
  --keywords-file configs/keywords/csg_units.txt \
  --since 2024-11-15 \
  --max-pages 5 \
  --with-detail
```
*说明：不指定 `--output` 时，结果会自动保存到 `data_csv/` 目录下，文件名包含当前时间戳。*

**方式二：单点采集**
仅查询特定的一家单位（适合临时验证）：
```bash
python crawlers/sites/csg_bidding.py \
  --keyword "南方电网数字电网集团有限公司" \
  --max-pages 1 \
  --with-detail
```

---

## 接口与开发笔记

- 环境：`.venv` + `pip install 'httpx[http2]' pydantic python-dotenv rich tenacity`（已写入 `requirements.txt`）。
- 当前聚焦站点：https://ecsg.com.cn/cms/NoticeList.html?id=1-1&typeid=4&word=&seacrhDate=
- 列表接口：`POST https://ecsg.com.cn/api/tender/tendermanage/gatewayNoticeQueryController/queryGatewayNoticeListPagination`
  - Headers：`Content-Type: application/json;charset=UTF-8`、`Origin/Referer` 指向 `ecsg.com.cn`，`X-Requested-With: XMLHttpRequest`
  - Body 模板：
    ```json
    {"projectLevel1ClassifyId":"1","noticeType":"1","noticeTitle":"","publishTime":"","organizationInfoName":"","pageNo":1,"pageSize":20}
    ```
- 详情接口：
  - `POST https://ecsg.com.cn/api/tender/tendermanage/gatewayNoticeQueryController/getCahSwitch` → 返回 bool，需在调用 `getNotice` 时带上 `cahSwitch`。
  - `POST https://ecsg.com.cn/api/tender/tendermanage/gatewayNoticeQueryController/getNotice`，Body：`{"objectId":"<objectId>","objectType":"1","cahSwitch":true}`
  - 附件：`POST https://ecsg.com.cn/api/tender/tendermanage/gatewayNoticeQueryController/getNoticeAttachmentInfo`，Body：`{"objId":"<objectId>"}`。
- 下一步任务：
  1. 继续整理 `objectType`、`noticeType` 对应含义，补充常见异常码处理。
  2. 在 `sgcc_supply.py` 中扩展 `--with-detail/--standardize` 逻辑，沉淀标准字段（预算、采购人、附件列表）。
  3. 验证命令：`python crawlers/sites/sgcc_supply.py --max-pages 1 --with-detail --standardize --output exports/sgcc_sample.jsonl`，确认输出 20 条且 JSONL 可复用。

URL:https://ecsg.com.cn/api/tender/tendermanage/gatewayNoticeQueryController/queryGatewayNoticeListPagination

## 2025-11-18 工作记录

- 完成 `sgcc_supply.py` 详情抓取与标准化输出，新增 `--detail-keyword`、`--with-detail`、`--standardize` 等参数，可生成 JSONL（示例：`python crawlers/sites/sgcc_supply.py --max-pages 1 --with-detail --standardize --output exports/sgcc_sample.jsonl`）。
- 新增 `crawlers/sites/csg_bidding.py`，支持通过 `https://www.bidding.csg.cn/dbsearch.jspx` 抓取“南方电网供应链统一服务平台”公告，示例命令：  
  `python crawlers/sites/csg_bidding.py --keyword '南方电网数字电网集团有限公司' --since 2024-11-15 --max-pages 5 --with-detail --output exports/csg_data_sec_2024.jsonl`
- 页面解析要点：列表位于 `div.List2 > li`，详情正文在 `div.Content`，发布时间可从 `<span class="Black14 Gray">` 解析；分页通过 `pageNo` 参数循环。
- 批量名单整理：根据客户提供截图，新增 `configs/keywords/csg_units.txt`，包含 17 家重点单位（储能、供应链、数字电网等）。脚本运行会在输出中新增 `source_keyword` 字段，方便按单位汇总。
- 数据持久化（2025-11-23）：
  - 新建 `data_csv` 目录用于存放采集结果。
  - 优化 `csg_bidding.py`，支持自动生成 CSV 文件。若不指定 `--output`，脚本将自动在 `data_csv/` 下生成以当前时间命名的 CSV 文件（如 `20251123_200500.csv`），且自动处理 HTTP 500 错误跳过无效页面。
- 稳定性优化（2025-11-23）：
  - 针对详情页频繁 500 错误，引入 `tenacity` 重试机制（指数退避）和随机延迟（0.5~1.5s）。
  - 增强 Headers 伪装，补充 `Sec-Ch-Ua`、`Accept-Language` 等浏览器指纹字段，降低反爬风控触发率。
- 字段提取优化（2025-11-23）：
  - 针对详情页解析，增加精准字段提取逻辑，优先从下划线内容抓取“招标人”、“项目名称”、“项目编号”及关键时间节点，正则表达式兜底。
  - 优化 CSV 输出格式，仅保留客户指定的 7 列（招标人、项目名称、项目编号、招标文件获取时间、招标文件截止时间、开标时间、招标公告网址），提升数据可用性。

## 2025-11-24 工作记录

- **数据质量优化**：
  - **去噪**：增加列表页过滤逻辑，仅抓取“招标公告”和“非招标公告”，自动剔除“中标候选人公示”、“结果公告”等冗余数据，解决项目重复和编号缺失问题。
  - **规范化**：所有日期字段强制格式化为 `YYYY-MM-DD`，去除不需要的时分秒信息。
  - **数据补全**：针对部分项目编号抓取失败的情况（如 URL 1200415018），增加对“招标编号”、“采购编号”等变体关键字的识别支持。
- **字段扩展**：
  - 新增“采购方式”列（CSV 第4列）。逻辑优化为：优先识别“非招标公告”标记为“非公开招标”，否则若包含“招标公告”则标记为“公开招标”。
- **兼容性增强**：
  - 针对非招标公告的特殊格式（如使用“采购编号”、“采购人为”），扩展了正则提取规则，确保关键信息不遗漏。

### 常见问题（FAQ）

**Q: 运行脚本提示 `zsh: permission denied: .venv/bin/activate`？**
A: 这是因为试图直接执行激活脚本。正确做法是使用 `source` 命令加载它：
```bash
source .venv/bin/activate
```

### 批量采集（2025-11-23 更新）

- 新增 `configs/keywords/csg_units.txt` 储存截图中的 17 个单位名称，可与 `csg_bidding.py` 的 `--keywords-file` 配合批量抓取。
- 命令示例（自动保存到 data_csv）：
  ```bash
  python crawlers/sites/csg_bidding.py \
    --keywords-file configs/keywords/csg_units.txt \
    --since 2024-11-15 \
    --max-pages 5 \
    --with-detail
  ```
  执行后将在 `data_csv/` 目录下生成类似 `20251123_xxxxxx.csv` 的文件。  
  ```
  python crawlers/sites/csg_bidding.py \
    --keywords-file configs/keywords/csg_units.txt \
    --since 2024-11-15 \
    --max-pages 5 \
    --with-detail \
    --output exports/csg_units_2024.jsonl
  ```
- 输出记录会新增 `source_keyword` 字段，标识来源单位，方便后续筛选和汇总。

## 2025-11-27 工作记录 — AI 智能分析功能

### 功能概述
新增基于 **LangChain + OpenAI GPT** 的项目内容智能分析功能，可自动从招标公告详情页提取：
- 项目建设内容概述
- 项目预算金额（自动归一化为万元）
- 分包信息（如有多个标包）
- 每个分包的具体内容和金额

### 核心模块

1. **分析器模块 (`analyzers/project_analyzer.py`)**
   - `ProjectAnalyzer`: 核心分析器类，封装了 LangChain 调用逻辑
   - `ProjectAnalysis`: 结构化的分析结果模型
   - `PackageInfo`: 分包信息模型
   - 支持从 HTML 中自动提取"2. 项目概况和招标/采购范围"部分
   - 智能识别各种金额表述（"元"、"万元"、"千元"、"亿元"）并统一转换为万元

2. **独立分析工具 (`analyze_projects.py`)**
   - 可读取 `csg_bidding.py` 生成的 CSV 文件
   - 批量分析每个项目的详情页
   - 输出增强版 CSV，包含 AI 提取的建设内容和金额信息
   - 使用示例：
     ```bash
     # 设置环境变量
     export OPENAI_API_KEY="your-api-key"
     export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选
     
     # 分析已采集的项目
     python analyze_projects.py data_csv/20251126_215926.csv
     
     # 仅分析前5条（测试用）
     python analyze_projects.py data_csv/20251126_215926.csv -n 5
     
     # 指定输出路径
     python analyze_projects.py data_csv/20251126_215926.csv -o results/analyzed.csv
     ```

3. **测试脚本 (`test_analyzer.py`)**
   - 快速验证分析器功能的简单脚本
   - 使用内置示例文本测试提取效果

### 输出格式
增强后的 CSV 包含以下新增列：
- **整体建设内容**: AI 提取的项目概述（50-200字）
- **整体金额（万元）**: 项目总预算（自动归一化）
- **是否有分包**: "是"或"否"
- **分包数量**: 分包个数
- **分包详情**: JSON 格式的分包列表（包名、内容、金额）

### 技术要点
- **金额归一化**: 自动识别并转换"元"、"千元"、"万元"、"亿元"为统一的万元单位
- **智能提取**: 默认使用 Kimi moonshot-v1-8k，采用 temperature=0.0 确保输出稳定
- **分包识别**: 可识别"第一包"、"标包1"、"包1"等多种分包表述
- **容错处理**: 对无法提取或分析失败的项目标注错误信息，不中断整体流程

### 配置说明

**默认使用 Kimi（月之暗面）大模型**

1. 获取 API Key：访问 https://platform.moonshot.cn/console/api-keys
2. 复制 `env.example` 为 `.env` 并填写：

```bash
cp env.example .env
# 编辑 .env 文件，填入：
# OPENAI_API_KEY=sk-your-kimi-key
# OPENAI_BASE_URL=https://api.moonshot.cn/v1
```

**优势**：
- 🇨🇳 国内访问无需翻墙，速度快
- 💰 价格优惠（约 ¥12/百万tokens）
- 🎯 中文理解优秀

详细配置见：`docs/KIMI_SETUP.md`

### 依赖更新
新增依赖已写入 `requirements.txt`：
- `langchain`
- `langchain-openai`
- `langchain-community`
- `openai`
- `tiktoken`
- 及相关传递依赖

