from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ComputerControlIntent:
    action: str
    arguments: dict[str, Any]


SITE_URLS = {
    "taobao": "https://www.taobao.com/",
    "jd": "https://www.jd.com/",
    "tmall": "https://www.tmall.com/",
}


def detect_computer_control_intent(text: str) -> ComputerControlIntent | None:
    normalized = _normalize(text)
    if not normalized:
        return None

    site = _detect_site(normalized)
    query = _extract_shopping_query(text, normalized, site)
    if site in {"taobao", "jd"} and query:
        return ComputerControlIntent(
            "shopping_search",
            {
                "site": site,
                "query": query,
            },
        )

    url = _extract_url(text)
    if url and _looks_like_browser_open(normalized):
        return ComputerControlIntent("browser_open", {"url": url})

    if site and _looks_like_browser_open(normalized):
        return ComputerControlIntent("browser_open", {"url": SITE_URLS[site]})

    if _looks_like_browser_screenshot(normalized):
        return ComputerControlIntent("browser_screenshot", {})

    return None


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text or "").lower()


def _detect_site(normalized: str) -> str | None:
    if "淘宝" in normalized or "taobao" in normalized:
        return "taobao"
    if "京东" in normalized or "jingdong" in normalized or re.search(r"\bjd\b", normalized):
        return "jd"
    if "天猫" in normalized or "tmall" in normalized:
        return "tmall"
    return None


def _extract_url(text: str) -> str | None:
    match = re.search(r"https?://[^\s，。！？,!?]+", text or "", re.IGNORECASE)
    return match.group(0) if match else None


def _looks_like_browser_open(normalized: str) -> bool:
    return any(word in normalized for word in ("打开", "浏览器", "网页", "访问", "open"))


def _looks_like_browser_screenshot(normalized: str) -> bool:
    if not any(word in normalized for word in ("截图", "截屏", "screenshot")):
        return False
    return any(word in normalized for word in ("浏览器", "网页", "当前页面", "页面", "browser"))


def _extract_shopping_query(original: str, normalized: str, site: str | None) -> str | None:
    if site not in {"taobao", "jd"}:
        return None
    if not any(word in normalized for word in ("多少钱", "价格", "价钱", "报价", "多钱", "搜索", "搜一下", "查看")):
        return None

    text = _strip_url(original)
    match = re.search(
        r"(?:查看|搜索|搜一下|搜|查一下|查|找一下|找)?[，,。.\s]*([^，,。.!！?？\n\r]+?)"
        r"(?:多少钱|什么价|价格|价钱|报价|多钱)",
        text,
        re.IGNORECASE,
    )
    if match:
        query = _clean_query(match.group(1))
        if query:
            return query

    compact = re.sub(r"\s+", " ", text).strip()
    compact = re.sub(r"(多少钱|什么价|价格|价钱|报价|多钱).*", "", compact, flags=re.IGNORECASE)
    query = _clean_query(compact)
    return query or None


def _strip_url(text: str) -> str:
    return re.sub(r"https?://\S+", "", text or "", flags=re.IGNORECASE)


def _clean_query(value: str) -> str:
    query = value.strip(" \t\r\n，,。.!！?？:：；;\"'“”‘’`")
    replacements = [
        "请必须调用",
        "computer_control",
        "action=shopping_search",
        "site=taobao",
        "site=jd",
        "query=",
        "使用浏览器",
        "用浏览器",
        "浏览器",
        "打开",
        "淘宝",
        "京东",
        "天猫",
        "网页",
        "页面",
        "查看",
        "搜索",
        "搜一下",
        "查一下",
        "帮我",
        "请",
        "把截图也显示出来",
        "截图也显示出来",
        "显示出来",
        "截图",
        "的",
    ]
    for marker in replacements:
        query = query.replace(marker, " ")
    query = re.sub(r"\b(site|action|query)\s*=\s*[\w-]+", " ", query, flags=re.IGNORECASE)
    query = re.sub(r"\s+", " ", query).strip(" ，,。.!！?？:：；;\"'“”‘’`")
    return query
