"""商品级优化建议生成服务"""
from loguru import logger
import db
from services import heat_service


# ===================== 动作建议映射表 =====================
NEGATIVE_ACTION_MAP = {
    "太贵": "适当强调优惠活动或性价比",
    "贵了": "适当强调优惠活动或性价比",
    "好贵": "适当强调优惠活动或性价比",
    "死贵": "适当强调优惠活动或性价比",
    "价格高": "适当强调优惠活动或性价比",
    "买不起": "推荐平替或分期方案",
    "难看": "换个角度展示或更换模特",
    "丑": "换个角度展示或更换模特",
    "质量差": "展示商品细节或真实用户评价",
    "做工差": "展示商品细节或真实用户评价",
    "假货": "出示正品证明或授权书",
    "假的": "出示正品证明或授权书",
    "退货": "强调售后保障和退换政策",
    "退款": "强调售后保障和退换政策",
    "色差": "使用自然光展示实物颜色",
    "偏小": "详细讲解尺码对照表",
    "偏大": "详细讲解尺码对照表",
    "不好用": "演示正确的使用方法",
    "差": "重点强调核心卖点和优势",
    "坑": "展示真实使用效果和评价",
    "不值": "对比同类产品价格，突出性价比",
    "避雷": "正面回应用户顾虑，展示真实测评",
    "踩雷": "正面回应用户顾虑，展示真实测评",
    "智商税": "用数据和评测证明产品价值",
    "发货慢": "说明当前发货时效和物流安排",
}

POSITIVE_ACTION_MAP = {
    "喜欢": "保持当前讲解节奏，可加快上链接",
    "好看": "保持当前讲解节奏，可加快上链接",
    "划算": "趁热打铁推出限时优惠",
    "便宜": "趁热打铁推出限时优惠",
    "真香": "增加库存或延长秒杀时间",
    "买买买": "立即引导下单，强调库存紧张",
    "上链接": "立即上架链接",
    "已买": "引导买家分享体验，形成口碑",
    "下单了": "引导买家分享体验，形成口碑",
    "好用": "重点强调该卖点，引导更多转化",
    "质量好": "重点强调该卖点，引导更多转化",
}


def record_keyword_feedback(product_id, keyword, sentiment):
    """记录商品关键词反馈到数据库"""
    try:
        rows = db.query(
            "SELECT mention_count FROM product_keyword_feedback "
            "WHERE product_id = %s AND keyword = %s",
            (product_id, keyword)
        )
        if rows:
            db.execute(
                "UPDATE product_keyword_feedback SET mention_count = mention_count + 1, "
                "sentiment = %s WHERE product_id = %s AND keyword = %s",
                (sentiment, product_id, keyword)
            )
        else:
            db.insert("product_keyword_feedback", {
                "product_id": product_id,
                "keyword": keyword,
                "sentiment": sentiment,
                "mention_count": 1,
            })
    except Exception as e:
        logger.error(f"记录关键词反馈失败：{e}")


def process_danmu_keywords(text, keywords_list, sentiment):
    """
    处理弹幕分析结果，记录商品关键词反馈
    text: 弹幕文本
    keywords_list: [{"word": "太贵", "sentiment": "负向"}, ...]
    sentiment: 整体情感
    """
    text_lower = text.lower()
    products = heat_service.get_products()
    for product in products:
        if product["name"] in text_lower:
            for kw in keywords_list:
                record_keyword_feedback(product["id"], kw["word"], kw["sentiment"])


def generate_suggestions():
    """
    生成商品级优化建议
    返回: {
        "general": "整体建议",
        "product_suggestions": [
            {"product_name": "xxx", "keyword": "太贵", "sentiment": "负向",
             "count": 15, "advice": "适当强调优惠活动或性价比"}
        ]
    }
    """
    suggestions = {"general": "", "product_suggestions": []}

    products = heat_service.get_products()
    if not products:
        suggestions["general"] = "暂无商品数据，请先添加商品"
        return suggestions

    # 查询每个商品的高频关键词
    for product in products:
        rows = db.query(
            "SELECT keyword, sentiment, mention_count "
            "FROM product_keyword_feedback "
            "WHERE product_id = %s ORDER BY mention_count DESC LIMIT 5",
            (product["id"],)
        )
        for row in rows:
            keyword = row["keyword"]
            sentiment = row["sentiment"]
            count = row["mention_count"]

            if count < 2:
                continue

            # 生成具体建议
            if sentiment == "负向":
                action = NEGATIVE_ACTION_MAP.get(keyword, "关注并正面回应观众反馈")
                advice = f"解说{product['name']}时，大量弹幕反馈'{keyword}'（{count}次），建议{action}"
            elif sentiment == "正向":
                action = POSITIVE_ACTION_MAP.get(keyword, "继续保持当前讲解方式")
                advice = f"{product['name']}的'{keyword}'特点获得观众认可（{count}次），建议{action}"
            else:
                advice = f"观众对{product['name']}的'{keyword}'关注度较高（{count}次），建议重点讲解"

            suggestions["product_suggestions"].append({
                "product_name": product["name"],
                "keyword": keyword,
                "sentiment": sentiment,
                "count": count,
                "advice": advice,
            })

    # 生成整体建议
    total_products = len(products)
    total_mentions = sum(p["mention_count"] for p in products)
    total_positive = sum(p["positive_mention"] for p in products)
    total_negative = sum(p["negative_mention"] for p in products)

    if total_mentions > 0:
        neg_rate = total_negative / total_mentions
        pos_rate = total_positive / total_mentions
        if neg_rate > 0.4:
            suggestions["general"] = "负面情绪较多，建议强调性价比和优惠活动，积极回应观众疑虑"
        elif pos_rate > 0.6:
            suggestions["general"] = "正向情绪高涨，可加快上链接节奏，趁热推出限时优惠"
        else:
            suggestions["general"] = "情绪稳定，按原计划讲解即可，关注热度最高的商品"
    else:
        suggestions["general"] = "暂无弹幕数据，等待弹幕采集中..."

    # 按提及次数排序
    suggestions["product_suggestions"].sort(key=lambda x: x["count"], reverse=True)

    return suggestions
