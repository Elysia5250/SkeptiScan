#!/usr/bin/env python3
"""
Generate a HARD test dataset (v3).

Categories:
A) 真实产品但听起来像骗局 — not_scam 混淆样本
B) 经典骗局案例加工       — scam
C) 偷换概念型（不煽动）    — scam  
D) 让步/钓鱼型广告        — scam
E) 正常商品              — not_scam

Usage:
    python generate_dataset.py --key sk-xxx          # LLM generates rich variations
    python generate_dataset.py                        # fallback templates
"""

import argparse
import csv
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

SEEDS = [
    # === A1-A5: 真实产品但听起来像骗局（not_scam）=== 混淆用
    ("not_scam", "低氘水",
     "低氘水（又名超轻水），氘含量＜125ppm，经中国疾病预防控制中心营养与食品安全所检验合格（报告编号：2024XXXX）。"
     "本品以天然冰川水为原料，采用专利同位素分离技术精制而成。"
     "国内外已有数百篇SCI论文探讨低氘水的生物学效应。产品标准号Q/LLS0001S，食品生产许可证SCXXXXXXXX。"
     "建议作为日常饮用水长期饮用，不宣称任何疾病治疗效果。"),

    ("not_scam", "经颅微电流刺激仪CES",
     "经颅微电流刺激仪（CES），国家药品监督管理局二类医疗器械注册（注册号：国械注准2024XXXX）。"
     "采用微米级电流（<2mA）通过耳夹电极刺激脑干，调节神经递质平衡。"
     "已获美国FDA 510(k)上市许可（K23XXXXX），在美军军事医学研究中被用于改善睡眠。"
     "适用于焦虑症、失眠的辅助治疗，须在医生指导下使用。注意事项：癫痫患者禁用。"),

    ("not_scam", "弱激光鼻腔照射治疗仪",
     "弱激光鼻腔照射治疗仪，国家二类医疗器械（注册证号：粤械注准2024XXXX）。"
     "采用650nm±10nm半导体激光，输出功率5mW，通过鼻腔黏膜照射毛细血管网，促使血液中一氧化氮解离。"
     "北京安贞医院、上海中山医院多中心临床试验表明，辅助治疗高脂血症总有效率78.5%。"
     "该技术源自NASA宇航员血液健康研究，后经瑞典科学家进一步验证。"
     "本产品仅作为辅助治疗手段，不能替代药物治疗。"),

    ("not_scam", "高压电位治疗仪",
     "高压电位治疗仪（High Voltage Potential Therapy），国家三类医疗器械注册（国械注准2024XXXX）。"
     "基于俄罗斯航天医学领域的高压电场技术，产生7000V高压负电场，作用于人体全身。"
     "经中国人民解放军总医院（301医院）临床研究证实，对失眠、慢性疼痛有显著改善效果。"
     "日本厚生劳动省将其列为家庭用医疗器（认证号：22500BZX00XXXXX）。"
     "使用时需保持环境干燥，心脏起搏器植入者禁用。"),

    ("not_scam", "脑电生物反馈训练仪",
     "脑电生物反馈仪（Neurofeedback），二类医疗器械（注册号：京械注准2024XXXX）。"
     "采用高精度脑电传感器（采样率512Hz，精度0.5μV），实时采集α/β/θ脑波频段。"
     "利用神经可塑性原理，通过视觉/听觉反馈训练增强目标脑波。"
     "已在国内多家三甲医院精神科、儿科用于ADHD辅助治疗（参考文献：中华精神科杂志2023;56(3):178-185）。"
     "训练效果需长期坚持，每次训练20-30分钟，每周3-5次。不适用于癫痫患者。"),

    # === B1-B5: 经典骗局案例加工（scam）===
    ("scam", "火疗养生调理套",
     "传承千年中医火疗秘法，以特制药酒配合火焰燃烧技术，从足三里到大椎穴全线疏通。"
     "本疗法由权氏中医研究院（已注销）创始人历经三十年研发，融合道医养生精华。"
     "内服外用相结合：外用火疗打开毛孔排毒通道，内服灵芝孢子粉激活自愈力。"
     "一个疗程调理：高血压、糖尿病、风湿骨痛、妇科问题全面改善。已有超过10万人受益。"
     "我们不做治疗，只做调理。调理好了是您的福气，调理不好是我们缘分不够。"
     "零风险创业：加盟火疗馆，月入十万不是梦！总部全方位支持。"),

    ("scam", "免疫增强口服液套餐",
     '本产品采用独家「仿野生」灵芝孢子粉+虫草多糖复合配方，通过调节树突状细胞活性增强机体免疫功能。'
     "中国科学院微生物研究所（合作关系，非官方认可）提供技术支持。"
     "多位肿瘤患者服用后白细胞计数显著回升，部分案例见内部资料汇编。"
     "我们不做虚假承诺，但临床统计显示92.7%的使用者免疫指标改善。"
     "由XX集团（前身：天津天狮生物工程有限公司）荣誉出品。"
     "购买满3000元成为VIP会员，享受团队业绩分红。推荐朋友加入，享受三代奖金。"),

    ("scam", "碱性体质调理套盒",
     "《人体酸碱平衡论》创始人亲传弟子团队研发（创始人已去世）。本产品依据「酸性体质是万病之源」理论，"
     "采用天然矿物质提取液，pH值8.5-9.0，每日三次每次10ml可快速纠正酸性体质。"
     "独家使用哈佛大学（同名同姓研究员）论文数据作为科研依据。"
     "一个调理周期（3个月）可降低癌症风险85%。建议搭配碱性饮食指导（另购）效果更佳。"
     "郑重声明：本产品为食品，不涉及疾病治疗。具体效果因人而异。"
     "限时赠送pH试纸一盒（100条），免费检测自身体质！"),

    ("scam", "精准基因防癌筛查套餐",
     "采用第三代纳米孔测序技术（宣传用语，非实际采用），一次检测覆盖3000种癌症相关基因位点。"
     "与北京某三甲医院（退休医生个人合作）提供报告解读服务。由某知名基因公司（已停止该业务）提供技术支持。"
     "检测发现高风险基因者，可搭配购买本中心定制防癌套餐（另收费29800元/年）。"
     "我们不是医疗机构，不提供诊断。检测结果仅供参考。但据统计，90%的早期癌症患者因未及时发现而错过最佳治疗期。"
     "现在购买基因检测套餐，免费赠送价值1980元的量子波动检测仪一台！"),

    ("scam", "互联网+消费创富系统",
     "全新S2B2C消费商模式，你消费我返利，消费变投资！"
     "购买498元礼包成为创客，享受平台利润分红+团队佣金。直推奖励20%，间推奖励10%，三代奖励5%。"
     "月入过万不是梦：推荐10人，团队裂变至100人，月被动收入超5万元！"
     "已有来自全国32个省市超过50万人参与，累计分配利润超过20亿元。"
     "平台资质：已取得ICP备案（正在办理中）、与某国有银行（仅签署意向协议）达成资金存管合作。"
     "温馨提示：投资有风险，入市需谨慎。但不尝试怎么知道不行呢？"),

    # === C1-C5: 偷换概念型（scam，不煽动语言）===
    ("scam", "南极磷虾油胶囊",
     "本产品采用南极纯磷虾油，磷脂型Omega-3含量高达56%，是普通鱼油的1.5倍。"
     "中国科学院南海海洋研究所（联合实验室合作项目）参与研发。上海某医院（研究合作协议，非临床验证）"
     "的初步实验表明，36例高血脂志愿者服用3个月后，总胆固醇平均下降1.2mmol/L。"
     "个体数据存在差异，我们如实陈述研究结果，不做疗效保证。"
     "本品为保健食品，保健功能：辅助降血脂。适宜人群：血脂偏高者。不替代药品治疗。"),

    ("scam", "干细胞修护精华液",
     "本产品采用瑞士苹果干细胞提取物（非人类干细胞），每瓶含5%苹果干细胞活性因子。"
     "实验室数据显示（体外细胞实验，非人体），该成分可延长成纤维细胞传代次数约30%。"
     "建议使用方法：每日早晚各一次，涂抹于清洁后的面部皮肤。"
     "研究表明（文献综述汇总），苹果干细胞在护肤品中的应用前景广阔。"
     "本产品为化妆品，不能替代医疗美容项目。实际效果因个人肤质而异。"),

    ("scam", "深海鱼油DHA高纯版",
     "每粒含DHA 400mg（实际含量200mg），EPA 60mg。采用秘鲁渔场深海鱼，分子蒸馏技术提纯。"
     "根据相关文献综合报道（多篇非针对本产品的独立研究），Omega-3对于心血管健康具有积极作用。"
     "引用论文来源：Journal of Lipid Research, 2018, 引用本产品相关综述论著3篇（非临床研究报告）。"
     "每日2粒，餐后服用。连续服用3个月评估效果。"
     "本品为保健食品，不替代药品。少年儿童、孕妇及哺乳期妇女慎用。"),

    ("scam", "石墨烯远红外发热护膝",
     "本产品内置石墨烯发热膜（石墨烯含量未公开），通电后释放6-14μm远红外波。"
     "实验室条件下（环境温度25℃，无风环境），测试显示可提高局部皮肤温度3-5℃。"
     "据用户反馈统计（在线问卷，样本量128人），约68%的使用者表示膝盖不适感有所缓解。"
     "温馨提示：本产品为电加热保暖护具，不具备治疗功能。如有病理性膝关节问题请及时就医。"
     "石墨烯发热技术也应用于航天、军事等高精尖领域（本产品所用材料非同等技术等级）。"),

    ("scam", "家用弱激光血压手环",
     "采用腕式激光照射技术，激光波长650nm，输出功率<1mW（符合Class I激光安全标准）。"
     "多项研究（引用中国知网收录论文，非本产品测试）表明低强度激光照射对改善微循环具有正面意义。"
     "注意事项：本产品为辅助保健用具，并非医疗器械，不能替代降压药物治疗。"
     "建议每日佩戴4-6小时，持续使用3个月后由医生评估血压控制情况。"
     "本产品已通过国家家用电器质量监督检验中心安全检测（报告编号：WDJ2024XXXX）。"),

    # === D1-D5: 让步/钓鱼型广告（scam）===
    ("scam", "野生林下参礼盒",
     "长白山野生林下参，生长年限15年以上（实际林下参5-8年）。产地直销，无中间商赚差价！"
     "只要198元！原价1280元的林下参礼盒，中秋特惠仅需198元。买一盒送一盒，再送枸杞一袋！"
     "每天一根参，换你十年少。但我们实事求是地说，人参不能替代药品治疗。"
     "前100名下单再送价值299元的养生壶一台。不满意7天无理由退换，运费我们承担。"
     "限量500份，售完即止！已售473份，仅剩27份！"),

    ("scam", "免费领智能血糖仪",
     "免费领！原价598元的智能语音血糖仪（市场同类产品实际价格50-80元），现在0元领取！"
     "只需支付耗材费299元（含50条试纸+采血针），后续试纸需从我司购买（单价6.9元/条，市场价2元/条以下）。"
     "活动说明：血糖仪免费送，耗材有偿提供。我们靠耗材赚钱。"
     "活动倒计时：最后3天！已有8652人成功领取。"
     "立即拨打电话400-XXX-XXXX免费领取！说朋友介绍再送维生素C一瓶！"),

    ("scam", "体验课低价引流-正式课高价",
     "3天2夜国学养生体验营，仅需99元（含食宿）！原价2980元。"
     "邀请国内知名国学大师（助理讲师）授课。体验营期间可免费体验：针灸、拔罐、艾灸各一次。"
     "体验营最后一天特设一对一健康咨询，将由高级健康管理师为您定制专属调理方案。"
     "调理方案费用：基础套餐19800元/年，尊享套餐39800元/年。报名体验营即送500元抵用券。"
     "郑重声明：体验营无强制消费。但名额有限，仅限60岁以上人士报名。"),

    ("scam", "祖传秘方免费试用装",
     "祖传七代秘方（创始人记忆中追溯），纯中药制剂（未取得药品批准文号）。"
     "免费申领3天试用装，只需支付快递费39元（实际快递成本12元）。"
     "3天内无效全额退款（需退回剩余产品，运费自理），有效则继续购买完整疗程（2980元/月）。"
     "为保障您的权益，建议收到试用装后先使用，满意再付款。"
     "我们不夸大效果。但用了没效果的人，99%是没有按疗程使用。"),

    ("scam", "中老年养生会员卡",
     "办理金卡会员（年费999元），享受全年免费体检（指定机构普通门诊价值300元）及养生讲座。"
     "会员专享：公司自产保健品全场8折、优先预约国内专家（退休副主任医师视频问诊5分钟）、定期旅游。"
     "一次性充值满5000元升级钻石会员，额外赠送价值2980元的多功能理疗仪一台（出厂价约200元）。"
     "每月15日会员日，全场买二送一！仅限会员参加。"
     "温馨提示：保健品不能替代药品。本卡一经售出，概不退换。"),

    # === E1-E5: 正常商品（not_scam）===
    ("not_scam", "必奇蒙脱石散",
     "必奇蒙脱石散，国药准字H20093611，海南先声药业生产。每袋3g，10袋装。"
     "用于治疗成人及儿童急慢性腹泻，口服后覆盖消化道黏膜形成保护屏障。"
     "世界卫生组织（WHO）推荐腹泻治疗基础用药。全国各大药房有售。"),

    ("not_scam", "美的破壁机",
     "美的破壁料理机PB系列，1200W大功率纯铜电机，转速38000转/分。8叶精钢刀头，微压熬煮技术。"
     "通过国家3C认证（证书号：202401XXXXXX）。京东自营旗舰店有售，享受全国联保。"),

    ("not_scam", "仁济医院挂号服务",
     "上海交通大学医学院附属仁济医院（三甲）官方挂号平台。可预约东院、西院各科室专家门诊。"
     "24小时退号服务。挂号费严格按照上海市物价局标准收取。不收取任何额外服务费。"
     "本平台为医院官方合作渠道，非黄牛代挂号。"),

    ("not_scam", "斯利安叶酸片",
     "斯利安叶酸片，国药准字H10970079，北京斯利安药业生产。每片含叶酸0.4mg，31片装。"
     "国家卫生健康委员会推荐备孕期及孕早期妇女补充用量。预防胎儿神经管畸形。"
     "全国各妇幼保健院、药房均有售，医保目录内药品。"),

    ("not_scam", "罗氏血糖仪套装",
     "罗氏（Roche）Accu-Chek Instant血糖仪，瑞士原装进口机芯。采用黄金电极试纸技术。"
     "通过ISO 15197:2013国际血糖监测系统准确性标准认证。含血糖仪+50条试纸+采血笔+便携包。"
     "罗氏中国官方授权销售（授权码：RC2024XXXX），全国联保2年。天猫医药健康旗舰店有售。"),
]


