"""
联网事实核查服务
通过多搜索引擎交叉验证商品宣传中的可疑声称

搜索引擎优先级：
  1. DuckDuckGo (ddgs 库，免费，无需 API Key)
  2. Wikipedia API（查伪科学概念）
  3. Bing 刮削（降级方案）
"""

import re
import json
from typing import Optional
from urllib.parse import quote_plus

# ---------------------------------------------------------------------------
# 搜索引擎后端注册
# ---------------------------------------------------------------------------
_BACKENDS = []
_BACKEND_NAMES = []

# 1. DuckDuckGo (首选)
try:
    from ddgs import DDGS
    _BACKENDS.append("ddgs")
    _BACKEND_NAMES.append("DuckDuckGo")
    print("[FactCheck] DuckDuckGo 搜索引擎已就绪")
except ImportError:
    pass

# 2. Wikipedia (始终可用，无需额外依赖)
_BACKENDS.append("wikipedia")
_BACKEND_NAMES.append("Wikipedia")

# 3. Bing (始终可用，使用 httpx + lxml 刮削)
try:
    import httpx
    from lxml import html as lxml_html
    _BACKENDS.append("bing")
    _BACKEND_NAMES.append("Bing")
    print("[FactCheck] Bing 搜索引擎已就绪")
except ImportError:
    pass


def is_search_available() -> bool:
    return len(_BACKENDS) > 0


def get_available_backends() -> list:
    return _BACKEND_NAMES


# ---------------------------------------------------------------------------
# 后端搜索函数
# ---------------------------------------------------------------------------

def _search_ddgs(query: str, max_results: int = 5) -> list[dict]:
    """使用 DuckDuckGo 搜索（带超时）"""
    import concurrent.futures

    def _run():
        with DDGS() as ddgs:
            results = []
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "body": r.get("body", "")[:200],
                    "href": r.get("href", ""),
                    "source": "ddgs",
                })
            return results

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_run)
            return future.result(timeout=5.0)
    except concurrent.futures.TimeoutError:
        print(f"[FactCheck] DuckDuckGo 超时")
        return []
    except Exception as e:
        print(f"[FactCheck] DuckDuckGo 失败: {e}")
        return []


def _search_wikipedia(query: str, max_results: int = 3) -> list[dict]:
    """搜索 Wikipedia 获取伪科学概念的定义"""
    import concurrent.futures

    def _wiki_search(query, max_results):
        try:
            import wikipedia
            wikipedia.set_lang("zh")
            results = []
            search_results = wikipedia.search(query, results=max_results)
            for title in search_results:
                try:
                    summary = wikipedia.summary(title, sentences=2)
                    page = wikipedia.page(title)
                    results.append({
                        "title": title,
                        "body": summary[:200],
                        "href": page.url,
                        "source": "wikipedia",
                    })
                except Exception:
                    continue
            return results
        except Exception:
            return []

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_wiki_search, query, max_results)
            return future.result(timeout=8.0)
    except concurrent.futures.TimeoutError:
        return []


def _search_bing(query: str, max_results: int = 5) -> list[dict]:
    """使用 Bing 搜索（刮削，带超时）"""
    import concurrent.futures

    def _run():
        url = f"https://www.bing.com/search?q={quote_plus(query)}&count={max_results}&setlang=zh-cn"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        with httpx.Client(timeout=12.0, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            tree = lxml_html.fromstring(resp.text)

        results = []
        for li in tree.xpath('//ol[@id="b_results"]//li[contains(@class, "b_algo")]')[:max_results]:
            a_tag = li.find('h2/a')
            if a_tag is None:
                a_tag = li.find('a')
            if a_tag is None:
                continue
            href = a_tag.get("href", "")
            title = a_tag.text_content().strip()
            body = ""
            for div in li.iter('div'):
                if 'b_caption' in div.get('class', ''):
                    p = div.find('p')
                    if p is not None:
                        body = p.text_content().strip()[:200]
                    break
            if href and title:
                results.append({"title": title, "body": body, "href": href, "source": "bing"})
        return results

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_run)
            return future.result(timeout=15.0)
    except concurrent.futures.TimeoutError:
        return []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# 查询生成
# ---------------------------------------------------------------------------

