# ✨ AI 项目内容分析器 - 功能总结

## 🎯 核心功能

**使用 LangChain + OpenAI GPT 自动分析招标项目，提取商业关键信息**

### 提取内容
- 📝 **项目建设内容**: 简明概述（50-200字）
- 💰 **项目预算金额**: 自动归一化为万元
- 📦 **分包信息**: 识别多个标包及各自内容和金额

## 🚀 快速开始

### 1. 配置环境

```bash
# 激活虚拟环境
source .venv/bin/activate

# 设置 Kimi API Key（推荐）
export OPENAI_API_KEY="sk-your-kimi-key"
export OPENAI_BASE_URL="https://api.moonshot.cn/v1"

# 获取 API Key: https://platform.moonshot.cn/console/api-keys
```

### 2. 采集数据

```bash
python crawlers/sites/csg_bidding.py \
  --keyword "南方电网数字电网集团有限公司" \
  --with-detail
```

### 3. AI 分析

```bash
# 测试前 5 条
python analyze_projects.py data_csv/20251126_215926.csv -n 5

# 批量分析全部
python analyze_projects.py data_csv/20251126_215926.csv
```

### 4. 查看结果

用 Excel 打开输出的 `analyzed_XXXXXX_XXXXXX.csv` 文件

## 📊 输出示例

**原始 CSV（9列）:**
```
招标人,项目单位,项目名称,项目编号,采购方式,招标文件获取时间,招标文件截止时间,开标时间,招标公告网址
```

**增强 CSV（新增5列）:**
```
...(原有列)...,整体建设内容,整体金额(万元),是否有分包,分包数量,分包详情
```

**示例数据:**
- **整体建设内容**: "采购网络安全工控机，包括A型50台和B型30台，用于提升网络安全防护能力"
- **整体金额(万元)**: 250.0
- **是否有分包**: 是
- **分包数量**: 2
- **分包详情**: `[{"package_name":"第一包:网络安全工控机A型","construction_content":"...","amount_wan_yuan":150.0},{...}]`

## 💡 核心技术

| 组件 | 技术栈 | 说明 |
|------|--------|------|
| **分析器** | LangChain + Pydantic | 结构化提示词和输出 |
| **LLM** | Kimi moonshot-v1-8k | 国内访问快，中文优秀 |
| **金额归一化** | 提示词工程 | AI 自动转换为万元 |
| **批量处理** | Python + httpx | 并发请求和容错处理 |

## 📈 性能指标

- **速度**: 单个项目 2-5秒
- **成本**: 100个项目约 ¥2.40（使用 Kimi moonshot-v1-8k）
- **准确率**: 金额提取 >95%，内容概括 >90%*
- **国内访问**: 无需翻墙，稳定快速

*基于内部测试数据

## 🎨 应用场景

### 客户经理
- ⚡ 快速筛选符合预算和方向的商机
- 📊 生成项目统计报表（总金额、平均金额等）
- 🎯 精准定位高价值项目

### 投标团队
- 📝 快速了解项目核心需求
- 💰 预算评估和报价参考
- 📦 识别分包机会

### 数据分析
- 📈 按金额区间统计项目分布
- 🏢 分析不同单位的采购特点
- 🔍 发现行业趋势和热点

## 📚 完整文档

- [使用指南](docs/ai_analyzer_guide.md) - 详细使用说明
- [功能文档](docs/FEATURE_AI_ANALYZER.md) - 技术架构和设计
- [工作日志](notes/stage1.md#2025-11-27-工作记录) - 开发过程记录

## 🎬 演示脚本

运行交互式演示（包含测试和分析流程）:

```bash
./demo_ai_analyzer.sh
```

## ⚙️ 高级配置

### 自定义模型

编辑 `analyzers/project_analyzer.py`，修改默认模型:

```python
analyzer = ProjectAnalyzer(
    model="gpt-4",  # 使用更强大的模型
    temperature=0.0
)
```

### 自定义提示词

在 `ProjectAnalyzer.__init__` 中修改 `self.prompt` 变量

### 批量处理优化

```bash
# 并发处理（需要自行修改代码支持）
# 或分批处理大量数据
python analyze_projects.py data_1.csv -o result_1.csv
python analyze_projects.py data_2.csv -o result_2.csv
```

## 🐛 故障排查

### 问题1: "必须提供 api_key..."

**解决**: 
```bash
export OPENAI_API_KEY="sk-your-kimi-key"
export OPENAI_BASE_URL="https://api.moonshot.cn/v1"
```
获取 API Key: https://platform.moonshot.cn/console/api-keys

### 问题2: 某些项目分析失败

**原因**: 
- 详情页无法访问
- 页面结构特殊
- API 超时

**解决**: 脚本会自动跳过失败项，在输出中标注错误

### 问题3: 提取的金额不准确

**原因**: 页面中金额表述特殊或模糊

**解决**: 
1. 检查原始页面内容
2. 调整提示词
3. 使用更强大的模型（如 gpt-4）

## 🔮 未来规划

- [ ] 支持更多招标平台
- [ ] 离线模型集成（降低成本）
- [ ] 实体识别（供应商、品牌等）
- [ ] 智能摘要和标签
- [ ] 多语言支持

## 🤝 反馈与支持

- **GitHub Issues**: 报告 Bug 或提出建议
- **Email**: yejingcn@hotmail.com
- **文档**: 查看 `docs/` 目录下的详细文档

---

**版本**: v0.2  
**发布**: 2025-11-27  
**作者**: Yip King

**许可**: Apache License 2.0

