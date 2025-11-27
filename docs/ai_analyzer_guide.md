wo# AI 项目内容分析器使用指南

## 概述

AI 项目内容分析器是 BidInsight v0.2 新增的智能分析功能，基于 **LangChain + Kimi（月之暗面）** 实现。它可以自动从招标公告详情页中提取：

- 📝 项目建设内容概述（50-200字精简描述）
- 💰 项目预算金额（自动归一化为万元）
- 📦 分包信息（如有多个标包，自动识别并分别提取）
- 🔢 每个分包的具体内容和金额

**为什么选择 Kimi？**
- 🇨🇳 国内访问无需翻墙，速度快稳定
- 💰 价格优惠（约 ¥12/百万tokens）
- 🎯 中文理解和生成质量优秀
- 🧠 支持 `kimi-k2-thinking` 推理模型（思维链）

## 快速开始

### 1. 环境配置

**获取 Kimi API Key：**

访问 Kimi 开放平台：https://platform.moonshot.cn/console/api-keys

**配置方式：**

```bash
# 方式一：使用环境变量（推荐）
export MOONSHOT_API_KEY="sk-your-kimi-api-key"
# 注：也可以使用 OPENAI_API_KEY，代码会自动识别

# 方式二：使用 .env 文件
cp env.example .env
# 编辑 .env 文件，填入：
# MOONSHOT_API_KEY=sk-your-kimi-api-key
```

### 2. 基本使用

**批量分析已采集的项目：**

```bash
# 激活虚拟环境
source .venv/bin/activate

# 分析 CSV 文件中的所有项目
python analyze_projects.py data_csv/20251126_215926.csv

# 输出文件会自动保存在 data_csv/ 目录下，文件名类似：
# analyzed_20251127_143052.csv
```

**测试分析功能：**

```bash
# 仅分析前 5 条记录（快速测试）
python analyze_projects.py data_csv/20251126_215926.csv -n 5

# 运行简单的测试脚本
python test_analyzer.py
```

**指定输出路径：**

```bash
python analyze_projects.py data_csv/20251126_215926.csv -o results/analyzed.csv
```

### 3. 命令行参数

```bash
python analyze_projects.py [CSV文件] [选项]

必需参数：
  CSV文件              输入的 CSV 文件路径（由 csg_bidding.py 生成）

可选参数：
  -o, --output PATH    输出 CSV 文件路径（默认自动生成时间戳文件名）
  -n, --max-count N    最多分析多少条记录（用于测试）
  --model MODEL        指定使用的模型（默认: moonshot-v1-8k）
                       可选: moonshot-v1-8k, moonshot-v1-32k, 
                            moonshot-v1-128k, kimi-k2-thinking
  --api-key KEY        API Key（也可通过环境变量 MOONSHOT_API_KEY 设置）
  --base-url URL       API Base URL（默认: https://api.moonshot.cn/v1）
```

### 4. 模型选择

| 模型 | 上下文 | 适用场景 | 价格 | 特点 |
|------|--------|---------|------|------|
| **moonshot-v1-8k** | 8K | 常规项目分析 | ¥12/百万tokens | 默认，性价比最高 |
| **moonshot-v1-32k** | 32K | 长文本项目 | ¥24/百万tokens | 适合复杂项目 |
| **moonshot-v1-128k** | 128K | 超长文档 | ¥60/百万tokens | 极长内容 |
| **kimi-k2-thinking** | - | 复杂推理分析 | ¥30/百万tokens | 支持思维链（reasoning） |

**使用推理模型示例：**

```bash
# 使用 kimi-k2-thinking 进行深度分析
python analyze_projects.py data_csv/20251126_215926.csv --model kimi-k2-thinking -n 5
```

## 输出格式

增强后的 CSV 在原有列的基础上新增以下字段：

| 列名 | 说明 | 示例 |
|------|------|------|
| 整体建设内容 | AI 提取的项目概述 | "采购网络安全工控机50台，包括A型和B型两种规格，用于提升公司网络安全防护能力" |
| 整体金额（万元） | 项目总预算（万元） | 250.0 |
| 是否有分包 | "是"或"否" | 是 |
| 分包数量 | 分包个数 | 2 |
| 分包详情 | JSON 格式的分包列表 | 见下方示例 |

**分包详情 JSON 示例：**

```json
[
  {
    "package_name": "第一包：网络安全工控机A型",
    "construction_content": "采购50台A型网络安全工控机，符合国产化要求，具备TPM2.0安全芯片",
    "amount_wan_yuan": 150.0
  },
  {
    "package_name": "第二包：网络安全工控机B型",
    "construction_content": "采购30台B型网络安全工控机，支持国密算法，具备硬件加密功能",
    "amount_wan_yuan": 100.0
  }
]
```

## 技术细节

### 金额归一化规则

