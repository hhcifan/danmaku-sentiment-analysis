"""热度计算服务"""
import threading
from datetime import datetime
from collections import defaultdict
from loguru import logger
import db


# 线程锁
PRODUCT_LOCK = threading.Lock()

# 内存中的商品列表和提及记录
PRODUCTS = []
PRODUCT_MENTION_RECORDS = defaultdict(list)

# SocketIO 实例（由 app.py 注入）
_socketio = None


def set_socketio(sio):
    global _socketio
    _socketio = sio


def _broadcast_product_change():
    """商品增删后广播最新商品列表和热度排名"""
    if not _socketio:
        return
    with PRODUCT_LOCK:
        product_list = [
            {"id": p["id"], "name": p["name"], "mention_count": p["mention_count"],
             "heat": p["heat"]}
            for p in PRODUCTS
        ]
        heat_data = [
            {"id": p["id"], "name": p["name"], "heat": p["heat"],
             "mention_count": p["mention_count"],
             "positive_mention": p["positive_mention"],
             "negative_mention": p["negative_mention"],
             "pinned": p.get("pinned", 0)}
            for p in sorted(PRODUCTS, key=lambda x: (x.get("pinned", 0), x["heat"]), reverse=True)
        ]
    _socketio.emit("product:list", product_list)
    _socketio.emit("heat:update", heat_data)


def load_products_from_db():
    """从数据库加载商品列表到内存"""
    global PRODUCTS
    rows = db.query("SELECT product_id, product_name, mention_count, positive_mention, "
                     "negative_mention, heat, pinned, click_rate_factor FROM product_info")
    with PRODUCT_LOCK:
        PRODUCTS = []
        for row in rows:
            PRODUCTS.append({
                "id": row["product_id"],
                "name": row["product_name"],
                "mention_count": row["mention_count"] or 0,
                "positive_mention": row["positive_mention"] or 0,
                "negative_mention": row["negative_mention"] or 0,
                "heat": row["heat"] or 0.0,
                "pinned": row.get("pinned", 0) or 0,
                "click_rate_factor": row.get("click_rate_factor", 0.0) or 0.0,
            })
    return PRODUCTS


def add_product(product_id, product_name):
    """添加商品"""
    with PRODUCT_LOCK:
        for p in PRODUCTS:
            if p["id"] == product_id:
                return False
        product_data = {
            "id": product_id,
            "name": product_name,
            "mention_count": 0,
            "positive_mention": 0,
            "negative_mention": 0,
            "heat": 0.0,
            "pinned": 0,
            "click_rate_factor": 0.0,
        }
        PRODUCTS.append(product_data)

    db.upsert("product_info", {
        "product_id": product_id,
        "product_name": product_name,
        "mention_count": 0,
        "positive_mention": 0,
        "negative_mention": 0,
        "heat": 0.0,
        "pinned": 0,
        "click_rate_factor": 0.0,
    }, "product_id")

    # 广播商品列表和热度排名更新
    _broadcast_product_change()
    return True


def remove_product(product_id):
    """删除商品"""
    with PRODUCT_LOCK:
        PRODUCTS[:] = [p for p in PRODUCTS if p["id"] != product_id]
    db.execute("DELETE FROM product_info WHERE product_id = %s", (product_id,))
    db.execute("DELETE FROM conversion_data WHERE product_id = %s", (product_id,))
    db.execute("DELETE FROM product_keyword_feedback WHERE product_id = %s", (product_id,))

    # 广播商品列表和热度排名更新
    _broadcast_product_change()


def pin_product(product_id, pinned):
    """置顶/取消置顶商品"""
    with PRODUCT_LOCK:
        for p in PRODUCTS:
            if p["id"] == product_id:
                p["pinned"] = 1 if pinned else 0
                break
    db.execute("UPDATE product_info SET pinned = %s WHERE product_id = %s",
               (1 if pinned else 0, product_id))

    # 立即计算并推送最新排名
    ranking = calculate_heat()
    if _socketio:
        _socketio.emit("heat:update", [
            {"id": p["id"], "name": p["name"], "heat": p["heat"],
             "mention_count": p["mention_count"],
             "positive_mention": p["positive_mention"],
             "negative_mention": p["negative_mention"],
             "pinned": p.get("pinned", 0)}
            for p in ranking
        ])
    return ranking


