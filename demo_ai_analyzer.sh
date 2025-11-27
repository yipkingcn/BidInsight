#!/bin/bash
# AI 项目分析器演示脚本

echo "============================================"
echo "  BidInsight AI 项目分析器 - 功能演示"
echo "============================================"
echo ""

# 检查虚拟环境
if [[ ! -f ".venv/bin/activate" ]]; then
    echo "❌ 错误: 虚拟环境不存在"
    echo "请先运行: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# 激活虚拟环境
source .venv/bin/activate

echo "✅ 虚拟环境已激活"
echo ""

# 检查 API Key
if [[ -z "$OPENAI_API_KEY" ]]; then
    echo "⚠️  警告: 未设置 OPENAI_API_KEY 环境变量"
    echo "请运行: export OPENAI_API_KEY='your-api-key'"
    echo ""
    read -p "是否继续(可能会失败)? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "============================================"
echo "步骤 1: 运行测试脚本（使用内置示例）"
echo "============================================"
echo ""
echo "运行命令: python test_analyzer.py"
echo ""
read -p "按回车继续..."
python test_analyzer.py

echo ""
echo "============================================"
echo "步骤 2: 查找最新的 CSV 文件"
echo "============================================"
echo ""

# 查找最新的 CSV 文件
if [[ ! -d "data_csv" ]]; then
    echo "❌ data_csv 目录不存在"
    echo "请先运行爬虫采集数据:"
    echo "  python crawlers/sites/csg_bidding.py --keyword '南方电网数字电网集团有限公司' --with-detail"
    exit 1
fi

latest_csv=$(ls -t data_csv/*.csv 2>/dev/null | grep -v "analyzed_" | head -1)

if [[ -z "$latest_csv" ]]; then
    echo "❌ 没有找到采集的 CSV 文件"
    echo "请先运行爬虫采集数据:"
    echo "  python crawlers/sites/csg_bidding.py --keyword '南方电网数字电网集团有限公司' --with-detail"
    exit 1
fi

echo "找到最新的 CSV 文件: $latest_csv"
line_count=$(wc -l < "$latest_csv")
echo "文件包含 $((line_count - 1)) 条记录（不含表头）"
echo ""

echo "============================================"
echo "步骤 3: 分析前 3 条记录（测试）"
echo "============================================"
echo ""
echo "运行命令: python analyze_projects.py $latest_csv -n 3"
echo ""
read -p "按回车继续..."
python analyze_projects.py "$latest_csv" -n 3

echo ""
echo "============================================"
echo "步骤 4: 查看分析结果"
echo "============================================"
echo ""

analyzed_csv=$(ls -t data_csv/analyzed_*.csv 2>/dev/null | head -1)

if [[ -z "$analyzed_csv" ]]; then
    echo "❌ 没有找到分析结果文件"
    exit 1
fi

echo "分析结果已保存到: $analyzed_csv"
echo ""
echo "CSV 文件列名:"
head -1 "$analyzed_csv" | tr ',' '\n' | nl
echo ""

echo "前 2 条记录预览:"
head -3 "$analyzed_csv" | tail -2 | cut -d',' -f1-5
echo "... (更多列请用 Excel 打开查看)"
echo ""

echo "============================================"
echo "✅ 演示完成!"
echo "============================================"
echo ""
echo "下一步建议:"
echo "1. 用 Excel 或其他工具打开 $analyzed_csv"
echo "2. 查看新增的分析列: 整体建设内容、整体金额(万元)、分包详情等"
echo "3. 如需分析全部记录，运行:"
echo "   python analyze_projects.py $latest_csv"
echo ""
echo "更多信息请参考: docs/ai_analyzer_guide.md"
echo ""

