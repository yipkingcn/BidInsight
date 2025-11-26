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