def count_product_mention(text, sentiment):
    """统计商品提及次数并记录情绪"""
    text_lower = text.lower()
    current_time = datetime.now()
    with PRODUCT_LOCK:
        for product in PRODUCTS:
            if product["name"] in text_lower:
                product["mention_count"] += 1
                PRODUCT_MENTION_RECORDS[product["name"]].append((current_time, sentiment))
                if sentiment == "正向":
                    product["positive_mention"] += 1
                elif sentiment == "负向":
                    product["negative_mention"] += 1

                _sync_product_to_db(product)


def _sync_product_to_db(product):
    """同步商品数据到数据库"""
    db.upsert("product_info", {
        "product_id": product["id"],
        "product_name": product["name"],
        "mention_count": product["mention_count"],
        "positive_mention": product["positive_mention"],
        "negative_mention": product["negative_mention"],
        "heat": product["heat"],
        "pinned": product.get("pinned", 0),
        "click_rate_factor": product.get("click_rate_factor", 0.0),
    }, "product_id")


def _calculate_time_decay(mention_time):
    """计算时间衰减系数"""
    time_diff = (datetime.now() - mention_time).total_seconds() / 60
    if time_diff <= 10:
        return 1.0
    elif time_diff <= 20:
        return 0.8
    else:
        return 0.5


def _calculate_density_coefficient(product_name):
    """计算密度放大系数"""
    current_time = datetime.now()
    recent_mentions = [t for t, s in PRODUCT_MENTION_RECORDS[product_name]
                       if (current_time - t).total_seconds() <= 60]
    density = len(recent_mentions)
    if density > 10:
        return 1.5
    elif density > 5:
        return 1.2
    else:
        return 1.0


def calculate_heat():
    """
    计算所有商品热度值（含点击率因子）
    公式: 热度 = (基础提及分 + 情绪修正分) × 时间衰减 × 密度放大 × (1 + 点击率因子×0.5)
    返回按热度排序的商品列表（置顶商品优先）
    """
    with PRODUCT_LOCK:
        for product in PRODUCTS:
            name = product["name"]
            total_mentions = product["mention_count"]

            if total_mentions == 0:
                product["heat"] = 0.0
                continue

            # 基础提及分
            base_score = total_mentions * 1.0

            # 情绪修正分
            positive_score = product["positive_mention"] * 1.8
            negative_score = product["negative_mention"] * 1.5
            emotion_correction = positive_score - negative_score

            # 时间衰减系数
            time_decays = [_calculate_time_decay(t) for t, s in PRODUCT_MENTION_RECORDS[name]]
            avg_time_decay = sum(time_decays) / len(time_decays) if time_decays else 1.0

            # 密度放大系数
            density_coeff = _calculate_density_coefficient(name)

            # 点击率因子
            click_factor = 1 + product.get("click_rate_factor", 0.0) * 0.5

            # 最终热度
            total_heat = (base_score + emotion_correction) * avg_time_decay * density_coeff * click_factor
            product["heat"] = round(total_heat, 2)

            _sync_product_to_db(product)

        # 排序：置顶优先，其次按热度降序
        sorted_products = sorted(
            PRODUCTS,
            key=lambda x: (x.get("pinned", 0), x["heat"]),
            reverse=True
        )
        return sorted_products


def update_click_rate_factor(product_id, click_rate):
    """更新商品的点击率因子"""
    # 归一化到 0-1 范围
    factor = min(click_rate, 1.0)
    with PRODUCT_LOCK:
        for p in PRODUCTS:
            if p["id"] == product_id:
                p["click_rate_factor"] = factor
                break
    db.execute("UPDATE product_info SET click_rate_factor = %s WHERE product_id = %s",
               (factor, product_id))


def get_products():
    """获取当前商品列表"""
    with PRODUCT_LOCK:
        return list(PRODUCTS)


def get_heat_ranking():
    """获取热度排名"""
    return calculate_heat()