分析器会自动识别并转换各种金额表述为万元：

| 原始表述 | 转换规则 | 示例 |
|---------|---------|------|
| X元 | 除以 10,000 | 1,000,000元 → 100万元 |
| X千元 | 除以 10 | 2,500千元 → 250万元 |
| X万元 | 直接使用 | 250万元 → 250万元 |
| X亿元 | 乘以 10,000 | 0.5亿元 → 5,000万元 |

### 分包识别

可识别的分包表述包括但不限于：

- "第一包"、"第二包"
- "第1包"、"第2包"
- "标包1"、"标包2"
- "包1"、"包2"
- "一标段"、"二标段"

### 使用的 AI 模型

- 默认模型：`gpt-4o-mini`（性价比高，速度快）
- 温度参数：`0.0`（确保输出稳定一致）
- 输出格式：结构化 JSON（基于 Pydantic 模型）

## 常见问题

### Q1: 提示 "必须提供 api_key 参数或设置环境变量 OPENAI_API_KEY"

**A:** 需要先配置 OpenAI API Key。有两种方式：

```bash
# 方式一：环境变量
export OPENAI_API_KEY="sk-your-key"

# 方式二：.env 文件
echo "OPENAI_API_KEY=sk-your-key" > .env
```

### Q2: 某些项目分析失败，显示 "分析失败: XXX"

**A:** 可能的原因：
1. 详情页无法访问（网络问题或页面已下线）
2. 页面结构特殊，无法提取"2. 项目概况"部分
3. API 调用失败（配额不足、网络超时等）

脚本会继续处理其他项目，不会中断整体流程。

### Q3: 如何提高分析速度？

**A:** 几个建议：
1. 使用 `-n` 参数先测试小批量
2. 如果有代理或自定义 API 端点，设置 `OPENAI_BASE_URL`
3. 考虑使用更快的模型（在代码中修改 `model` 参数）

### Q4: 分析结果不准确怎么办？

**A:** 可以尝试：
1. 检查原始详情页内容是否完整
2. 调整提示词（修改 `analyzers/project_analyzer.py` 中的 `prompt`）
3. 使用更强大的模型（如 `gpt-4`，但成本更高）

## 成本估算

基于 OpenAI 官方定价（2024年11月）：

- **gpt-4o-mini**: 
  - 输入: $0.15 / 1M tokens
  - 输出: $0.60 / 1M tokens
  
- **每个项目预估消耗**:
  - 输入: ~2,000 tokens（详情页内容 + 提示词）
  - 输出: ~300 tokens（结构化分析结果）
  - 单项成本: 约 $0.0005（0.0005美元）

- **批量分析100个项目**: 约 $0.05（5美分）

## 最佳实践

1. **先小批量测试**: 使用 `-n 5` 先测试 5 条记录，确认效果和成本
2. **分批处理**: 对于大量数据，建议分批处理以便监控进度
3. **结果验证**: 随机抽查几个项目，验证提取的准确性
4. **保留原始数据**: 输出文件包含原始列和新增列，便于对比核对

## 示例工作流

```bash
# 1. 激活虚拟环境
source .venv/bin/activate

# 2. 采集项目数据
python crawlers/sites/csg_bidding.py \
  --keywords-file configs/keywords/csg_units.txt \
  --since 2024-11-15 \
  --max-pages 3 \
  --with-detail

# 输出：data_csv/20251127_140500.csv

# 3. 测试分析（前5条）
export OPENAI_API_KEY="sk-your-key"
python analyze_projects.py data_csv/20251127_140500.csv -n 5

# 4. 确认效果后，批量分析
python analyze_projects.py data_csv/20251127_140500.csv

# 输出：data_csv/analyzed_20251127_141000.csv

# 5. 用 Excel 打开结果文件查看
open data_csv/analyzed_20251127_141000.csv
```

## 进阶使用

### 在代码中使用分析器

```python
from analyzers.project_analyzer import ProjectAnalyzer

# 初始化分析器
analyzer = ProjectAnalyzer(
    api_key="sk-your-key",
    model="gpt-4o-mini",
    temperature=0.0
)

# 分析文本内容
content = """
2. 项目概况和招标范围
本项目为XXX采购...
"""
result = analyzer.analyze(content)

print(f"建设内容: {result.overall_construction_content}")
print(f"金额: {result.overall_amount_wan_yuan}万元")
print(f"分包数: {len(result.packages)}")
```

### 自定义提示词

编辑 `analyzers/project_analyzer.py` 中的 `self.prompt` 变量，可以调整分析策略和输出格式。

## 技术支持

如有问题或建议，请：

1. 查看 `notes/stage1.md` 中的常见问题部分
2. 提交 GitHub Issue
3. 联系项目维护者：yejingcn@hotmail.com

---

*最后更新: 2025-11-27*

