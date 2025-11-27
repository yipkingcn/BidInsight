#!/usr/bin/env python3
"""
测试分析器的简单脚本
"""

from analyzers.project_analyzer import ProjectAnalyzer

# 测试文本(示例)
test_content = """
2. 项目概况和招标范围

2.1 项目概况
本项目为南方电网数据平台与安全（广东）有限公司2025年网络安全工控机年度框架采购。

2.2 招标范围
第一包:网络安全工控机A型
采购数量:50台
预算金额:150万元
主要技术要求:符合国产化要求,具备TPM2.0安全芯片

第二包:网络安全工控机B型  
采购数量:30台
预算金额:100万元
主要技术要求:支持国密算法,具备硬件加密功能

项目总预算:250万元
"""


def main():
    print("初始化分析器...")
    try:
        analyzer = ProjectAnalyzer()
    except ValueError as e:
        print(f"错误: {e}")
        print("请设置环境变量 OPENAI_API_KEY")
        return
    
    print("\n开始分析...")
    result = analyzer.analyze(test_content)
    
    print("\n=== 分析结果 ===")
    print(f"整体建设内容: {result.overall_construction_content}")
    print(f"整体金额(万元): {result.overall_amount_wan_yuan}")
    print(f"是否有分包: {result.has_multiple_packages}")
    print(f"分包数量: {len(result.packages)}")
    
    if result.packages:
        print("\n分包详情:")
        for i, pkg in enumerate(result.packages, 1):
            print(f"\n  第{i}个分包:")
            print(f"    名称: {pkg.package_name}")
            print(f"    建设内容: {pkg.construction_content}")
            print(f"    金额(万元): {pkg.amount_wan_yuan}")


if __name__ == "__main__":
    main()

