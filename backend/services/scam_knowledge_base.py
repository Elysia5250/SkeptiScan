"""
伪科学/骗局知识库 (Knowledge Base)
用于在 AI 分析前对文本进行预标记，识别已知的 scam 信号模式。

结构：
  - PSEUDO_TERMS: 伪科学术语 → 说明 + 风险等级
  - LEGIT_PATTERNS: 正规产品特征 → 说明（减分项）
  - MLM_PHRASES: 传销典型话术
  - RED_FLAG_PATTERNS: 复合风险模式（正则）
"""

import re

# ---------------------------------------------------------------------------
# 伪科学术语词典
# term → (category, explanation)
# category: 'pseudo' | 'medical' | 'authority' | 'mlm' | 'data_fraud'
# ---------------------------------------------------------------------------

PSEUDO_TERMS: dict[str, tuple[str, str]] = {
    # 伪科学包装 (25 pts max)
    "量子共振": ("pseudo", "量子共振是伪科学术语，真正的量子效应在宏观物体上不可观测"),
    "量子纠缠": ("pseudo", "量子纠缠是微观物理现象，用于商品宣传属于伪科学包装"),
    "量子能量": ("pseudo", "量子能量是伪科学概念，不具有任何已知的生物学效应"),
    "量子养生": ("pseudo", "将量子概念套用到养生领域属于伪科学营销"),
    "磁疗": ("pseudo", "静态磁场治疗缺乏高质量临床证据支持"),
    "磁疗仪": ("pseudo", "磁疗仪器不属于国家认可的医疗器械治疗手段"),
    "负离子治疗": ("pseudo", "负离子对疾病的治疗效果未被科学证实"),
    "小分子团水": ("pseudo", "小分子团水概念已被科学界否定，不具备特殊健康功效"),
    "活化细胞": ("pseudo", "活化细胞是模糊的伪科学概念，没有可验证的生物学定义"),
    "能量场": ("pseudo", "人体能量场没有科学依据，属于伪科学概念"),
    "经络疏通": ("pseudo", "经络学说的疗效声称需要具体验证，不可作为万能疗效"),
    "微循环改善": ("pseudo", "改善微循环作为万能疗效声称常用于保健品骗局"),
    "排出毒素": ("pseudo", "人体有自身排毒系统，不需要额外排毒产品"),
    "排毒": ("pseudo", "排毒作为商品声称缺乏科学定义和验证标准"),
    "纳米治疗": ("pseudo", "纳米技术用于治疗需要具体说明，模糊声称属于伪科学"),
    "石墨烯治疗": ("pseudo", "石墨烯在医疗领域的应用极为有限，多数声称不实"),
    "远红外治疗": ("pseudo", "远红外作为疾病治疗手段缺乏充分科学证据"),
    "富勒烯抗衰老": ("pseudo", "富勒烯的抗衰老效果被严重夸大，缺乏人体临床证据"),

    # 虚假医疗声称 (25 pts max)
    "根治": ("medical", "根治慢性病的声称属于违法医疗广告"),
    "治愈癌症": ("medical", "声称治愈癌症属于严重虚假医疗宣传"),
    "抗癌": ("medical", "非药品的'抗癌'声称缺乏法律和科学依据"),
    "降血压": ("medical", "声称非药品能降血压属于违法宣传"),
    "降血糖": ("medical", "声称非药品能降血糖属于违法宣传"),
    "替代化疗": ("medical", "替代化疗的声称极其危险，属于严重虚假宣传"),
    "告别药物": ("medical", "暗示可以停用处方药属于危险的不实信息"),
    "不用吃药": ("medical", "暗示可以停止药物治疗属于危险的虚假宣传"),
    "无效退款": ("medical", "常作为虚假承诺出现，实际退款条件苛刻"),
    "有效率达": ("medical", "有效率数据需要明确样本量和控制组"),
    "临床验证": ("medical", "需要具体说明验证机构和验证方式"),

    # 虚假权威背书 (15 pts max)
    "院士推荐": ("authority", "院士推荐需要核实验证，多数为虚假背书"),
    "院士研发": ("authority", "声称院士研发需要可核实的具体姓名和机构"),
    "央视推荐": ("authority", "央视推荐需要核实是否为广告或虚假宣传"),
    "CCTV推荐": ("authority", "CCTV推荐需要核实是否为广告或虚假宣传"),
    "国家专利": ("authority", "国家专利需要提供专利号供查询验证"),
    "国际认证": ("authority", "国际认证需要说明具体认证机构和认证标准"),
    "FDA认证": ("authority", "FDA认证不等于FDA批准，需要区分"),
    "诺贝尔": ("authority", "声称与诺贝尔奖有关联需要具体核实"),

    # 传销/非法集资 (20 pts max)
    "直推奖励": ("mlm", "直推奖励是典型的多级分销传销特征"),
    "间推奖": ("mlm", "间接提成是传销的典型特征"),
    "三代返利": ("mlm", "多级返利模式属于传销特征"),
    "拉人头": ("mlm", "以拉人头为核心的分销模式涉嫌传销"),
    "发展下线": ("mlm", "发展下线是传销的典型特征"),
    "团队业绩": ("mlm", "以团队业绩为计酬依据涉嫌传销"),
    "稳赚不赔": ("mlm", "保证收益属于非法金融活动特征"),
    "日收益": ("mlm", "每日固定高收益是非法集资典型特征"),
    "保本": ("mlm", "保本承诺属于非法金融活动特征"),
    "加盟费": ("mlm", "以加盟费为核心盈利模式需警惕传销风险"),
    "消费返利": ("mlm", "消费返利模式常与传销混淆"),
    "内部名额": ("mlm", "制造稀缺感的非法营销话术"),
    "限时入场": ("mlm", "限时入场是典型的高压销售话术"),
    "佣金": ("mlm_context", "推荐佣金需要区分正常销售与传销"),

    # 数据欺诈 (10 pts max)
    "有效率": ("data_fraud", "有效率需说明样本量、控制组和验证机构"),
    "临床数据显示": ("data_fraud", "需要具体说明数据来源和发布时间"),
    "研究表明": ("data_fraud", "需要具体说明研究机构和发表期刊"),
    "统计显示": ("data_fraud", "统计数据需说明样本量和收集方法"),
    "用户反馈": ("data_fraud", "用户反馈不等于科学证据"),
    "内部数据": ("data_fraud", "不可验证的内部数据可能为捏造"),
}