def _build_search_queries(claim: str) -> list[str]:
    """
    根据可疑宣传语构建多组搜索查询

    策略：
    1. 原样搜索（确认产品/概念的真实性）
    2. 提取核心伪科学概念 + "辟谣" 或 "骗局"
    3. 提取权威背书关键词 + "虚假"
    4. 提取健康/疗效关键词 + "虚假宣传"
    """
    queries = [claim]

    # 提取产品名（【】内的内容，或首段关键词）
    product_match = re.search(r'【(.+?)】', claim)
    product = product_match.group(1) if product_match else ""

    scam_keywords = {
        "quantum": ["量子"],
        "magnetic": ["磁疗", "磁场"],
        "negative_ion": ["负离子"],
        "far_infrared": ["远红外", "红外"],
        "nano": ["纳米"],
        "graphene": ["石墨烯"],
        "detox": ["排毒", "毒素"],
        "meridian": ["经络", "疏通"],
        "cure_all": ["包治百病", "根治"],
        "stem_cell": ["干细胞"],
        "fulvene": ["富勒烯"],
    }

    added = set()
    added.add(claim)
    kw_claim = product or claim

    for category, keywords in scam_keywords.items():
        for kw in keywords:
            if kw in kw_claim:
                for suffix in [" 骗局", " 辟谣", " 虚假宣传", " 智商税"]:
                    q = f"{kw}{suffix}"
                    if q not in added:
                        queries.append(q)
                        added.add(q)
                break

    # 权威背书检测
    auth_patterns = [
        (r"(院士|中科院)", " 虚假背书"),
        (r"(央视|CCTV)", " 虚假广告"),
        (r"(国家专利|国家认证)", " 查询"),
        (r"(诺贝尔)", " 虚假关联"),
    ]
    for pat, suffix in auth_patterns:
        if re.search(pat, claim):
            q = re.search(pat, claim).group(1) + suffix
            if q not in added:
                queries.append(q)
                added.add(q)

    # 投资/返利检测
    if re.search(r"(返利|分红|佣金|日收益|稳赚)", claim):
        queries.append("消费返利 骗局 传销")
        queries.append("庞氏骗局 特征")

    # 去重截断
    unique = []
    for q in queries:
        if q not in unique:
            unique.append(q)
    return unique[:5]


# ---------------------------------------------------------------------------
# 搜索执行
# ---------------------------------------------------------------------------

