#!/bin/bash
# Kimi API 环境配置脚本
# 使用方法: source setup_env.sh

echo "🚀 正在配置 Kimi API 环境..."

# 设置 API Key
export MOONSHOT_API_KEY="sk-Mt7Mh7krVbANT1qm9bBExcZBgqL3VeOKeIkooUlYex1iI4Gu"
export OPENAI_BASE_URL="https://api.moonshot.cn/v1"

# 激活虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ 虚拟环境已激活"
else
    echo "⚠️  虚拟环境不存在，请先运行: python -m venv .venv"
fi

echo "✅ API Key 已设置"
echo "✅ Base URL: https://api.moonshot.cn/v1"
echo ""
echo "📝 现在可以使用以下命令:"
echo "   python test_kimi_connection.py        # 测试连接"
echo "   python analyze_projects.py data.csv   # 分析项目"
echo ""