# ---------------------------------------------------------------------------
# 正规信号特征（减分项）
# ---------------------------------------------------------------------------

LEGIT_SIGNALS: list[tuple[re.Pattern, str, int]] = [
    (re.compile(r'国药准字[A-Z]'), "正规药品批准文号，可查", -5),
    (re.compile(r'国械注准\d'), "正规医疗器械注册号", -5),
    (re.compile(r'国食健字[GJ]\d'), "正规保健食品批准文号", -4),
    (re.compile(r'食健备\d'), "保健食品备案号", -3),
    (re.compile(r'工商营业执照|统一社会信用代码'), "正规工商注册", -2),
    (re.compile(r'(NIKE|飞利浦|联想|华润三九|云南白药|蒙牛|华为|罗氏)\S{0,4}(官方|正品|旗舰)'),
     "知名品牌官方渠道", -3),
    (re.compile(r'(国药准字|国械注准)\S{6,20}(?!.*治疗|.*治愈|.*根治)'), "有注册号且无明显违规声称", -5),
]

# ---------------------------------------------------------------------------
# 复合风险模式（正则）
# ---------------------------------------------------------------------------

RED_FLAG_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    ("bait_free_trial", re.compile(r'免费.{0,10}(领|送|得).{0,20}(仅需|只需|付)(运费|邮费|快递费|检测费)'),
     "免费试用 + 隐藏费用（钓鱼模式）"),
    ("bait_entry_price", re.compile(r'(仅需|只需|低至)\d+元.{0,30}(套餐|疗程|正式|完整).{0,10}\d{4,5}元'),
     "低价入门引流 + 高价后续收费"),
    ("mlm_recruit", re.compile(r'(推荐|邀请).{0,8}(好友|朋友|他人).{0,8}(佣金|奖励|返利|提成)'),
     "拉人头返利模式"),
    ("exclusive_time", re.compile(r'(仅限.{0,6}(老年|60|70)岁|名额.{0,4}限).{0,10}(报名|参加|购买)'),
     "针对特定弱势群体的定向营销"),
    ("fake_urgency", re.compile(r'(限时|限量|最后.{0,3}(天|名|份|套)|仅剩|秒杀|错过)'),
     "制造虚假紧迫感的高压销售"),
    ("contradictory_disclaimer", re.compile(r'(不(是|能|替代|具备).{0,10}(药|治疗|医疗)).{0,30}(但|不过|然而).{0,20}(效果|改善|有效)'),
     "让步免责：先否认治疗效果再暗示有效"),
    ("vague_citation", re.compile(r'(引用|根据|基于).{0,10}(文献|研究|论文).{0,5}(非本|非我|独立|综合|相关|公开)'),
     "引用不直接相关的文献作为证据"),
]