def _execute_searches(search_queries: list[str], max_results: int) -> list[dict]:
    """对一组查询执行多后端搜索，合并去重结果"""
    claim_results = []
    seen_urls = set()
    max_per_query = max_results

    for query in search_queries:
        # Bing 优先（快，0.3-2s）
        hits = _search_bing(query, max_per_query)
        for hit in hits:
            url = hit.get("href", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                claim_results.append(hit)

        # DDGS（慢但覆盖更广，16s）— 只在首轮查询用
        if query == search_queries[0]:
            ddgs_hits = _search_ddgs(query, max_per_query)
            for hit in ddgs_hits:
                url = hit.get("href", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    claim_results.append(hit)

        # Wikipedia 查伪科学概念 — 只在首轮查询用
        if query == search_queries[0]:
            wiki_hits = _search_wikipedia(query, max_per_query // 2)
            for hit in wiki_hits:
                url = hit.get("href", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    claim_results.append(hit)

    return claim_results


# ---------------------------------------------------------------------------
# 摘要生成
# ---------------------------------------------------------------------------

def _summarize_findings(claim: str, results: list[dict]) -> str:
    """从搜索结果中提取核查结论摘要"""
    risk_indicators = ["骗局", "虚假", "辟谣", "智商税", "警告", "查处", "违规",
                       "不实", "误导", "虚假宣传", "诈骗", "陷阱", "上当",
                       "传销", "非法", "处罚", "取缔"]

    authoritative_patterns = [
        r"gov\.cn", r"12315", r"nhc\.gov", r"nmpa\.gov", r"fda\.gov",
        r"央视", r"新华社", r"人民日报", r"澎湃新闻",
        r"丁香医生", r"腾讯较真", r"科普中国", r"维基百科", r"wikipedia",
    ]

    all_text = " ".join([r.get("title", "") + " " + r.get("body", "") for r in results])

    found_risks = [w for w in risk_indicators if w in all_text]

    authoritative_sources = []
    for r in results:
        url = r.get("href", "")
        title = r.get("title", "")
        for pat in authoritative_patterns:
            if re.search(pat, url) or re.search(pat, title):
                authoritative_sources.append(r["title"])
                break

    # Wikipedia 直接查到了概念定义
    wiki_hits = [r for r in results if "wikipedia" in r.get("href", "")]
    wiki_summary = wiki_hits[0]["body"] if wiki_hits else ""

    parts = []
    if found_risks and authoritative_sources:
        parts.append("该声称相关的搜索结果中出现风险提示")
        parts.append(f"权威来源指出类似宣传存在误导性（{authoritative_sources[0][:30]}）")
        if wiki_summary:
            parts.append(f"Wikipedia 定义：{wiki_summary[:80]}")
        return "。".join(parts) + "。建议进一步核实。"
    elif found_risks:
        parts.append("搜索结果中发现多条涉及风险的讨论")
        if wiki_summary:
            parts.append(f"Wikipedia 说明该概念并非宣传所述：{wiki_summary[:80]}")
        return "。".join(parts) + "。该声称可信度较低，建议谨慎对待。"
    elif authoritative_sources:
        return f"未发现明显风险信号，搜索结果中有{authoritative_sources[0][:30]}等信息可供参考。"
    elif wiki_summary:
        return f"Wikipedia 对相关概念的解释与宣传存在差异：{wiki_summary[:100]}"
    else:
        return "联网搜索未返回与该声称直接相关的权威核查信息。"


# ---------------------------------------------------------------------------
# 公开接口
# ---------------------------------------------------------------------------

def search_claims(claims: list[str], max_results_per_query: int = 3) -> list[dict]:
    """
    对可疑宣传内容进行联网搜索核查（多后端）

    Args:
        claims: 可疑宣传语列表
        max_results_per_query: 每个查询返回的最大结果数

    Returns:
        [{"claim": ..., "search_queries": [...], "results": [...], "summary": ...}, ...]
    """
    if not claims or not is_search_available():
        return []

    result_groups = []

    for claim in claims[:5]:
        search_queries = _build_search_queries(claim)
        claim_results = _execute_searches(search_queries, max_results_per_query)

        if claim_results:
            result_groups.append({
                "claim": claim,
                "search_queries": search_queries,
                "results": claim_results[:6],
                "summary": _summarize_findings(claim, claim_results),
                "sources": list(set(r.get("source", "") for r in claim_results)),
            })

    return result_groups


def build_fact_check_prompt(fact_results: list[dict]) -> str:
    """
    将事实核查结果构建为提示词片段，供 AI 分析时参考使用。
    改进版：包含搜索摘要、每个来源的标题和正文片段，以及聚合结论。
    """
    if not fact_results:
        return ""

    parts = ["\n【联网事实核查参考信息】"]
    parts.append("以下信息来自搜索引擎交叉验证，请结合你的分析使用：")
    parts.append("")

    for idx, item in enumerate(fact_results, 1):
        parts.append(f"[{idx}] 可疑声称: {item['claim']}")
        parts.append(f"    核查摘要: {item['summary']}")
        sources = item.get("sources", [])
        if sources:
            parts.append(f"    数据来源: {', '.join(sources)}")

        if item["results"]:
            parts.append("    搜索到的相关资料:")
            for r in item["results"][:3]:
                title = r.get("title", "")
                body = r.get("body", "")
                href = r.get("href", "")
                src = r.get("source", "web")
                if body:
                    parts.append(f"    - [{src}] {title[:50]}")
                    parts.append(f"      摘要: {body[:150]}")
                    parts.append(f"      链接: {href}")
                else:
                    parts.append(f"    - [{src}] {title[:60]}")
        parts.append("")

    # 聚合结论
    risk_signals = []
    for item in fact_results:
        s = item.get("summary", "")
        if "风险" in s or "误导" in s or "骗局" in s:
            risk_signals.append(item["claim"])

    if risk_signals:
        parts.append("【检索聚合结论】")
        parts.append(f"搜索结果显示以下声称存在风险信号: {'; '.join(risk_signals[:3])}")
        parts.append("建议在评分时参考这些线索。")

    return "\n".join(parts)
