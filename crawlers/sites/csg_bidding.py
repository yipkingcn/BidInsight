"""中国南方电网 bidding.csg.cn 列表采集脚本."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urljoin

import httpx
import pandas as pd
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from tenacity import retry, stop_after_attempt, wait_exponential

console = Console()

LIST_BASE_URL = "https://www.bidding.csg.cn/dbsearch.jspx"
DETAIL_BASE_URL = "https://www.bidding.csg.cn"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "max-age=0",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
    "sec-ch-ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}


def normalize_date(date_str: str) -> str:
    try:
        return dt.datetime.strptime(date_str, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return date_str


def parse_since(value: Optional[str]) -> Optional[dt.date]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"无法识别日期格式: {value}")


def build_list_url(keyword: str, page_no: int) -> str:
    params = {
        "channelId": "309",
        "types": "",
        "org": "",
        "q": keyword,
        "pageNo": str(page_no),
    }
    return f"{LIST_BASE_URL}?{urlencode(params, encoding='utf-8', doseq=True)}"


def parse_listing(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    result: List[Dict[str, Any]] = []
    for li in soup.select("div.List2 li"):
        category_tag = li.select_one("span.Right a")
        date_tag = li.select_one("span.Right span.Gray")
        company_tag = li.select_one("a.Blue")
        detail_link_tag = li.select("a[target=_blank]")
        
        if not detail_link_tag:
            continue
            
        # 过滤：只抓取“招标公告”或“非招标公告”类型的记录
        category_text = category_tag.get_text(strip=True) if category_tag else ""
        if "招标公告" not in category_text and "非招标公告" not in category_text:
            continue

        detail_link = detail_link_tag[-1]
        
        # 判断采购方式
        # 注意："非招标公告" 包含 "招标公告" 子串，必须先判断 "非招标公告"
        if "非招标公告" in category_text:
            procurement_method = "非公开招标"
        elif "招标公告" in category_text:
            procurement_method = "公开招标"
        else:
            procurement_method = "其他"

        record = {
            "category": category_text,
            "procurement_method": procurement_method,
            "publish_date": normalize_date(
                date_tag.get_text(strip=True) if date_tag else ""
            ),
            "company": company_tag.get_text(strip=True) if company_tag else "",
            "title": detail_link.get_text(strip=True),
            "detail_url": urljoin(DETAIL_BASE_URL, detail_link.get("href", "")),
        }
        result.append(record)
    return result


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_detail(client: httpx.Client, url: str) -> Dict[str, Any]:
    # 随机延迟 0.5 ~ 1.5 秒，降低反爬风险
    time.sleep(random.uniform(0.5, 1.5))
    resp = client.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    title = soup.select_one("h1.s-title")
    publish_tag = soup.select_one("div.s-date")
    content = soup.select_one("div.Content")
    
    attachments = []
    for link in soup.select("div.fj-list a"):
        attachments.append(
            {
                "name": link.get_text(strip=True),
                "url": urljoin(DETAIL_BASE_URL, link.get("href", "")),
            }
        )

    def extract_value(markers: List[str]) -> Optional[str]:
        """
        1. 优先尝试从 u 标签获取。
        2. 预处理全文（合并空白）后，使用正则提取。
        3. 支持中文日期格式自动转换为 YYYY-MM-DD HH:mm:ss。
        """
        if not content:
            return None
        
        # 1. 尝试 u 标签 (仅作补充，因为很多页面不再用 u 标签)
        for u in content.find_all("u"):
            prev = u.previous_sibling
            if prev and isinstance(prev, str):
                clean_prev = re.sub(r"\s+", "", prev)
                for marker in markers:
                    if marker.replace(" ", "") in clean_prev:
                        return u.get_text(strip=True)

        # 2. 全文预处理：将所有空白字符（换行、制表符等）替换为单个空格，方便正则匹配
        # 并将中文冒号替换为英文冒号
        full_text_raw = content.get_text("\n", strip=True)
        normalized_text = re.sub(r"\s+", " ", full_text_raw).replace("：", ":")
        
        # 提取日期的通用正则（支持 YYYY-MM-DD 和 YYYY年MM月DD日，允许空格）
        # Group 1-3: YMD, Group 4-6: HMS (Optional)
        date_pattern_str = (
            r"(\d{4})\s*[-年]\s*(\d{1,2})\s*[-月]\s*(\d{1,2})\s*[日]?"
            r"(?:\s*(\d{1,2})\s*[时:]\s*(\d{1,2})\s*[分:]\s*(\d{1,2})\s*[秒]?)?"
        )
        
        is_time_field = any("时间" in m for m in markers)
        
        for marker in markers:
            # 清理 marker 中的空格
            clean_marker = marker.replace(" ", "")
            # 构建正则：
            # marker 的每个字符中间允许插入 \s* (处理 "项目 编号" 这种情况)
            marker_regex_part = r"\s*".join(list(map(re.escape, clean_marker)))
            
            if is_time_field:
                # 匹配日期时间
                # Pattern: Marker + (optional :) + space + Date
                pattern = re.compile(
                    marker_regex_part + r"\s*[:]?\s*" + date_pattern_str
                )
                match = pattern.search(normalized_text)
                if match:
                    y, m, d, h, min_, s = match.groups()
                    # 格式化为标准时间
                    date_str = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
                    # 用户仅需要 YYYY-MM-DD，忽略时分秒
                    return date_str
            else:
                # 匹配普通文本
                # Pattern: Marker + (optional :) + content
                # 如果是项目编号，允许字母数字横杠
                if "编号" in marker:
                    # 贪婪匹配直到空格或标点
                     pattern = re.compile(marker_regex_part + r"\s*[:]?\s*([A-Za-z0-9-]+)")
                else:
                     pattern = re.compile(marker_regex_part + r"\s*[:]?\s*([^\s:;]+)")
                
                match = pattern.search(normalized_text)
                if match:
                    return match.group(1).strip()

        return None

    # 专门处理"项目编号"：增强逻辑
    # 在 normalized_text 中直接搜索
    project_code = extract_value(["项目编号", "采购编号", "招标编号"])

    return {
        "detail_title": title.get_text(strip=True) if title else None,
        "detail_publish_info": publish_tag.get_text(strip=True) if publish_tag else None,
        "detail_html": str(content) if content else None,
        "detail_text": content.get_text("\n", strip=True) if content else None,
        "attachments": attachments,
        # 新增字段
        "tenderee": extract_value(["招标人为", "采购人为"]),
        "project_name": extract_value(["本招标项目", "本采购项目"]),
        "project_code": project_code,
        # 使用更精确的 Marker，匹配 normalized_text 中的内容
        "doc_start_time": extract_value(["获取开始时间", "招标文件获取开始时间"]),
        "doc_end_time": extract_value(["获取结束时间", "招标文件获取结束时间", "投标报名截止时间"]),
        "bid_open_time": extract_value(["开标时间", "递交截止时间"]), # 开标时间通常也是递交截止时间
        "detail_url": url,
    }


def fetch_records(
    keyword: str,
    max_pages: int,
    since: Optional[dt.date],
    with_detail: bool,
    client_timeout: float = 30.0,
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with httpx.Client(
        headers=DEFAULT_HEADERS, timeout=httpx.Timeout(client_timeout)
    ) as client:
        for page in range(1, max_pages + 1):
            url = build_list_url(keyword, page)
            try:
                resp = client.get(url)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                console.log(
                    f"[yellow]警告：关键词 '{keyword}' 第 {page} 页请求失败 "
                    f"(HTTP {exc.response.status_code})，跳过。[/yellow]"
                )
                continue
            except httpx.RequestError as exc:
                console.log(f"[red]请求异常：{exc}[/red]")
                continue

            page_records = parse_listing(resp.text)
            if not page_records:
                console.log(f"第 {page} 页空数据，提前结束。")
                break
            for record in page_records:
                publish_date = record.get("publish_date")
                if since and publish_date:
                    try:
                        record_date = dt.datetime.strptime(
                            publish_date, "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        record_date = None
                    if record_date and record_date < since:
                        continue

                detail_payload = {}
                if with_detail:
                    try:
                        detail_payload = fetch_detail(client, record["detail_url"])
                    except Exception as exc:
                        console.log(
                            f"[red]详情页抓取失败 ({record['detail_url']}): {exc}[/red]"
                        )

                records.append({**record, **detail_payload})
    return records


def render_table(records: List[Dict[str, Any]]) -> None:
    if not records:
        console.print("[bold red]未获取到公告，请调整关键词或时间范围。[/bold red]")
        return
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("标题", overflow="fold")
    table.add_column("公司", overflow="fold")
    table.add_column("类别", width=6)
    table.add_column("发布日期", width=12)

    for row in records[:10]:
        table.add_row(
            row.get("title", ""),
            row.get("company", "") or "-",
            row.get("category", "") or "-",
            row.get("publish_date", "") or "-",
        )
    console.print(table)


def persist(records: List[Dict[str, Any]], output: Optional[str]) -> None:
    if not output:
        return

    # Ensure parent directory exists
    Path(output).parent.mkdir(parents=True, exist_ok=True)

    if output.lower().endswith(".csv"):
        df = pd.DataFrame(records)
        if not df.empty:
            # 定义输出列名映射
            col_mapping = {
                "tenderee": "招标人",
                "project_name": "项目名称",
                "project_code": "项目编号",
                "procurement_method": "采购方式",
                "doc_start_time": "招标文件获取时间",
                "doc_end_time": "招标文件截止时间",
                "bid_open_time": "开标时间",
                "detail_url": "招标公告网址",
            }
            
            # 确保所有字段都存在，不存在则填充空字符串
            for col in col_mapping.keys():
                if col not in df.columns:
                    df[col] = ""

            # 选择并重命名列
            final_cols = list(col_mapping.keys())
            df = df[final_cols]
            df.rename(columns=col_mapping, inplace=True)
            
        df.to_csv(output, index=False, encoding="utf_8_sig")
        console.log(f"[green]已保存 CSV 文件：{output}[/green]")
    else:
        with open(output, "w", encoding="utf-8") as fp:
            for record in records:
                fp.write(json.dumps(record, ensure_ascii=False) + "\n")
        console.log(f"[green]已保存 JSONL 文件：{output}[/green]")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="bidding.csg.cn 列表采集（按关键词查询企业公告）"
    )
    parser.add_argument(
        "--keyword",
        help="单个搜索关键词（可输入企业名称）。如需批量，请使用 --keywords-file。",
    )
    parser.add_argument(
        "--keywords-file",
        help="包含多个关键词的文本文件（每行一个名称，支持注释 #）。",
    )
    parser.add_argument(
        "--since",
        default="",
        help="发布日期下限, YYYY-MM-DD（默认不过滤）",
    )
    parser.add_argument("--max-pages", type=int, default=3, help="最大翻页数，默认 3")
    parser.add_argument(
        "--with-detail",
        action="store_true",
        help="是否抓取详情正文与附件",
    )
    parser.add_argument(
        "--output",
        help="结果保存路径（支持 .jsonl 或 .csv）。未指定时自动在 data_csv/ 生成 CSV。",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    since_date = parse_since(args.since)

    # 自动设置默认输出路径
    if not args.output:
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"data_csv/{timestamp}.csv"

    console.log(
        f"开始采集：since={since_date or '未限制'}, max_pages={args.max_pages}, "
        f"with_detail={args.with_detail}, output={args.output}"
    )

    keywords: List[str] = []
    if args.keyword:
        keywords.append(args.keyword)
    if args.keywords_file:
        with open(args.keywords_file, "r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                keywords.append(line)
    keywords = list(dict.fromkeys(keywords))  # 去重并保持顺序
    if not keywords:
        raise SystemExit("请提供 --keyword 或 --keywords-file。")

    all_records: List[Dict[str, Any]] = []
    for kw in keywords:
        console.log(f"[cyan]采集关键词[/cyan]：{kw}")
        kw_records = fetch_records(
            keyword=kw,
            max_pages=args.max_pages,
            since=since_date,
            with_detail=args.with_detail,
        )
        for record in kw_records:
            record["source_keyword"] = kw
        console.log(f"关键词 {kw} 获取 {len(kw_records)} 条。")
        all_records.extend(kw_records)
    
    # 去重：根据 detail_url
    seen_urls = set()
    unique_records = []
    for record in all_records:
        url = record.get("detail_url")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        unique_records.append(record)
    all_records = unique_records

    console.log(f"全部关键词共获取 {len(all_records)} 条记录（已去重）。")
    render_table(all_records)
    persist(all_records, args.output)


if __name__ == "__main__":
    main()

