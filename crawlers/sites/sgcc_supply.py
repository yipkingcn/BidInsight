"""南方电网供应链统一服务平台公告采集脚本（Stage 1 demo）."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
from html import unescape
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, ConfigDict, Field
from rich.console import Console
from rich.table import Table
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

TZ_SH = dt.timezone(dt.timedelta(hours=8))
LIST_API = (
    "https://ecsg.com.cn/api/tender/tendermanage/"
    "gatewayNoticeQueryController/queryGatewayNoticeListPagination"
)
DETAIL_PAGE_URL = (
    "https://ecsg.com.cn/cms/NoticeDetail.html?objectId={object_id}"
    "&objectType={object_type}&typeid=4"
)
NOTICE_API = (
    "https://ecsg.com.cn/api/tender/tendermanage/gatewayNoticeQueryController/getNotice"
)
CAH_SWITCH_API = (
    "https://ecsg.com.cn/api/tender/tendermanage/"
    "gatewayNoticeQueryController/getCahSwitch"
)
ATTACHMENT_API = (
    "https://ecsg.com.cn/api/tender/tendermanage/"
    "gatewayNoticeQueryController/getNoticeAttachmentInfo"
)
ATTACH_DOWNLOAD_API = (
    "https://ecsg.com.cn/api/tender/tendermanage/"
    "gatewayNoticeQueryController/downloadNoticeAttachment"
)
DEFAULT_HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Connection": "keep-alive",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "https://ecsg.com.cn",
    "Referer": "https://ecsg.com.cn/cms/NoticeList.html?id=1-1&typeid=4&word=&seacrhDate=",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
}
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
BUDGET_PATTERN = re.compile(
    r"(?:预算|金额|限价|估算|标段金额|最高限价)[：:\s]*"
    r"([0-9]+(?:\.[0-9]+)?)\s*(亿|万元|万|元)?",
    re.IGNORECASE,
)
UNIT_MULTIPLIER = {
    "元": 1,
    "万": 10_000,
    "万元": 10_000,
    "亿": 100_000_000,
}


class Attachment(BaseModel):
    attachment_id: Optional[str] = Field(default=None, alias="attachmenId")
    name: str = Field(alias="fileName")
    file_type: Optional[str] = Field(default=None, alias="fileType")
    download_endpoint: str = Field(default=ATTACH_DOWNLOAD_API, alias="downloadUrl")

    model_config = ConfigDict(populate_by_name=True)


class StandardNotice(BaseModel):
    source_site: str = "南方电网供应链统一服务平台"
    notice_id: str
    object_id: str
    object_type: Optional[int] = None
    title: Optional[str] = None
    publish_date: Optional[str] = None
    buyer: Optional[str] = None
    notice_type: Optional[str] = None
    category: Optional[str] = None
    detail_url: str
    summary: Optional[str] = None
    budget_amount_cny: Optional[float] = None
    budget_text: Optional[str] = None
    attachments: List[Attachment] = Field(default_factory=list)
    detail_html: Optional[str] = None
    detail_text: Optional[str] = None
    raw_list: Dict[str, Any]
    raw_detail: Optional[Dict[str, Any]] = None


console = Console()


def strip_html(html_content: Optional[str]) -> str:
    if not html_content:
        return ""
    text = TAG_RE.sub(" ", html_content)
    text = unescape(text)
    return WHITESPACE_RE.sub(" ", text).strip()


def extract_budget(text: str) -> tuple[Optional[float], Optional[str]]:
    if not text:
        return (None, None)
    match = BUDGET_PATTERN.search(text)
    if not match:
        return (None, None)
    value = float(match.group(1))
    unit = (match.group(2) or "元").strip()
    amount_cny = value * UNIT_MULTIPLIER.get(unit, 1)
    return amount_cny, match.group(0)


def summarize_text(text: str, limit: int = 280) -> Optional[str]:
    if not text:
        return None
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def parse_attachments(items: Optional[List[Dict[str, Any]]]) -> List[Attachment]:
    if not items:
        return []

    normalized: List[Attachment] = []
    for item in items:
        attachment_id = item.get("attachmenId") or item.get("attachmentId") or item.get("id")
        payload = {
            "attachmenId": attachment_id,
            "fileName": item.get("fileName") or item.get("name") or "附件",
            "fileType": item.get("fileType"),
            "downloadUrl": ATTACH_DOWNLOAD_API,
        }
        normalized.append(Attachment(**payload))
    return normalized


def standardize_notice(
    base: Dict[str, Any],
    detail: Optional[Dict[str, Any]],
    attachments: Optional[List[Attachment]],
) -> Dict[str, Any]:
    detail_html = (detail or {}).get("noticeContent")
    detail_text = strip_html(detail_html) if detail_html else None
    budget_amount, budget_text = extract_budget(detail_text or "")

    publish_date = normalize_publish_time((detail or {}).get("publishTime")) or base.get(
        "publish_date"
    )

    title = (detail or {}).get("noticeTitle") or base.get("title")
    buyer = (
        (detail or {}).get("organizationInfoName")
        or (detail or {}).get("purchaseOrgName")
        or base.get("buyer")
    )

    attachments_list = attachments or []

    normalized = StandardNotice(
        notice_id=base.get("notice_id") or base.get("object_id"),
        object_id=base.get("object_id"),
        object_type=base.get("object_type"),
        title=title,
        publish_date=publish_date,
        buyer=buyer,
        notice_type=str((detail or {}).get("noticeType") or base.get("notice_type") or ""),
        category=(detail or {}).get("projectLevel1ClassifyName") or base.get("category"),
        detail_url=base.get("detail_url"),
        summary=summarize_text(detail_text),
        budget_amount_cny=budget_amount,
        budget_text=budget_text,
        attachments=attachments_list,
        detail_html=detail_html,
        detail_text=detail_text,
        raw_list=base.get("raw") or {},
        raw_detail=detail,
    )

    return normalized.model_dump()


def parse_date(date_str: Optional[str]) -> str:
    """校验并返回 ISO8601 日期；空值表示不做时间过滤."""
    if not date_str:
        return ""

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return dt.datetime.strptime(date_str, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"无法解析日期: {date_str}")


def normalize_publish_time(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        try:
            ts = float(value) / 1000
            return dt.datetime.fromtimestamp(ts, tz=TZ_SH).isoformat()
        except OSError:
            return None
    if isinstance(value, str):
        try:
            return parse_date(value) or None
        except ValueError:
            return value
    return None


def build_notice(record: Dict[str, Any]) -> Dict[str, Any]:
    notice_id = (
        record.get("noticeId")
        or record.get("tenderProjectId")
        or record.get("objectId")
    )
    object_id = record.get("objectId") or notice_id
    raw_object_type = record.get("objectType") or 1
    try:
        object_type = int(raw_object_type)
    except (ValueError, TypeError):
        object_type = 1
    return {
        "notice_id": notice_id,
        "object_id": object_id,
        "object_type": object_type,
        "title": (record.get("title") or record.get("noticeTitle") or "").strip(),
        "publish_date": normalize_publish_time(record.get("publishTime")),
        "buyer": record.get("purchaseOrgName") or record.get("organizationInfoName"),
        "notice_type": str(record.get("noticeType") or record.get("type") or ""),
        "category": record.get("projectLevel1ClassifyName"),
        "detail_url": DETAIL_PAGE_URL.format(
            object_id=object_id, object_type=object_type
        ),
        "raw": record,
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=8))
def fetch_page(client: httpx.Client, payload: Dict[str, Any]) -> Dict[str, Any]:
    response = client.post(LIST_API, json=payload)
    response.raise_for_status()
    return response.json()


def fetch_cah_switch(client: httpx.Client) -> bool:
    response = client.post(CAH_SWITCH_API, json={})
    response.raise_for_status()
    data = response.json()
    if isinstance(data, bool):
        return data
    if isinstance(data, str):
        return data.lower() == "true"
    return bool(data)


@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=8))
def fetch_notice_detail(
    client: httpx.Client,
    object_id: str,
    object_type: Optional[int],
    cah_switch: Optional[bool],
) -> Dict[str, Any]:
    payload = {
        "objectId": object_id,
        "objectType": str(object_type or 1),
    }
    if cah_switch is not None:
        payload["cahSwitch"] = cah_switch
    response = client.post(NOTICE_API, json=payload)
    response.raise_for_status()
    return response.json()


def fetch_notice_attachments(client: httpx.Client, object_id: str) -> List[Attachment]:
    response = client.post(ATTACHMENT_API, json={"objId": object_id})
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        return []
    return parse_attachments(data)


def fetch_notices(
    since: str,
    max_pages: int,
    page_size: int,
    notice_type: str,
    project_level_id: str,
    keyword: str,
    org_name: str,
    delay: float,
    with_detail: bool,
    standardize: bool,
    detail_keyword: Optional[str],
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with httpx.Client(headers=DEFAULT_HEADERS, timeout=httpx.Timeout(20.0)) as client:
        cah_switch = fetch_cah_switch(client) if with_detail else None
        normalized_detail_keyword = detail_keyword.lower() if detail_keyword else None
        for page in range(1, max_pages + 1):
            payload = {
                "projectLevel1ClassifyId": project_level_id,
                "noticeType": notice_type,
                "noticeTitle": keyword,
                "publishTime": since or "",
                "organizationInfoName": org_name,
                "pageNo": page,
                "pageSize": page_size,
            }
            page_data = fetch_page(client, payload)
            data = page_data.get("data") or page_data or {}
            items = data.get("list") or []
            if not items:
                console.log(f"第 {page} 页无数据，提前结束。")
                break

            for item in items:
                base = build_notice(item)
                detail: Optional[Dict[str, Any]] = None
                attachments: List[Attachment] = []

                if with_detail:
                    try:
                        detail = fetch_notice_detail(
                            client,
                            object_id=base["object_id"],
                            object_type=base["object_type"],
                            cah_switch=cah_switch,
                        )
                    except httpx.HTTPError as exc:
                        console.log(f"[red]详情获取失败({base['object_id']}): {exc}[/red]")
                    else:
                        attachments = fetch_notice_attachments(client, base["object_id"])

                normalized = (
                    standardize_notice(base, detail, attachments) if standardize else None
                )

                include_record = True
                if normalized_detail_keyword:
                    haystacks = [
                        (normalized or {}).get("detail_text"),
                        (normalized or {}).get("detail_html"),
                        (detail or {}).get("noticeContent"),
                        base.get("title"),
                    ]
                    combined = " ".join(h for h in haystacks if h)
                    include_record = normalized_detail_keyword in combined.lower()

                if not include_record:
                    continue

                records.append(
                    {
                        "base": base,
                        "detail": detail,
                        "attachments": [att.model_dump() for att in attachments],
                        "standardized": normalized,
                    }
                )

            total_count: Optional[int] = data.get("count")
            total_pages: Optional[int] = None
            if total_count is not None:
                total_pages = max(1, (int(total_count) + page_size - 1) // page_size)
            else:
                total_pages = data.get("pages")
            if total_pages and page >= total_pages:
                console.log("已到达接口返回的总页数。")
                break

            if delay > 0:
                time.sleep(delay)

    return records


def render_preview(records: List[Dict[str, Any]], prefer_standardized: bool) -> None:
    if not records:
        console.print("[bold red]未获取到公告，请检查参数或站点状态。[/bold red]")
        return

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("标题", overflow="fold")
    table.add_column("发布日期", width=12)
    table.add_column("采购单位", overflow="fold")
    table.add_column("类型", width=8)
    table.add_column("预算(万元)", width=10)

    for record in records[:10]:
        payload = (
            record.get("standardized")
            if prefer_standardized and record.get("standardized")
            else record.get("base", {})
        )
        budget_display = "-"
        budget_value = payload.get("budget_amount_cny")
        if budget_value:
            budget_display = f"{budget_value / 10_000:.1f}"
        table.add_row(
            payload.get("title", ""),
            payload.get("publish_date", ""),
            payload.get("buyer", "") or "-",
            payload.get("notice_type", "") or "-",
            budget_display,
        )

    console.print(table)


def persist_records(
    records: List[Dict[str, Any]], output_path: Optional[str], prefer_standardized: bool
) -> None:
    if not output_path:
        return

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        for record in records:
            payload = (
                record.get("standardized")
                if prefer_standardized and record.get("standardized")
                else record
            )
            fp.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="南方电网供应链公告列表采集（Stage 1 示例）"
    )
    parser.add_argument(
        "--since",
        default="",
        help="发布日期（publishTime）过滤，格式 YYYY-MM-DD；默认留空不过滤。",
    )
    parser.add_argument("--max-pages", type=int, default=1, help="最大分页数量。")
    parser.add_argument("--page-size", type=int, default=20, help="每页数量。")
    parser.add_argument("--notice-type", default="1", help="noticeType，默认 1。")
    parser.add_argument(
        "--project-level-id",
        default="1",
        help="projectLevel1ClassifyId，默认 1（工程/货物/服务分类）。",
    )
    parser.add_argument("--keyword", default="", help="noticeTitle 关键词过滤。")
    parser.add_argument(
        "--org-name", default="", help="organizationInfoName 采购单位过滤。"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.8,
        help="分页请求之间的秒级延迟，用于降低访问频率。",
    )
    parser.add_argument(
        "--with-detail",
        action="store_true",
        help="为每条公告请求详情页 JSON 与附件列表。",
    )
    parser.add_argument(
        "--standardize",
        action="store_true",
        help="输出标准化字段（title/buyer/publish_date/budget 等）。",
    )
    parser.add_argument(
        "--output",
        help="将结果保存为 JSON Lines 文件（默认仅打印）。",
    )
    parser.add_argument(
        "--detail-keyword",
        default="",
        help="仅保留详情正文中包含该关键字的公告（不区分大小写）。",
    )
    args = parser.parse_args()

    since = parse_date(args.since)
    with_detail_flag = args.with_detail or args.standardize or bool(args.detail_keyword)
    console.log(
        f"开始采集：since={since or '未限制'}, max_pages={args.max_pages}, "
        f"page_size={args.page_size}, notice_type={args.notice_type}, "
        f"project_level_id={args.project_level_id}, "
        f"with_detail={with_detail_flag}, standardize={args.standardize}, "
        f"detail_keyword={args.detail_keyword or '无'}"
    )

    notices = fetch_notices(
        since=since,
        max_pages=args.max_pages,
        page_size=args.page_size,
        notice_type=args.notice_type,
        project_level_id=args.project_level_id,
        keyword=args.keyword,
        org_name=args.org_name,
        delay=args.delay,
        with_detail=with_detail_flag,
        standardize=args.standardize,
        detail_keyword=args.detail_keyword or None,
    )
    console.log(f"共获取 {len(notices)} 条公告。")
    render_preview(notices, prefer_standardized=args.standardize)
    persist_records(notices, args.output, prefer_standardized=args.standardize)


if __name__ == "__main__":
    main()

