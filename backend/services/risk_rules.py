"""
风险关键词规则检测模块
使用简单关键词匹配识别可疑营销话术
"""

# 高风险关键词：通常与虚假宣传、伪科学相关
HIGH_RISK_KEYWORDS = [
    "量子",
    "磁疗",
    "负离子",
    "排毒",
    "活化细胞",
    "抗癌",
    "调节免疫",
    "包治百病",
    "祖传秘方",
]

# 中风险关键词：可能涉及营销套路或夸大宣传
MEDIUM_RISK_KEYWORDS = [
    "院士推荐",
    "央视推荐",
    "国家专利",
    "限时优惠",
    "免费体验",
    "返利",
    "投资回报",
    "无效退款",
    "马上抢购",
    "限量发售",
]


def detect_risk_keywords(text: str) -> dict:
    """
    检测文本中包含的风险关键词

    Args:
        text: 待检测的文本内容

    Returns:
        {
            "high_risk_keywords": [...],   # 匹配到的高风险关键词
            "medium_risk_keywords": [...], # 匹配到的中风险关键词
            "all_matched": [...]           # 所有匹配到的关键词
        }
    """
    if not text:
        return {
            "high_risk_keywords": [],
            "medium_risk_keywords": [],
            "all_matched": [],
        }

    high_matched = [kw for kw in HIGH_RISK_KEYWORDS if kw in text]
    medium_matched = [kw for kw in MEDIUM_RISK_KEYWORDS if kw in text]

    return {
        "high_risk_keywords": high_matched,
        "medium_risk_keywords": medium_matched,
        "all_matched": high_matched + medium_matched,
    }