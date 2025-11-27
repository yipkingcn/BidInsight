#!/usr/bin/env python3
"""
更新原始 CSV 文件，添加 AI 分析结果列
"""
import pandas as pd
import sys
from pathlib import Path

def update_csv_with_analysis(original_csv: str, analyzed_csv: str, output_csv: str = None):
    """
    将 AI 分析结果合并到原始 CSV
    
    Args:
        original_csv: 原始 CSV 文件路径
        analyzed_csv: AI 分析后的 CSV 文件路径
        output_csv: 输出文件路径，如果为 None 则覆盖原始文件
    """
    # 读取原始 CSV
    print(f"📖 读取原始 CSV: {original_csv}")
    df_original = pd.read_csv(original_csv)
    print(f"   原始列: {list(df_original.columns)}")
    print(f"   记录数: {len(df_original)}")
    
    # 读取分析结果 CSV
    print(f"\n📖 读取分析结果: {analyzed_csv}")
    df_analyzed = pd.read_csv(analyzed_csv)
    print(f"   分析列: {list(df_analyzed.columns)}")
    print(f"   记录数: {len(df_analyzed)}")
    
    # 合并：以原始 CSV 为基础，根据"招标公告网址"匹配分析结果
    print(f"\n🔄 合并数据...")
    
    # 提取分析结果中的新增列
    analysis_columns = ['项目内容', '分包预算', '项目预算(万元)']
    
    # 创建一个字典来存储分析结果
    analysis_dict = {}
    for _, row in df_analyzed.iterrows():
        url = row['招标公告网址']
        analysis_dict[url] = {
            '项目内容': row.get('项目内容', ''),
            '分包预算': row.get('分包预算', ''),
            '项目预算(万元)': row.get('项目预算(万元)', '')
        }
    
    # 为原始 CSV 添加分析列
    df_original['项目内容'] = ''
    df_original['分包预算'] = ''
    df_original['项目预算(万元)'] = ''
    
    # 匹配并填充分析结果
    matched = 0
    for idx, row in df_original.iterrows():
        url = row['招标公告网址']
        if url in analysis_dict:
            df_original.at[idx, '项目内容'] = analysis_dict[url]['项目内容']
            df_original.at[idx, '分包预算'] = analysis_dict[url]['分包预算']
            df_original.at[idx, '项目预算(万元)'] = analysis_dict[url]['项目预算(万元)']
            matched += 1
    
    print(f"   匹配成功: {matched}/{len(df_original)} 条记录")
    
    # 调整列顺序：在项目编号后插入新列
    original_cols = ['招标人', '项目单位', '项目名称', '项目编号']
    new_cols = ['项目内容', '分包预算', '项目预算(万元)']
    remaining_cols = ['采购方式', '招标文件获取时间', '招标文件截止时间', '开标时间', '招标公告网址']
    
    final_columns = original_cols + new_cols + remaining_cols
    df_result = df_original[final_columns]
    
    # 保存结果
    if output_csv is None:
        output_csv = original_csv
    
    print(f"\n💾 保存结果到: {output_csv}")
    df_result.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"   最终列数: {len(df_result.columns)}")
    print(f"   最终列: {list(df_result.columns)}")
    print(f"\n✅ 完成！")
    
    # 显示统计
    # 转换为数值类型
    df_result['项目预算(万元)'] = pd.to_numeric(df_result['项目预算(万元)'], errors='coerce')
    analyzed_count = df_result['项目预算(万元)'].notna().sum()
    total_budget = df_result['项目预算(万元)'].sum()
    print(f"\n📊 统计信息:")
    print(f"   已分析项目: {analyzed_count}/{len(df_result)}")
    if analyzed_count > 0:
        print(f"   总预算: {total_budget:.2f} 万元")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python update_original_csv.py <原始CSV> <分析结果CSV> [输出CSV]")
        print("示例: python update_original_csv.py data_csv/20251126_215926.csv data_csv/analyzed_20251127_213648.csv")
        sys.exit(1)
    
    original = sys.argv[1]
    analyzed = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not Path(original).exists():
        print(f"❌ 错误: 原始文件不存在: {original}")
        sys.exit(1)
    
    if not Path(analyzed).exists():
        print(f"❌ 错误: 分析结果文件不存在: {analyzed}")
        sys.exit(1)
    
    update_csv_with_analysis(original, analyzed, output)

