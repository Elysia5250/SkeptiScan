"""
AI 分析模块
负责调用大模型 API 对商品信息进行风险分析

功能：
  - 使用 OpenAI Compatible API（通过 openai SDK）
  - 支持三层提示词结构：BASE_SYSTEM_PROMPT + EXTRA_PROMPT + USER_PROMPT
  - 文字提取（HTML 直接提取 → 降级 Playwright 截图 → OCR）
  - OCR 图片文字提取 → 增强关键词检测 + 补充分析上下文
  - 联网事实核查 → 对可疑声称自动搜索权威来源交叉验证
  - 如果 API 调用失败或未配置 Key，返回模拟报告（mock 模式）
  - 结合规则检测模块的关键词匹配结果增强分析
  - 不再向 LLM 发送图片，全部以文字形式输入，节省 token 成本
"""

import json
from pathlib import Path
from typing import Optional

from config import get_ai_config, has_api_key
from services.risk_rules import detect_risk_keywords
from services.ocr import extract_text, get_ocr_engine_name
from services.html_extractor import extract_page_text
from services.fact_checker import search_claims, build_fact_check_prompt, is_search_available

# ---------------------------------------------------------------------------
# Mock 报告（无 API Key 或 API 调用失败时使用）
# ---------------------------------------------------------------------------

MOCK_REPORT = {
    "summary": "Demo mode — no API key configured.",
    "risk_level": 5,
    "suspicious_claims": [
        "示例：调节免疫力，快速见效",
        "示例：限时优惠，最后一天",
        "示例：院士团队研发，国家专利",
    ],
    "marketing_tricks": [
        "示例：健康焦虑营销——利用对疾病的恐惧诱导购买",
        "示例：权威背书——虚构院士、央视推荐等增加可信度",
        "示例：限时紧迫——制造稀缺感催促冲动消费",
    ],
    "fact_check_suggestions": [
        "建议配置 API Key 后进行真实分析",
        "可以查看商品是否有国家药品监督管理局备案",
    ],
    "purchase_advice": "当前为演示模式，不能作为真实购买依据。请配置有效的 API Key 以获取真实分析。",
    "elderly_friendly_warning": "先别急着买，等家人帮你一起查清楚。正规产品不会用'量子''磁疗'这些模糊概念做宣传。",
    "detailed_analysis": "## Demo Mode\n\nThis is a mock report. Configure a real API key to get actual analysis.",
}

# ---------------------------------------------------------------------------
# BASE_SYSTEM_PROMPT：后端写死的基础系统提示词
# ---------------------------------------------------------------------------

