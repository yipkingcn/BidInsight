# 🚀 快速开始指南

## ✅ 环境已配置完成

您的 Kimi API Key 已配置成功！

```
API Key: sk-Mt7Mh7krVbANT1qm9...
模型: moonshot-v1-8k (默认)
连接: https://api.moonshot.cn/v1
状态: ✅ 已验证
```

## 📝 日常使用流程

### 方式 1: 使用快速配置脚本（推荐）

```bash
# 配置环境并激活虚拟环境
source setup_env.sh
```

### 方式 2: 手动配置

```bash
# 1. 设置 API Key
export MOONSHOT_API_KEY="sk-Mt7Mh7krVbANT1qm9bBExcZBgqL3VeOKeIkooUlYex1iI4Gu"

# 2. 激活虚拟环境
source .venv/bin/activate
```

## 🧪 测试连接

```bash
python test_kimi_connection.py
```

预期输出：
```
✅ 连接成功！
🤖 Kimi 回复: 你好，我是你的人工智能助手...
📊 模型: moonshot-v1-8k
📊 使用 tokens: 42
```

## 🎯 实际使用

### 1. 爬取项目数据

```bash
# 单关键词爬取
python crawlers/sites/csg_bidding.py --keyword "南方电网" --with-detail

# 批量爬取
python crawlers/sites/csg_bidding.py --keywords-file keywords.txt --with-detail
```

输出文件：`data_csv/YYYYMMDD_HHMMSS.csv`

### 2. AI 分析项目内容

#### 测试分析（前 5 条）

```bash
python analyze_projects.py data_csv/20251127_*.csv -n 5
```

#### 批量分析（所有记录）

```bash
python analyze_projects.py data_csv/20251127_*.csv
```

#### 使用推理模型（复杂项目）

```bash
# 推理模型更适合：
# - 多分包项目
# - 复杂金额提取
# - 需要逻辑推理的场景
python analyze_projects.py data_csv/20251127_*.csv --model kimi-k2-thinking
```

### 3. 查看结果

输出文件：`data_csv/analyzed_YYYYMMDD_HHMMSS.csv`

用 Excel 或其他工具打开查看，新增列：
- 整体建设内容
- 整体金额(万元)
- 是否有分包
- 分包数量
- 分包详情

## 🎛️ 模型选择建议

| 项目类型 | 推荐模型 | 命令参数 | 成本 |
|---------|---------|---------|------|
| 简单采购 | moonshot-v1-8k | 默认，无需指定 | ¥0.024/项 |
| 中等复杂 | moonshot-v1-8k | 默认 | ¥0.024/项 |
| 多分包项目 | kimi-k2-thinking | `--model kimi-k2-thinking` | ¥0.06/项 |
| 超长文档 | moonshot-v1-32k | `--model moonshot-v1-32k` | ¥0.048/项 |

## 📊 成本估算

### 基于实际使用（每个项目约 2000 tokens）

| 数量 | moonshot-v1-8k | kimi-k2-thinking | moonshot-v1-32k |
|------|----------------|------------------|-----------------|
| 10 个 | ¥0.24 | ¥0.60 | ¥0.48 |
| 50 个 | ¥1.20 | ¥3.00 | ¥2.40 |
| 100 个 | ¥2.40 | ¥6.00 | ¥4.80 |
| 500 个 | ¥12.00 | ¥30.00 | ¥24.00 |

**建议策略**：
- 先用 moonshot-v1-8k 批量处理大部分项目（性价比高）
- 对复杂或失败的项目使用 kimi-k2-thinking 重新分析

## 🔧 常见命令

```bash
# 完整工作流（从爬取到分析）
source setup_env.sh
python crawlers/sites/csg_bidding.py --keyword "南方电网" --with-detail
python analyze_projects.py data_csv/$(ls -t data_csv/*.csv | head -1) -n 5

# 测试连接
python test_kimi_connection.py

# 查看帮助
python analyze_projects.py --help
python crawlers/sites/csg_bidding.py --help
```

## 📚 详细文档

- **Kimi 配置指南**: `docs/KIMI_SETUP.md`
- **AI 分析器指南**: `docs/ai_analyzer_guide.md`
- **项目 README**: `README.md`
- **工作日志**: `notes/stage1.md`

## ❓ 常见问题

### Q1: "必须提供 api_key" 错误

**解决**: 确保已设置环境变量
```bash
source setup_env.sh
# 或
export MOONSHOT_API_KEY="sk-Mt7Mh7krVbANT1qm9bBExcZBgqL3VeOKeIkooUlYex1iI4Gu"
```

### Q2: 如何查看余额？

访问：https://platform.moonshot.cn/console/account

### Q3: 分析速度慢

- 正常速度：2-5秒/项目
- 如果超过 10秒：检查网络连接或尝试其他模型

### Q4: 如何切换模型？

```bash
# 标准模型（默认）
python analyze_projects.py data.csv

# 推理模型
python analyze_projects.py data.csv --model kimi-k2-thinking

# 长文本模型
python analyze_projects.py data.csv --model moonshot-v1-32k
```

## 💡 最佳实践

1. **测试先行**: 始终用 `-n 5` 先测试少量记录
2. **成本控制**: 大批量任务优先使用默认模型
3. **复杂项目**: 对于多分包项目使用推理模型
4. **错误处理**: 脚本已内置重试和容错，无需担心偶发失败
5. **数据备份**: 保留原始 CSV 和分析结果便于对比

## 🎉 开始使用

```bash
# 一键配置并测试
source setup_env.sh && python test_kimi_connection.py
```

祝您使用愉快！🚀

