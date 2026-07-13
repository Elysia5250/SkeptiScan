#!/usr/bin/env python3
"""
Search Bing for real product URLs — reviews, complaints, purchases.
Filters out encyclopedia/concept pages (baike, wikipedia, etc.).
Outputs a CSV skeleton to stdout: url,model_output,ground_truth

Usage:
    python scrape_sources.py > raw_cases.csv
"""

import csv
import sys
from urllib.parse import quote_plus, urlparse

try:
    import httpx
    from lxml import html as lxml_html
except ImportError:
    print("Missing dependencies: pip install httpx lxml", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Exclusion: domains that are encyclopedia / concept pages, never products
# ---------------------------------------------------------------------------
EXCLUDE_DOMAINS = [
    "baike.baidu.com", "wikipedia.org", "zh.wikipedia.org",
    "dict.baidu.com", "zdic.net", "汉语词典",
]

# ---------------------------------------------------------------------------
# Inclusion: domains that contain product news, reviews, complaints, or sales
# ---------------------------------------------------------------------------
INCLUDE_DOMAINS = [
    # E-commerce
    "taobao.com", "tmall.com", "jd.com", "pinduoduo.com",
    "amazon.cn", "amazon.com",
    "weixin.qq.com", "mp.weixin.qq.com",
    # News (product reports, scam exposure)
    "news.cctv.com", "news.cn", "xinhuanet.com",
    "163.com", "sohu.com", "sina.com.cn",
    "thepaper.cn", "chinanews.com", "ce.cn",
    # Tech / product reviews
    "36kr.com", "huxiu.com", "ifanr.com", "digitimes.com.cn",
    # Consumer protection / complaints
    "12315.cn", "315.gov.cn", "blacklist.315.org.cn",
    "tousu.sina.com.cn",
]

# ---------------------------------------------------------------------------
# Search queries — aim for specific products, not concepts
# ---------------------------------------------------------------------------

SCAM_QUERIES = [
    # 量子骗局相关产品
    "量子养生杯 骗局 曝光",
    "量子能量 产品 骗局",
    "量子鞋垫 骗局",
    # 磁疗相关
    "磁疗床垫 骗局 投诉",
    "磁疗仪 骗局",
    # 保健品类
    "包治百病 保健品 曝光",
    "院士推荐 保健品 骗局",
    "负离子 治疗仪 骗局",
    # 微商/骗局类
    "祖传秘方 调理 骗局",
    "红外治疗仪 投诉",
    "纳米 保健品 骗局",
    "排毒 保健品 曝光",
    # 投资返利
    "消费返利 骗局 曝光",
    "稳赚不赔 投资 骗局",
]

NORMAL_QUERIES = [
    "官方旗舰店 知名品牌 保健品 测评",
    "国药准字 保健品 使用体验",
    "正规 医疗器械 评测",
    "三甲医院 推荐 保健品",
    "维生素 品牌 评测",
]

SEARCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def is_good_url(url: str) -> bool:
    """Keep URLs that are product-related, reject encyclopedia/concept pages."""
    domain = urlparse(url).netloc.lower()
    path = urlparse(url).path.lower()

    # Exclusion
    for ex in EXCLUDE_DOMAINS:
        if ex in domain:
            return False

    # Inclusion
    for inc in INCLUDE_DOMAINS:
        if inc in domain:
            skip = ["search", "category", "list", "sale", "promo", "shop/"]
            if any(s in path for s in skip):
                return False
            return True

    # Also allow zhihu (product discussions)
    if "zhihu.com" in domain:
        return True

    return False


def search_urls(query: str, max_results: int = 15) -> list[str]:
    """Search Bing and return matching URLs."""
    url = f"https://www.bing.com/search?q={quote_plus(query)}&count={max_results}&setlang=zh-cn"
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(url, headers=SEARCH_HEADERS)
            resp.raise_for_status()
    except Exception as e:
        return []

    tree = lxml_html.fromstring(resp.text)
    found = []
    seen = set()
    for a in tree.xpath("//h2/a | //li[contains(@class,'b_algo')]//a"):
        href = a.get("href", "").strip()
        if href.startswith("http") and href not in seen:
            found.append(href)
            seen.add(href)

    result = []
    for link in found:
        if is_good_url(link) and link not in result:
            result.append(link)
    return result[:6]


def main():
    writer = csv.writer(sys.stdout)
    writer.writerow(["url", "model_output", "ground_truth"])

    case_id = 0
    queries = [(q, "scam") for q in SCAM_QUERIES] + [(q, "not_scam") for q in NORMAL_QUERIES]

    for query, hint in queries:
        print(f"  [{hint}] {query[:45]}...", file=sys.stderr, end=" ")
        urls = search_urls(query)
        print(f"got {len(urls)} URLs", file=sys.stderr)
        for url in urls:
            case_id += 1
            writer.writerow([url, "", ""])

    print(f"\nTotal: {case_id} URLs. Edit the CSV to fill ground_truth.", file=sys.stderr)
    print(f"Then: python run_benchmark.py --csv dataset.csv", file=sys.stderr)


if __name__ == "__main__":
    main()