BASE_SYSTEM_PROMPT = """You are a "Consumer Risk Analysis Assistant" — your job is to evaluate product claims, promotional materials, and investment offers, then produce a structured, evidence-based risk assessment.

You must assess on a **1–10 risk scale**, where:

| Level | Category | Meaning |
|-------|----------|---------|
| 1–3   | Safe     | Legitimate product from a known brand; normal marketing language, no false claims. |
| 4–6   | Suspicious | Some promotional exaggeration or unsubstantiated claims, but not obviously fraudulent. Buyer should be cautious. |
| 7–10  | Scam     | Clear false medical/therapeutic claims, pseudoscience packaging, fabricated authority endorsements, or obvious fraud indicators. |

Scoring criteria:
- **1–3**: Genuine product, no false efficacy claims, brand is verifiable. Normal sales language (e.g. "limited time offer", "free shipping") does NOT make it a scam.
- **4–6**: Contains some exaggerated or unverifiable claims, but not clearly fraudulent. May use marketing hype without crossing into pseudoscience.
- **7–8**: Uses pseudoscientific concepts (quantum, magnetic therapy, negative ions, detox, meridian疏通), fake authority endorsements ("academician recommended", "CCTV recommended" without verifiable sources), or disease-treatment promises for a non-medical product.
- **9–10**: Clear fraud: fake cures, investment scams promising guaranteed returns, fabricated credentials, explicit health/disease claims for unlicensed products.

Key risk signals to evaluate (individually, each adds to the score):
1. **False efficacy claims**: "cures cancer", "lowers blood pressure", "treats diabetes", "quick results", "根治" for chronic diseases.
2. **Pseudoscience packaging**: quantum, magnetic therapy, negative ions, energy fields, cell activation, detox, meridian疏通, improved microcirculation — terms with no scientific basis in the claimed context.
3. **Fake authority endorsements**: "academician recommended", "CCTV recommended", "national patent", "expert team", "international award" — without verifiable sources.
4. **Health anxiety marketing**: inducing fear of disease, implying "buy or miss the cure".
5. **Investment/financial risk**: guaranteed high returns, no risk, referral commissions, "limited slots", "internal quota".
6. **Concept substitution (偷换概念)**: Citing unrelated scientific research that does not actually test this product. Using in-vitro or animal data to imply human efficacy. Using a researcher with the same name as a famous person ("同名同姓研究员"). Citing papers from unrelated fields. This is a RED FLAG — legitimate products use their OWN clinical data, not unrelated citations.
7. **Concession disclaimer (让步免责声明)**: Phrases like "cannot replace medication, but..." "not a medical device, but..." "we don't make promises, but statistics show..." — these are often used to create an illusion of honesty while still implying efficacy. A genuine product simply states what it is without needing to deny what it isn't.
8. **Bait-and-switch pricing (钓鱼/后续收费)**: Free trial with hidden subscription costs ("仅付邮费" then requiring expensive consumables). Low-price entry with high-price upsell ("99元体验营" then "19800元套餐"). Free gift with undisclosed terms.
9. **Data fabrication indicators**: "Clinical data" without verifiable institution names. Vague percentages ("有效率96.5%") without sample size or control group. Citing "internal data" or "user feedback survey" as scientific evidence.

Output format:
- Respond with **valid JSON only**, no markdown wrapping (except the detailed_analysis field).
- The JSON schema is:

{
  "summary": "Brief summary of the product/promotion in Chinese.",
  "risk_level": <integer 1-10>,
  "suspicious_claims": ["Claim 1", "Claim 2"],
  "marketing_tricks": ["Tactic 1", "Tactic 2"],
  "fact_check_suggestions": ["Suggestion 1", "Suggestion 2"],
  "purchase_advice": "Purchase advice in Chinese",
  "elderly_friendly_warning": "One-sentence warning for elderly users in Chinese",
  "detailed_analysis": "Full analysis in **Markdown format** explaining why this score was given, what risk signals were found, what sources were checked, and what the final recommendation is. Write this in Chinese."
}"""


def _mock_risk_level(keywords: list[str]) -> int:
    """模拟模式下根据关键词数量估算风险等级"""
    count = len(keywords)
    if count >= 3:
        return 8
    elif count >= 1:
        return 5
    return 3


def _get_mock_report(ocr_text: str = "", url: str = "") -> dict:
    """
    生成模拟分析报告
    如果 OCR 提取到了文字或匹配到了风险关键词，会在 mock 报告中进行相应调整
    """
    report = dict(MOCK_REPORT)
    report["risk_level"] = 5  # default mock

    product_text = ocr_text or url or ""
    if product_text:
        keywords = detect_risk_keywords(product_text)
        if keywords["all_matched"]:
            report["risk_level"] = _mock_risk_level(keywords["all_matched"])
            report["suspicious_claims"] = [
                f"商品使用了「{kw}」等概念进行宣传" for kw in keywords["all_matched"][:5]
            ] + report["suspicious_claims"][:3]

    return report