GENERATION_PROMPT = """You are generating adversarial test data for a consumer scam detection system.

SEED:
Label: {label}
Product: {name}
Description: {desc}

Task: Generate {count} variations for a hard test dataset.

Guidelines:
- Each variation must be 200-500 characters, a realistic product description paragraph.
- {"Scam case: Mix in convincing legitimacy signals (approval numbers, doctor quotes, clinical data). "
  "Use calm, professional language — no exclamation marks, no '🔥', no '限时优惠'. "
  "The scam should feel like a legitimate product ad that makes you pause and think. "
  "偷换概念: substitute concepts (lab data → human effect, individual case → general proof). "
  "让步修辞: '不能替代药品，但……' '虽然没有临床验证，但研究表明……' "
  "钓鱼: free trial with hidden costs, subscription traps." if label == "scam" else
  "Not_scam case: This is a legitimate product. It might sound pseudoscientific but has real "
  "credentials (FDA approval, clinical trials, government certification). "
  "Write it in a way that sounds potentially suspicious but is factually true."}
- Vary structure: product description, mechanism explanation, data citations, caution notices.
- Output only the variations, one per line. No markdown, no numbering."""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", default="", help="API key")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--api", default="https://api.deepseek.com")
    parser.add_argument("--model", default="deepseek-v4-flash")
    args = parser.parse_args()

    key = args.key
    if not key:
        try:
            from config import get_ai_config, has_api_key
            if has_api_key():
                cfg = get_ai_config()
                key, args.api, args.model = cfg["api_key"], cfg["base_url"], cfg["model"]
                print("[Setup] Using API key from config", file=sys.stderr)
        except Exception:
            pass

    if key:
        key = key.strip()
        # Save to .env for future runs
        env_path = Path(__file__).parent.parent / "backend" / ".env"
        env_content = f"OPENAI_API_KEY={key}\nOPENAI_API_BASE={args.api}\nOPENAI_MODEL={args.model}\n"
        if not any("OPENAI_API_KEY" in l for l in open(env_path, encoding="utf-8").read().split("\n") if os.path.exists(env_path)):
            with open(env_path, "a") as f:
                f.write("\n" + env_content)

    per_seed = args.count // len(SEEDS)
    extra = args.count % len(SEEDS)

    output_path = Path(__file__).parent / "dataset_100.csv"
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["text", "model_output", "ground_truth", "risk_level", "explanation"])

        total = 0
        for idx, (label, name, desc) in enumerate(SEEDS):
            n = per_seed + (1 if idx < extra else 0)
            print(f"  [{idx+1}/{len(SEEDS)}] {label}: {name} ({n})...", file=sys.stderr, end=" ")

            if key:
                variants = _generate_via_llm(name, desc, label, n, key, args.api, args.model)
            else:
                variants = _fallback(name, desc, label, n)

            for v in variants[:n]:
                w.writerow([v, "", label, "", ""])
                total += 1
            print("ok" if len(variants) >= n * 0.5 else f"only {len(variants)}", file=sys.stderr)

    print(f"\nDone: {total} cases -> {output_path}", file=sys.stderr)


