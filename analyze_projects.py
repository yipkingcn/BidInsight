#!/usr/bin/env python3
"""
项目分析工具
读取已爬取的CSV文件,使用AI分析项目内容
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import httpx
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from rich.progress import track

from analyzers.project_analyzer import ProjectAnalyzer, ProjectAnalysis


console = Console()


def fetch_detail_content(url: str) -> str:
    """获取详情页面的完整HTML内容"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    with httpx.Client(headers=headers, timeout=30.0, http2=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def read_csv_records(csv_path: str) -> List[Dict[str, Any]]:
    """读取CSV文件"""
    records = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return records


def analyze_projects(
    csv_path: str,
    output_path: Optional[str] = None,
    max_count: Optional[int] = None,
    skip_existing: bool = True,
    model: str = "moonshot-v1-8k"
) -> List[Dict[str, Any]]:
    """
    分析项目
    
    Args:
        csv_path: 输入的CSV文件路径
        output_path: 输出文件路径,如果为None则自动生成
        max_count: 最多分析多少条记录
        skip_existing: 是否跳过已经分析过的记录
        model: 使用的模型名称
        
    Returns:
        分析结果列表
    """
    # 读取CSV
    console.print(f"[cyan]正在读取 {csv_path}...[/cyan]")
    records = read_csv_records(csv_path)
    console.print(f"[green]共读取 {len(records)} 条记录[/green]")
    
    # 限制数量
    if max_count:
        records = records[:max_count]
        console.print(f"[yellow]仅分析前 {max_count} 条记录[/yellow]")
    
    # 初始化分析器
    console.print(f"[cyan]正在初始化AI分析器 (模型: {model})...[/cyan]")
    try:
        analyzer = ProjectAnalyzer(model=model)
    except ValueError as e:
        console.print(f"[red]错误: {e}[/red]")
        console.print("[yellow]请设置环境变量 MOONSHOT_API_KEY 或 OPENAI_API_KEY[/yellow]")
        console.print("[yellow]获取 Kimi API Key: https://platform.moonshot.cn/console/api-keys[/yellow]")
        sys.exit(1)
    
    # 准备输出文件
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("data_csv")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"analyzed_{timestamp}.csv"
    
    # 分析每条记录
    results = []
    failed_count = 0
    
    for i, record in enumerate(track(records, description="正在分析项目...")):
        url = record.get("招标公告网址", "")
        project_name = record.get("项目名称", "未知项目")
        
        try:
            # 获取详情页内容
            html_content = fetch_detail_content(url)
            
            # 使用AI分析
            analysis = analyzer.analyze_from_html(html_content)
            
            if analysis:
                # 构建分包内容和预算（分段展示）
                package_contents = []
                package_budgets = []
                for pkg in analysis.packages:
                    # 分包内容：分包名称 + 建设内容
                    content_text = f"{pkg.package_name}: {pkg.construction_content}"
                    package_contents.append(content_text)
                    
                    # 分包预算
                    budget_text = f"{pkg.package_name}: {pkg.amount_wan_yuan if pkg.amount_wan_yuan else '未提及'}万元"
                    package_budgets.append(budget_text)
                
                # 用换行符分段
                project_content = "\n".join(package_contents)
                project_budget = "\n".join(package_budgets)
                
                # 合并原记录和分析结果
                result = {
                    **record,
                    "项目内容": project_content,
                    "项目预算": project_budget,
                    "整体建设内容": analysis.overall_construction_content,
                    "整体金额(万元)": analysis.overall_amount_wan_yuan or "",
                    "是否有分包": "是" if analysis.has_multiple_packages else "否",
                    "分包数量": len(analysis.packages),
                    "分包详情": json.dumps(
                        [p.model_dump() for p in analysis.packages], 
                        ensure_ascii=False
                    )
                }
                results.append(result)
                
                console.print(f"[green]✓[/green] [{i+1}/{len(records)}] {project_name[:40]}")
            else:
                console.print(f"[yellow]⊘[/yellow] [{i+1}/{len(records)}] {project_name[:40]} - 无法提取相关内容")
                results.append({
                    **record,
                    "项目内容": "",
                    "项目预算": "",
                    "整体建设内容": "",
                    "整体金额(万元)": "",
                    "是否有分包": "",
                    "分包数量": 0,
                    "分包详情": ""
                })
                failed_count += 1
                
        except Exception as e:
            console.print(f"[red]✗[/red] [{i+1}/{len(records)}] {project_name[:40]} - {e}")
            results.append({
                **record,
                "项目内容": "",
                "项目预算": "",
                "整体建设内容": f"分析失败: {str(e)}",
                "整体金额(万元)": "",
                "是否有分包": "",
                "分包数量": 0,
                "分包详情": ""
            })
            failed_count += 1
    
    # 保存结果
    if results:
        console.print(f"\n[cyan]正在保存结果到 {output_path}...[/cyan]")
        
        # 确定输出列顺序（在项目编号后增加"项目内容"和"项目预算"）
        fieldnames = [
            "招标人", "项目单位", "项目名称", "项目编号", 
            "项目内容", "项目预算",  # 新增两列
            "采购方式",
            "整体建设内容", "整体金额(万元)", "是否有分包", "分包数量",
            "招标文件获取时间", "招标文件截止时间", "开标时间",
            "招标公告网址", "分包详情"
        ]
        
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(results)
        
        console.print(f"[green]✓ 成功保存 {len(results)} 条记录[/green]")
        console.print(f"[yellow]  其中 {failed_count} 条分析失败或无相关内容[/yellow]")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="分析招标项目内容,提取建设内容和金额信息"
    )
    parser.add_argument(
        "csv_file",
        help="输入的CSV文件路径(由 csg_bidding.py 生成)"
    )
    parser.add_argument(
        "-o", "--output",
        help="输出CSV文件路径(默认自动生成时间戳文件名)"
    )
    parser.add_argument(
        "-n", "--max-count",
        type=int,
        help="最多分析多少条记录(用于测试)"
    )
    parser.add_argument(
        "--model",
        default="moonshot-v1-8k",
        help="使用的模型名称 (默认: moonshot-v1-8k, 可选: moonshot-v1-32k, moonshot-v1-128k, kimi-k2-thinking)"
    )
    parser.add_argument(
        "--api-key",
        help="API Key (也可通过环境变量 MOONSHOT_API_KEY 或 OPENAI_API_KEY 设置)"
    )
    parser.add_argument(
        "--base-url",
        help="API Base URL (默认: https://api.moonshot.cn/v1, 也可通过环境变量 OPENAI_BASE_URL 设置)"
    )
    
    args = parser.parse_args()
    
    # 设置环境变量(如果通过参数提供)
    if args.api_key:
        os.environ["MOONSHOT_API_KEY"] = args.api_key
        os.environ["OPENAI_API_KEY"] = args.api_key  # 向后兼容
    if args.base_url:
        os.environ["OPENAI_BASE_URL"] = args.base_url
    
    # 检查输入文件
    if not Path(args.csv_file).exists():
        console.print(f"[red]错误: 文件不存在: {args.csv_file}[/red]")
        sys.exit(1)
    
    # 执行分析
    analyze_projects(
        csv_path=args.csv_file,
        output_path=args.output,
        max_count=args.max_count,
        model=args.model
    )


if __name__ == "__main__":
    main()