def _build_user_prompt(
    product_text: Optional[str],
    url: Optional[str],
    source_type: Optional[str] = None,
    fact_check_context: Optional[str] = None,
) -> str:
    """
    生成用户消息（USER_PROMPT）

    规则：
    - product_text 是分析的主要依据（来自 HTML 提取或 OCR）
    - 如果有 URL 但未提取到文字，告诉 LLM 仅基于链接信息初步判断
    - 如果事实核查有结果：作为参考信息提供给模型
    """
    has_text = product_text and product_text.strip()
    has_url = url is not None and url.strip() != ""

    parts = []

    if has_text and has_url:
        source_label = {
            "html": "网页直接提取",
            "screenshot_ocr": "截图后 OCR 识别",
            "image_ocr": "用户上传图片 OCR 识别",
        }.get(source_type, "自动提取")

        parts.append(f"用户提交了商品链接：{url}")
        parts.append(f"以下是系统从该商品页面{source_label}到的文字内容：")
        parts.append("")
        parts.append(product_text.strip())
        parts.append("")
        parts.append("请基于以上文字内容进行风险分析，识别可疑宣传语、营销套路等。")
    elif has_text:
        source_label = "OCR 识别" if source_type == "image_ocr" else "提取"
        parts.append(f"以下是通过{source_label}获得的商品文字内容：")
        parts.append("")
        parts.append(product_text.strip())
        parts.append("")
        parts.append("请基于以上文字内容进行风险分析。")
    elif has_url:
        parts.append(f"用户提交了商品链接：{url}")
        parts.append(
            "当前未能读取到该页面的具体内容，请根据链接信息和用户提供的描述进行初步风险分析。"
            "并在报告中说明'当前未能完整读取商品页面，仅基于链接信息进行初步判断'。"
        )
    else:
        parts.append("用户未提供具体商品信息，请给出通用风险提示。")

    # 如果有事实核查结果，添加到提示词中
    if fact_check_context:
        parts.append(fact_check_context)

    return "\n".join(parts)


def _call_api(
    product_text: Optional[str],
    url: Optional[str],
    source_type: Optional[str] = None,
    fact_check_context: Optional[str] = None,
) -> dict:
    """
    使用 OpenAI SDK 调用大模型 API

    使用 openai 库的 OpenAI 客户端，支持 OpenAI Compatible API。
    不再发送图片，全部以文字形式输入。
    """
    from openai import OpenAI

    ai_config = get_ai_config()
    api_key = ai_config["api_key"]
    base_url = ai_config["base_url"]
    model = ai_config["model"]
    extra_prompt = ai_config["extra_prompt"]

    # 构建 messages（纯文本，无图片）
    messages = []

    # 第1层：BASE_SYSTEM_PROMPT
    messages.append({
        "role": "system",
        "content": BASE_SYSTEM_PROMPT
    })

    # 第2层：EXTRA_PROMPT（如果用户配置了额外提示词）
    if extra_prompt:
        messages.append({
            "role": "system",
            "content": f"以下是用户补充的分析要求，请在不违反基础规则的前提下参考：\n{extra_prompt}"
        })

    # 第3层：USER_PROMPT（仅文本）
    user_prompt = _build_user_prompt(product_text, url, source_type, fact_check_context)
    messages.append({"role": "user", "content": user_prompt})

    # 调用 API（禁用思考模式，避免 content 为空）
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=60.0,
    )

    request_kwargs = dict(
        model=model,
        messages=messages,
        temperature=0.2,
        max_tokens=2000,
    )

    # 部分模型（DeepSeek）需要显式禁用思考模式以保证 content 不为空
    # 部分 provider 不支持 extra_body，忽略即可
    try:
        request_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    except Exception:
        pass

    response = client.chat.completions.create(**request_kwargs)

    msg = response.choices[0].message
    content = msg.content

    # 处理 content 为空的情况（fallback 到 reasoning_content）
    if not content and hasattr(msg, "reasoning_content") and msg.reasoning_content:
        content = msg.reasoning_content

    if not content:
        raise ValueError("API 返回内容为空（可能是思考模式未正确关闭）")

    content = content.strip()

    # 尝试解析 JSON
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        # 尝试从 markdown 代码块中提取
        import re
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if match:
            result = json.loads(match.group(1))
        else:
            raise ValueError(f"无法从 API 响应中解析 JSON: {content[:200]}")

    return result


