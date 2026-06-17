"""
AI 分析模块
负责调用大模型 API 对商品信息进行风险分析

功能：
  - 使用 OpenAI Compatible API（通过 openai SDK）
  - 支持三层提示词结构：BASE_SYSTEM_PROMPT + EXTRA_PROMPT + USER_PROMPT
  - 如果 API 调用失败或未配置 Key，返回模拟报告（mock 模式）
  - 结合规则检测模块的关键词匹配结果增强分析
"""

import json
import base64
from pathlib import Path
from typing import Optional

from config import get_ai_config, has_api_key
from services.risk_rules import detect_risk_keywords

# ---------------------------------------------------------------------------
# Mock 报告（无 API Key 或 API 调用失败时使用）
# ---------------------------------------------------------------------------

MOCK_REPORT = {
    "summary": "当前未配置可用 API，系统返回演示报告。",
    "risk_level": "中",
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
}

# ---------------------------------------------------------------------------
# BASE_SYSTEM_PROMPT：后端写死的基础系统提示词
# ---------------------------------------------------------------------------

BASE_SYSTEM_PROMPT = """你是一名"消费风险分析助手"，用于帮助用户识别商品宣传、养生产品、投资返利项目中的潜在风险。

你的任务不是直接判定商品一定是诈骗，也不是替代法律、医学或监管机构结论，而是根据用户提供的商品页面、截图、链接或文字，识别其中可能存在的风险信号，并给出谨慎、可解释的风险提示。

你需要重点关注以下风险类型：

1. 夸大疗效：
   如抗癌、降血压、治疗糖尿病、包治百病、快速见效、根治慢性病等。

2. 伪科学包装：
   如量子、磁疗、负离子、能量场、细胞活化、排毒、经络疏通、改善微循环等缺乏明确证据的宣传。

3. 虚假权威背书：
   如院士推荐、央视推荐、国家认证、专利产品、专家团队、国际大奖等，但没有给出可核验来源。

4. 健康焦虑营销：
   通过夸大疾病风险、制造恐惧、暗示"不买就会错过治疗机会"等方式诱导消费。

5. 投资返利风险：
   如高额回报、稳赚不赔、拉人头返利、消费返现、内部名额、限时入场等。

6. 诱导性销售：
   如限时优惠、免费体验、老人专享、名额有限、现场成交优惠、不给思考时间等。

输出要求：
1. 不要直接使用"诈骗""骗子""违法"等绝对结论，除非用户提供的信息中已经包含明确的官方处罚、法院判决或监管通报。
2. 优先使用"风险较高""证据不足""宣传依据不充分""建议谨慎购买""建议进一步核查"等表达。
3. 语言要简明，适合普通用户，尤其是中老年用户理解。
4. 必须输出 JSON，不要输出 Markdown。
5. JSON 字段必须为：
{
  "summary": "商品或页面概述",
  "risk_level": "低/中/高",
  "suspicious_claims": ["可疑宣传语1", "可疑宣传语2"],
  "marketing_tricks": ["营销套路1", "营销套路2"],
  "fact_check_suggestions": ["建议核查点1", "建议核查点2"],
  "purchase_advice": "购买建议",
  "elderly_friendly_warning": "给中老年用户的一句话提醒"
}"""

# ---------------------------------------------------------------------------
# Prompt 模板
# ---------------------------------------------------------------------------

ANALYSIS_PROMPT_TEMPLATE = """请对以下商品信息进行分析，识别其中的可疑营销话术和消费风险。

商品信息：
{product_info}

请以 JSON 格式返回分析结果。"""


def _get_mock_report(product_text: str = "") -> dict:
    """
    生成模拟分析报告
    如果传入的文本中匹配到了风险关键词，会在 mock 报告中进行相应调整
    """
    report = dict(MOCK_REPORT)

    if product_text:
        keywords = detect_risk_keywords(product_text)
        if keywords["all_matched"]:
            report["suspicious_claims"] = [
                f"商品使用了「{kw}」等概念进行宣传" for kw in keywords["all_matched"][:5]
            ] + report["suspicious_claims"][:3]

    return report


def _build_user_prompt(image_path: Optional[str], url: Optional[str]) -> str:
    """
    生成用户消息（USER_PROMPT）

    规则：
    - 如果有图片：要求模型先识别图片中的商品名称、宣传语、疗效承诺、价格、权威背书等信息
    - 如果有链接：基于链接进行初步分析，无法访问则说明是初步判断
    - 如果同时有图片和链接：优先基于图片内容分析，链接作为补充信息
    """
    has_image = image_path is not None and Path(image_path).exists()
    has_url = url is not None and url.strip() != ""

    parts = []

    if has_image and has_url:
        parts.append("用户上传了商品截图，同时提供了商品链接，请优先分析截图中的内容，链接信息作为补充参考。")
        parts.append(f"商品链接：{url}")
        parts.append(
            "请从截图中识别商品名称、宣传语、疗效承诺、价格信息、权威背书等内容，"
            "结合链接信息进行全面风险分析。"
        )
    elif has_image:
        parts.append("用户上传了商品截图，请从截图中识别商品名称、宣传语、疗效承诺、价格信息、权威背书等，并进行风险分析。")
    elif has_url:
        parts.append(f"用户提交了商品链接：{url}")
        parts.append(
            "请根据链接信息和用户提供的描述进行初步风险分析。"
            "如果无法访问网页内容，请明确说明'当前未能完整读取商品页面，仅基于用户提供的信息进行初步判断'。"
        )
    else:
        parts.append("用户未提供具体商品信息，请给出通用风险提示。")

    return "\n".join(parts)


def _call_api(image_path: Optional[str], url: Optional[str]) -> dict:
    """
    使用 OpenAI SDK 调用大模型 API

    使用 openai 库的 OpenAI 客户端，支持 OpenAI Compatible API。
    """
    from openai import OpenAI

    ai_config = get_ai_config()
    api_key = ai_config["api_key"]
    base_url = ai_config["base_url"]
    model = ai_config["model"]
    extra_prompt = ai_config["extra_prompt"]

    # 构建 messages
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

    # 第3层：USER_PROMPT（根据输入动态生成）
    user_prompt = _build_user_prompt(image_path, url)

    # 构建 user_content（可能包含图片）
    user_content = [{"type": "text", "text": user_prompt}]

    # 如果存在图片，添加到请求中
    if image_path and Path(image_path).exists():
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        ext = Path(image_path).suffix.lower()
        mime_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }.get(ext, "image/png")

        user_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{image_data}",
                "detail": "high",
            },
        })

    messages.append({"role": "user", "content": user_content})

    # 调用 API
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=60.0,
    )

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
        max_tokens=2000,
    )

    content = response.choices[0].message.content

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


def analyze_product(image_path: Optional[str] = None, url: Optional[str] = None) -> dict:
    """
    商品风险分析入口函数

    优先级：
    1. 如果有 API Key（运行时配置 > 环境变量），调用真实 API
    2. 如果没有 API Key 或 API 调用失败，返回 mock 报告

    Args:
        image_path: 上传的图片文件路径（可选）
        url: 商品链接（可选）

    Returns:
        (report_dict, mode_str)
        其中 mode_str 为 "real_api" 或 "mock"
    """
    if has_api_key():
        try:
            report = _call_api(image_path, url)
            return report, "real_api"
        except Exception as e:
            print(f"[Warning] API 调用失败，降级到 Mock 模式: {e}")
            return _get_mock_report(url or ""), "mock"

    # 无 API Key，使用 Mock 模式
    return _get_mock_report(url or ""), "mock"