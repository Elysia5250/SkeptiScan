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
import re
from pathlib import Path
from typing import Optional

from config import get_ai_config, has_api_key

# ---------------------------------------------------------------------------
# 安全过滤：异常信息中可能包含 API Key，需要打码
# ---------------------------------------------------------------------------

_API_KEY_PATTERN = re.compile(r'(sk-[a-zA-Z0-9]{10,})\S*')


def _safe_error(e: Exception) -> str:
    """返回过滤后的异常信息，确保不含 API Key"""
    msg = str(e)
    msg = _API_KEY_PATTERN.sub("sk-...", msg)
    # 也过滤 Bearer token
    msg = msg.replace("Bearer sk-", "Bearer ***")
    if len(msg) > 200:
        msg = msg[:200] + "..."
    return msg

from services.risk_rules import detect_risk_keywords
from services.ocr import extract_text, get_ocr_engine_name
from services.html_extractor import extract_page_text
from services.fact_checker import search_claims, build_fact_check_prompt, is_search_available
from services.scam_knowledge_base import scan_text, build_kb_context

# ---------------------------------------------------------------------------
# Mock 报告（无 API Key 或 API 调用失败时使用）
# ---------------------------------------------------------------------------

MOCK_REPORT = {
    "summary": "Demo mode — no API key configured.",
    "risk_level": 5,
    "score_breakdown": {"pseudoscience": 0, "false_medical": 0, "fake_authority": 0,
                        "illegal_mlm": 0, "deceptive_marketing": 0, "data_fraud": 0,
                        "trusted_signals": 0},
    "triggered_items": ["示例：伪科学包装 (+5): 使用了量子概念", "示例：虚假医疗声称 (+10): 宣称治疗高血压"],
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

BASE_SYSTEM_PROMPT = """You are a "Consumer Risk Analysis Assistant". Evaluate product promotions and identify risk signals.

For each product, output JSON with:
- summary: brief product summary in Chinese
- risk_level: integer 1-10 (1-3=safe, 4-6=suspicious, 7-10=scam)
- suspicious_claims: list of suspicious claims found
- marketing_tricks: list of marketing tactics used
- fact_check_suggestions: list of verification suggestions
- purchase_advice: purchase recommendation in Chinese
- elderly_friendly_warning: one-sentence warning for elderly in Chinese
- detailed_analysis: full Markdown analysis in Chinese explaining reasoning

## Risk Signals

1. Pseudoscience: quantum, magnetic, negative ions, detox, meridian, nano-therapy
2. False medical claims: promises to cure/treat diseases, "不用吃药", vague efficacy data
3. Fake authority: unverifiable "院士"/"CCTV" endorsements, patents without numbers
4. MLM/illegal: referral commissions, guaranteed returns, recruitment fees
5. Deceptive marketing: urgency, bait-and-switch, hidden fees
6. Data fraud: citing non-applicable research, lab data implied as human evidence
7. Trusted signals (lower risk): verifiable 国药准字/国械注准, well-known brands, no health claims

## Scoring Examples

Example 1 — Clear scam (risk 8):
Input: "量子养生杯，院士推荐，包治百病，限时特惠仅需998元"
Analysis: pseudoscience(量子养生) + fake authority(院士推荐) + false medical(包治百病) + urgency → scam

Example 2 — Citation fraud (risk 7, tricky):
Input: "南极磷虾油胶囊。本品为保健食品，不替代药品治疗。中国科学院南海研究所参与研发。上海某医院初步实验表明36例志愿者服用后胆固醇下降。个体数据存在差异，我们如实陈述研究结果，不做疗效保证。"
Key insight: The product says "不做疗效保证" and "不替代药品", but cites "上海某医院实验" with "36例胆固醇下降". This is CONCEPT SUBSTITUTION — citing a limited study to imply efficacy while disclaiming responsibility. The disclaimer "不做疗效保证" does NOT make it safe. Score as data fraud + false medical claims.

Example 3 — Concession + data bait (risk 6, tricky):
Input: "石墨烯远红外发热护膝。本产品为电加热保暖护具，不具备治疗功能。实验室测试显示可提高局部皮肤温度3-5℃。用户反馈约68%使用者表示膝盖不适感有所缓解。"
Key insight: "不具备治疗功能" followed by "68%使用者表示缓解" is a CONCESSION DISCLAIMER — saying it's not medical while implying medical benefit. Score higher than it appears.

Example 4 — Legitimate but unusual (risk 2):
Input: "弱激光鼻腔照射治疗仪，国家二类医疗器械（注册号：粤械注准2024XXXX）。采用650nm半导体激光照射鼻腔毛细血管网。北京安贞医院多中心临床试验表明辅助治疗高脂血症总有效率78.5%。该技术源自NASA宇航员血液健康研究。本产品仅作为辅助治疗手段。"
Key insight: Despite "NASA research" sounding suspicious, this is a legitimate medical device with verifiable registration number (粤械注准) and named hospital trials. The "NASA" reference is factual. Score low (2) because of the verifiable credentials.

Output valid JSON only. No markdown wrapping."""


# ---------------------------------------------------------------------------
# 评分计算：根据 score_breakdown 计算最终 risk_level
# ---------------------------------------------------------------------------

_SCORE_THRESHOLDS = [(15, 1), (20, 2), (25, 3), (35, 4), (40, 5),
                     (50, 6), (60, 7), (70, 8), (85, 9)]


def _compute_risk_level(score_breakdown: dict) -> int:
    """根据检查清单得分汇总计算 1-10 风险等级"""
    total = max(0, sum(score_breakdown.values()))
    for threshold, level in _SCORE_THRESHOLDS:
        if total <= threshold:
            return level
    return 10


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
    如果匹配到了风险关键词，会在 mock 报告中进行相应调整
    """
    report = dict(MOCK_REPORT)
    report["score_breakdown"] = dict(MOCK_REPORT["score_breakdown"])
    report["triggered_items"] = []

    product_text = ocr_text or url or ""
    if product_text:
        keywords = detect_risk_keywords(product_text)
        matched = keywords["all_matched"]
        if matched:
            score = _mock_risk_level(matched)
            pseudo_score = min(25, len(matched) * 5)
            report["score_breakdown"]["pseudoscience"] = pseudo_score
            report["risk_level"] = _compute_risk_level(report["score_breakdown"])
            report["triggered_items"] = [
                f"伪科学包装 (+5): 使用了「{kw}」概念" for kw in matched[:5]
            ]
            report["suspicious_claims"] = [
                f"商品使用了「{kw}」等概念进行宣传" for kw in matched[:5]
            ] + report["suspicious_claims"][:3]
    else:
        report["risk_level"] = _compute_risk_level(report["score_breakdown"])

    return report


def _build_user_prompt(
    product_text: Optional[str],
    url: Optional[str],
    source_type: Optional[str] = None,
    fact_check_context: Optional[str] = None,
    kb_context: Optional[str] = None,
) -> str:
    """
    生成用户消息（USER_PROMPT）
    接受 KB 预检结果和事实核查结果作为额外上下文。
    """
    has_text = product_text and product_text.strip()
    has_url = url is not None and url.strip() != ""

    parts = []

    if has_text and has_url:
        source_label = {"html": "网页直接提取", "screenshot_ocr": "截图后 OCR 识别",
                        "image_ocr": "用户上传图片 OCR 识别"}.get(source_type, "自动提取")
        parts.append(f"用户提交了商品链接：{url}")
        parts.append(f"以下是系统从该商品页面{source_label}到的文字内容：")
        parts.append(""); parts.append(product_text.strip()); parts.append("")
        parts.append("请基于以上文字内容进行风险分析，识别可疑宣传语、营销套路等。")
    elif has_text:
        source_label = "OCR 识别" if source_type == "image_ocr" else "提取"
        parts.append(f"以下是通过{source_label}获得的商品文字内容：")
        parts.append(""); parts.append(product_text.strip()); parts.append("")
        parts.append("请基于以上文字内容进行风险分析。")
    elif has_url:
        parts.append(f"用户提交了商品链接：{url}")
        parts.append("当前未能读取到该页面的具体内容，请根据链接信息和用户提供的描述进行初步风险分析。"
                     "并在报告中说明'当前未能完整读取商品页面，仅基于链接信息进行初步判断'。")
    else:
        parts.append("用户未提供具体商品信息，请给出通用风险提示。")

    # KB 预检结果（最前面的参考信息）
    if kb_context:
        parts.append(f"\n{kb_context}")

    # 联网事实核查结果（第二轮注入用）
    if fact_check_context:
        parts.append(f"\n{fact_check_context}")

    return "\n".join(parts)


def _call_api(
    product_text: Optional[str],
    url: Optional[str],
    source_type: Optional[str] = None,
    fact_check_context: Optional[str] = None,
    kb_context: Optional[str] = None,
) -> dict:
    """
    使用 OpenAI SDK 调用大模型 API
    支持注入 KB 预检结果和联网事实核查结果。
    返回中包含 score_breakdown，后端据此计算 risk_level。
    """
    from openai import OpenAI

    ai_config = get_ai_config()
    api_key = ai_config["api_key"]
    base_url = ai_config["base_url"]
    model = ai_config["model"]
    extra_prompt = ai_config["extra_prompt"]

    messages = []

    # 第1层：BASE_SYSTEM_PROMPT
    messages.append({"role": "system", "content": BASE_SYSTEM_PROMPT})

    # 第2层：EXTRA_PROMPT（如果用户配置了额外提示词）
    if extra_prompt:
        messages.append({
            "role": "system",
            "content": f"以下是用户补充的分析要求，请在不违反基础规则的前提下参考：\n{extra_prompt}"
        })

    # 第3层：USER_PROMPT（含 KB + 事实核查上下文）
    user_prompt = _build_user_prompt(product_text, url, source_type, fact_check_context, kb_context)
    messages.append({"role": "user", "content": user_prompt})

    # 调用 API
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=60.0)
    request_kwargs = dict(model=model, messages=messages, temperature=0.2, max_tokens=2500)
    try:
        request_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    except Exception:
        pass

    response = client.chat.completions.create(**request_kwargs)

    msg = response.choices[0].message
    content = msg.content
    if not content and hasattr(msg, "reasoning_content") and msg.reasoning_content:
        content = msg.reasoning_content
    if not content:
        raise ValueError("API 返回内容为空")

    content = content.strip()

    # 解析 JSON
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if match:
            result = json.loads(match.group(1))
        else:
            raise ValueError(f"AI 输出格式错误: {content[:200]}")

    # 确保 score_breakdown 存在（从 KB 估算或 risk_level 换算）
    if "score_breakdown" not in result:
        result["score_breakdown"] = {"pseudoscience": 0, "false_medical": 0, "fake_authority": 0,
                                     "illegal_mlm": 0, "deceptive_marketing": 0, "data_fraud": 0,
                                     "trusted_signals": 0}
    if "triggered_items" not in result:
        result["triggered_items"] = []
    if "risk_level" not in result or not isinstance(result.get("risk_level"), int):
        result["risk_level"] = 5

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

    # ---- Step 2: 知识库预检（KB） ----
    kb_context = None
    if product_text:
        kb_result = scan_text(product_text)
        if kb_result.get("pseudo_terms") or kb_result.get("red_flags") or kb_result.get("legit_signals"):
            kb_context = build_kb_context(kb_result)
            # 将 KB 估算分暂存，可用于后续校验
            kb_estimates = kb_result.get("score_estimates", {})
            if any(v > 0 for v in kb_estimates.values()):
                print(f"[KB] 发现 {len(kb_result['pseudo_terms'])} 个风险术语, "
                      f"{len(kb_result['red_flags'])} 个可疑模式, "
                      f"估算分: {sum(kb_estimates.values())}")

    # ---- Step 3: AI 分析（注入 KB 预检结果） ----
    if has_api_key():
        try:
            report = _call_api(product_text, url, source_type, kb_context=kb_context)
            mode = "real_api"
        except Exception as e:
            print(f"[Warning] API 调用失败，降级到 Mock 模式: {_safe_error(e)}")
            report = _get_mock_report(ocr_from_image or product_text or "", url or "")
            mode = "mock"
    else:
        report = _get_mock_report(ocr_from_image or product_text or "", url or "")
        mode = "mock"

    # 将提取的文字附加到报告
    if product_text:
        report["extracted_text"] = product_text[:2000]

    # ---- Step 4: 联网事实核查（仅 external 模式启用） ----
    if output_mode == "external":
        suspicious_claims = report.get("suspicious_claims", [])
        if suspicious_claims and is_search_available():
            try:
                fact_results = search_claims(suspicious_claims)
                if fact_results:
                    report["fact_check_results"] = fact_results

                    # 事实核查结果 + KB 结果注入第二轮增强分析
                    if mode == "real_api" and has_api_key():
                        try:
                            fact_context = build_fact_check_prompt(fact_results)
                            enhanced_report = _call_api(product_text, url, source_type,
                                                        fact_check_context=fact_context,
                                                        kb_context=kb_context)
                            if product_text:
                                enhanced_report["extracted_text"] = product_text[:2000]
                            enhanced_report["fact_check_results"] = fact_results
                            report = enhanced_report
                            print("[FactCheck] 已注入事实核查+KB结果进行增强分析")
                        except Exception as e:
                            print(f"[Warning] 增强分析失败，使用原始报告: {_safe_error(e)}")
            except Exception as e:
                print(f"[Warning] 事实核查失败: {e}")

    # ---- Step 5: 关键词检测（始终运行） ----

    # ---- Step 4: 关键词检测（始终运行） ----
    keyword_text = product_text or url or ""
    if keyword_text:
        keywords = detect_risk_keywords(keyword_text)
        if keywords["all_matched"]:
            report["detected_keywords"] = keywords

    return report, mode