def analyze_product(image_path: Optional[str] = None, url: Optional[str] = None,
                    output_mode: str = "external",
                    raw_text: Optional[str] = None) -> tuple:
    """
    商品风险分析入口函数

    三种输入方式（按优先级）：
    1. raw_text → 直接使用提供的文案（测试/基准测试用，跳过提取步骤）
    2. url → HTML 提取正文（httpx, ~1s）→ 失败降级截图+OCR（~8s）
    3. image_path → OCR 提取文字

    流程：
    1. 获取商品文字
    2. 关键词规则检测（risk_rules）
    3. AI 分析（纯文本）
    4. 联网事实核查（仅 external 模式）

    Args:
        image_path: 上传的图片文件路径（可选）
        url: 商品链接（可选）
        output_mode: "external" 或 "benchmark"
        raw_text: 直接传入的文案（可选，优先级最高）

    Returns:
        (report_dict, mode_str)
    """
    # ---- Step 1: 文字提取 ----
    product_text = None
    source_type = None  # 'raw' | 'html' | 'screenshot_ocr' | 'image_ocr'

    # 1a. 直接文案（优先级最高，测试用）
    if raw_text and raw_text.strip():
        product_text = raw_text.strip()
        source_type = "raw"
        print(f"[Analyze] 直接文案输入 ({len(product_text)} 字符)")

    # 1b. URL → HTML 直接提取
    elif url and url.strip():
        page_text = extract_page_text(url.strip())
        if page_text:
            product_text = page_text
            source_type = "html"
            print(f"[Analyze] HTML 提取成功 ({len(page_text)} 字符)")
        else:
            # 1b. HTML 提取失败 → 降级截图 + OCR
            print("[Analyze] HTML 提取失败，降级到截图+OCR")
            try:
                from services.screenshot import capture_url_screenshot
                screenshot_path = capture_url_screenshot(url.strip())
                if screenshot_path:
                    ocr_result = extract_text(screenshot_path)
                    if ocr_result:
                        product_text = ocr_result
                        source_type = "screenshot_ocr"
                        print(f"[Analyze] 截图+OCR 成功 ({len(ocr_result)} 字符)")
            except Exception as e:
                print(f"[Warning] 截图降级失败: {e}")

    # 1c. 上传图片 → OCR
    ocr_from_image = None
    if image_path and Path(image_path).exists():
        ocr_from_image = extract_text(image_path)
        if ocr_from_image:
            # 如果已有 product_text（来自 URL），追加
            if product_text:
                product_text = product_text + "\n" + ocr_from_image
            else:
                product_text = ocr_from_image
                source_type = "image_ocr"
            print(f"[Analyze] 图片 OCR 成功 ({len(ocr_from_image)} 字符)")

    # ---- Step 2: AI 分析 ----
    if has_api_key():
        try:
            report = _call_api(product_text, url, source_type)
            mode = "real_api"
        except Exception as e:
            print(f"[Warning] API 调用失败，降级到 Mock 模式: {e}")
            report = _get_mock_report(ocr_from_image or product_text or "", url or "")
            mode = "mock"
    else:
        report = _get_mock_report(ocr_from_image or product_text or "", url or "")
        mode = "mock"

    # 将提取的文字附加到报告（前端可展示）
    if product_text:
        report["extracted_text"] = product_text[:2000]  # 截断，前端展示用

    # ---- Step 3: 联网事实核查（仅 external 模式启用增强） ----
    suspicious_claims = report.get("suspicious_claims", [])
    if suspicious_claims and is_search_available():
        try:
            fact_results = search_claims(suspicious_claims)
            if fact_results:
                report["fact_check_results"] = fact_results

                # external 模式：将事实核查结果注入第二轮分析增强报告
                if output_mode == "external" and mode == "real_api" and has_api_key():
                    try:
                        fact_context = build_fact_check_prompt(fact_results)
                        enhanced_report = _call_api(product_text, url, source_type, fact_context)
                        if product_text:
                            enhanced_report["extracted_text"] = product_text[:2000]
                        enhanced_report["fact_check_results"] = fact_results
                        report = enhanced_report
                        print("[FactCheck] 已注入事实核查结果进行增强分析")
                    except Exception as e:
                        print(f"[Warning] 增强分析失败，使用原始报告: {e}")
        except Exception as e:
            print(f"[Warning] 事实核查失败: {e}")

    # ---- Step 4: 关键词检测（始终运行） ----
    keyword_text = product_text or url or ""
    if keyword_text:
        keywords = detect_risk_keywords(keyword_text)
        if keywords["all_matched"]:
            report["detected_keywords"] = keywords

    return report, mode