# ---------------------------------------------------------------------------
# 查询接口
# ---------------------------------------------------------------------------

def scan_text(text: str) -> dict:
    """
    扫描文本，返回匹配的 KB 条目

    Returns:
        {
            "pseudo_terms": [("量子共振", "pseudo", "说明"), ...],  # 最多5个
            "legit_signals": [("正规药品批准文号，可查", -5), ...],
            "red_flags": [("bait_free_trial", "免费试用+隐藏费用"), ...],
            "score_estimates": {"pseudo_estimate": 15, "mlm_estimate": 0, ...}
        }
    """
    if not text:
        return {"pseudo_terms": [], "legit_signals": [], "red_flags": [], "score_estimates": {}}

    result = {"pseudo_terms": [], "legit_signals": [], "red_flags": [], "score_estimates": {}}

    # 伪科学术语匹配
    seen_terms = set()
    for term, (category, explanation) in PSEUDO_TERMS.items():
        if term in text:
            if term not in seen_terms:
                seen_terms.add(term)
                result["pseudo_terms"].append((term, category, explanation))

    # 截断
    result["pseudo_terms"] = result["pseudo_terms"][:10]

    # 正规信号
    for pattern, desc, points in LEGIT_SIGNALS:
        if pattern.search(text):
            result["legit_signals"].append((desc, points))

    # 复合风险模式
    for name, pattern, desc in RED_FLAG_PATTERNS:
        if pattern.search(text):
            result["red_flags"].append((name, desc))

    # 估算分数
    pseudo_count = sum(1 for _, cat, _ in result["pseudo_terms"] if cat == "pseudo")
    medical_count = sum(1 for _, cat, _ in result["pseudo_terms"] if cat == "medical")
    authority_count = sum(1 for _, cat, _ in result["pseudo_terms"] if cat == "authority")
    mlm_count = sum(1 for _, cat, _ in result["pseudo_terms"] if cat == "mlm")
    data_count = sum(1 for _, cat, _ in result["pseudo_terms"] if cat == "data_fraud")

    result["score_estimates"] = {
        "pseudoscience": min(25, pseudo_count * 5),
        "false_medical": min(25, medical_count * 5),
        "fake_authority": min(15, authority_count * 5),
        "illegal_mlm": min(20, mlm_count * 5),
        "data_fraud": min(10, data_count * 5),
        "trusted_signals": sum(p for _, p in result["legit_signals"]),
    }

    return result


def build_kb_context(kb_result: dict) -> str:
    """将 KB 扫描结果格式化为提示词片段"""
    parts = []
    pseudo = kb_result.get("pseudo_terms", [])
    signals = kb_result.get("legit_signals", [])
    flags = kb_result.get("red_flags", [])

    if pseudo:
        parts.append("【系统预检发现的风险信号】")
        for term, cat, expl in pseudo[:5]:
            parts.append(f"  - 「{term}」({cat}): {expl}")

    if flags:
        parts.append("【系统预检发现的可疑营销模式】")
        for name, desc in flags[:3]:
            parts.append(f"  - {desc}")

    if signals:
        parts.append("【系统预检发现的可信信号】")
        for desc, pts in signals[:3]:
            parts.append(f"  - {desc} ({pts}分)")

    if not pseudo and not flags and not signals:
        parts.append("【系统预检】未发现明显已知风险信号，需进一步分析。")

    return "\n".join(parts)