def _generate_via_llm(name, desc, label, count, key, base_url, model):
    from openai import OpenAI
    prompt = GENERATION_PROMPT.format(label=label, name=name, desc=desc, count=count)
    try:
        client = OpenAI(api_key=key, base_url=base_url, timeout=90.0)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=4000,
            extra_body={"thinking": {"type": "disabled"}},
        )
        content = resp.choices[0].message.content or ""
        lines = [l.strip() for l in content.split("\n")
                 if l.strip() and len(l.strip()) > 50
                 and not l.strip().startswith(("#", "```"))]
        return lines[:count] if len(lines) >= max(3, count // 3) else _fallback(name, desc, label, count)
    except Exception as e:
        print(f"LLM err: {e}", file=sys.stderr)
        return _fallback(name, desc, label, count)


def _fallback(name, desc, label, count):
    """Smart fallback: generate variations by paraphrasing the seed."""
    # Simple approach: use different segments of the seed as variations
    paragraphs = [s.strip() for s in desc.replace("\n", " ").split("。") if s.strip()]
    if len(paragraphs) < 3:
        paragraphs = [desc[:120], desc[60:180], desc[120:240], desc[180:300], desc[:200]]

    results = []
    for i in range(count):
        # Combine 2-3 paragraphs in different orders with slight modifications
        selected = random.sample(paragraphs, min(3, len(paragraphs)))
        joined = "。".join(selected) + "。"
        # Add a random caution or detail
        addons = [
            "请仔细阅读产品说明书并在医师指导下使用。" if label == "not_scam" else "",
            "个体效果存在差异，请理性看待。" if label == "scam" else "",
            "本广告内容由品牌方提供，不代表本平台立场。",
            "市场价仅供参考，实际价格以门店为准。",
        ]
        addon = random.choice(addons)
        text = f"{name}。{joined}{addon}"[:600]
        results.append(text)

    return results[:count]


if __name__ == "__main__":
    main()
