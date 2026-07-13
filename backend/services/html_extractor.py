"""
网页正文提取服务
通过 HTTP GET + lxml 快速提取商品页面的可见文本，替代 Playwright 截图 + OCR 路径
"""

import re
from typing import Optional
from urllib.parse import urlparse

# 需要跳过的标签（导航、脚本、广告等）
SKIP_TAGS = {"script", "style", "nav", "footer", "header", "noscript",
             "svg", "canvas", "iframe", "form", "button", "select",
             "aside", "dialog", "template"}

# 跳过的 class 关键词
SKIP_CLASSES = ["nav", "footer", "header", "sidebar", "ad", "advert",
                "banner", "popup", "modal", "cookie", "menu",
                "comment", "recommend", "related"]

# 提取正文时的最小段落长度
MIN_PARAGRAPH_LEN = 15

# 可信的商品内容区域 class/ID 关键词
CONTENT_CLASSES = ["product", "detail", "content", "main", "article",
                   "description", "info", "price", "title", "sku",
                   "parameter", "spec", "attribute", "tb-detail",
                   "item-info", "goods-detail"]


def _should_skip_element(el) -> bool:
    """判断元素是否应该跳过"""
    tag = el.tag if hasattr(el, "tag") else ""
    if tag in SKIP_TAGS:
        return True
    cls = el.get("class", "") + " " + el.get("id", "")
    for skip in SKIP_CLASSES:
        if skip in cls.lower():
            return True
    return False


def _extract_text_recursive(el, depth=0) -> list[str]:
    """递归提取可见文本"""
    if depth > 20:
        return []
    if _should_skip_element(el):
        return []

    parts = []
    tag = el.tag if hasattr(el, "tag") else ""

    # 获取直接文本
    if el.text and el.text.strip():
        text = el.text.strip()
        if len(text) >= MIN_PARAGRAPH_LEN or tag in ("h1", "h2", "h3", "h4", "title", "strong", "b"):
            parts.append(text)

    # 递归子元素
    for child in el:
        parts.extend(_extract_text_recursive(child, depth + 1))

    # tail text
    if el.tail and el.tail.strip():
        tail = el.tail.strip()
        if len(tail) >= MIN_PARAGRAPH_LEN:
            parts.append(tail)

    return parts


def _score_element(el) -> int:
    """给元素打分，判断其是否是主要内容区域"""
    score = 0
    tag = el.tag if hasattr(el, "tag") else ""
    cls = (el.get("class", "") + " " + el.get("id", "")).lower()

    for kw in CONTENT_CLASSES:
        if kw in cls:
            score += 10
        elif kw in tag:
            score += 5

    # 按标签加分
    tag_bonus = {"article": 15, "main": 15, "div": 0, "section": 5,
                 "table": 8, "ul": 3, "ol": 3, "dl": 5}
    score += tag_bonus.get(tag, 0)

    # 文本密度加分
    text_len = len(el.text_content().strip()) if hasattr(el, "text_content") else 0
    if text_len > 200:
        score += 5
    if text_len > 500:
        score += 5

    # 链接密度减分
    links = el.findall(".//a") if hasattr(el, "findall") else []
    link_text = sum(len(a.text_content().strip()) for a in links if hasattr(a, "text_content"))
    if text_len > 0 and link_text / text_len > 0.6:
        score -= 10

    return score


def extract_page_text(url: str, timeout: int = 15) -> Optional[str]:
    """
    抓取 URL 页面并提取可见正文

    Args:
        url: 商品页面 URL
        timeout: HTTP 请求超时（秒）

    Returns:
        页面正文纯文本，失败返回 None
    """
    from lxml import html as lxml_html
    import httpx

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, headers=headers, follow_redirects=True)
            resp.raise_for_status()
            html_content = resp.text
    except Exception as e:
        print(f"[HTMLExtract] HTTP 请求失败 ({url[:50]}...): {e}")
        return None

    try:
        tree = lxml_html.fromstring(html_content)
    except Exception as e:
        print(f"[HTMLExtract] HTML 解析失败: {e}")
        return None

    # 尝试按内容区域打分提取
    candidates = []

    # 优先尝试常用的内容容器
    for xpath_expr in [
        "//article",
        "//main",
        "//div[contains(@class,'product')]",
        "//div[contains(@class,'detail')]",
        "//div[contains(@class,'content')]",
        "//div[contains(@id,'product')]",
        "//div[contains(@id,'detail')]",
        "//div[contains(@class,'info')]",
        "//body",
    ]:
        elements = tree.xpath(xpath_expr)
        for el in elements:
            score = _score_element(el)
            text = el.text_content().strip()
            if text and len(text) > 100:
                candidates.append((score, text, el))

    if candidates:
        # 选择最高分的内容区域
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_text = candidates[0][1]
    else:
        # 全页提取
        body = tree.find("body")
        if body is None:
            return None
        parts = _extract_text_recursive(body)
        best_text = "\n".join(parts)

    # 清理：合并空白行
    lines = [line.strip() for line in best_text.split("\n")]
    lines = [line for line in lines if line and len(line) >= MIN_PARAGRAPH_LEN]
    result = "\n".join(lines)

    if len(result) < 20:
        return None

    print(f"[HTMLExtract] 成功提取 {len(result)} 字符 ({url[:50]}...)")
    return result
