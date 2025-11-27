#!/usr/bin/env python3
"""
修复 CSV 文件中的项目单位列
根据项目名称关键词自动填充项目单位
"""
import pandas as pd
import sys
from pathlib import Path

def get_project_unit(project_name: str) -> str:
    """
    根据项目名称判断项目单位
    """
    if pd.isna(project_name):
        return ""
    
    project_name = str(project_name)
    
    if "数据平台与安全" in project_name:
        return "数据安全公司"
    if "数字运营" in project_name:
        return "数字运营公司"
    if "广东电科院" in project_name:
        return "广东电科院"
    if "综合能源" in project_name:
        return "综合能源公司"
    
    return ""

def fix_project_unit(input_csv: str, output_csv: str = None):
    """
    修复 CSV 文件的项目单位列
    """
    if output_csv is None:
        output_csv = input_csv
    
    print(f"📖 读取 CSV: {input_csv}")
    df = pd.read_csv(input_csv)
    
    print(f"   总记录数: {len(df)}")
    print(f"   当前列: {list(df.columns)}")
    
    # 检查项目单位列是否存在
    if '项目单位' not in df.columns:
        print("❌ 错误: CSV 中没有'项目单位'列")
        return
    
    # 统计修复前的状态
    empty_before = df['项目单位'].isna().sum() + (df['项目单位'] == '').sum()
    print(f"\n📊 修复前: {empty_before} 条记录的项目单位为空")
    
    # 应用修复逻辑
    print(f"\n🔧 开始修复...")
    df['项目单位'] = df['项目名称'].apply(get_project_unit)
    
    # 统计修复后的状态
    filled = (df['项目单位'] != '').sum()
    print(f"✅ 修复完成: {filled} 条记录已填充项目单位")
    
    # 按项目单位统计
    print(f"\n📈 项目单位分布:")
    unit_counts = df['项目单位'].value_counts()
    for unit, count in unit_counts.items():
        if unit != '':
            print(f"   {unit}: {count} 个项目")
    empty_after = (df['项目单位'] == '').sum()
    if empty_after > 0:
        print(f"   (未识别): {empty_after} 个项目")
    
    # 保存结果
    print(f"\n💾 保存到: {output_csv}")
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"✅ 完成！")
    
    # 显示示例
    print(f"\n🔍 示例（前3条数据安全公司记录）:")
    data_security = df[df['项目单位'] == '数据安全公司'].head(3)
    for idx, row in data_security.iterrows():
        print(f"\n{idx+1}. {row['项目名称'][:50]}...")
        print(f"   项目单位: {row['项目单位']}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python fix_project_unit.py <CSV文件> [输出CSV]")
        print("示例: python fix_project_unit.py data_csv/20251126_215926.csv")
        print("      python fix_project_unit.py data_csv/20251126_215926.csv data_csv/20251126_215926_fixed.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not Path(input_file).exists():
        print(f"❌ 错误: 文件不存在: {input_file}")
        sys.exit(1)
    
    fix_project_unit(input_file, output_file)

