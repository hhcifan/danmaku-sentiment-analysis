"""用户分层推荐服务"""
from loguru import logger
import db
from services import heat_service


def record_behavior(user_id, product_id, action_type):
    """记录用户行为"""
    db.insert("user_behavior", {
        "user_id": user_id,
        "product_id": product_id,
        "action_type": action_type,
    })

    # 同时更新转化数据
    _update_conversion_from_behavior(product_id, action_type)


def _update_conversion_from_behavior(product_id, action_type):
    """根据用户行为自动更新转化数据"""
    field_map = {"click": "click_count", "cart": "cart_count", "order": "order_count"}
    field = field_map.get(action_type)
    if not field:
        return

    rows = db.query(
        "SELECT * FROM conversion_data WHERE product_id = %s", (product_id,)
    )
    if rows:
        db.execute(
            f"UPDATE conversion_data SET {field} = {field} + 1 WHERE product_id = %s",
            (product_id,)
        )
    else:
        data = {"product_id": product_id, "click_count": 0, "cart_count": 0, "order_count": 0}
        data[field] = 1
        db.insert("conversion_data", data)

    # 重新计算转化率
    _recalculate_conversion_rates(product_id)


def _recalculate_conversion_rates(product_id):
    """重新计算商品转化率"""
    rows = db.query(
        "SELECT click_count, cart_count, order_count FROM conversion_data WHERE product_id = %s",
        (product_id,)
    )
    if not rows:
        return

    row = rows[0]
    clicks = row["click_count"] or 0
    carts = row["cart_count"] or 0
    orders = row["order_count"] or 0

    click_rate = min(clicks / 100.0, 1.0) if clicks > 0 else 0.0
    cart_rate = carts / clicks if clicks > 0 else 0.0
    order_rate = orders / clicks if clicks > 0 else 0.0

    db.execute(
        "UPDATE conversion_data SET click_rate=%s, cart_rate=%s, order_rate=%s WHERE product_id=%s",
        (round(click_rate, 4), round(cart_rate, 4), round(order_rate, 4), product_id)
    )

    # 更新热度服务中的点击率因子
    heat_service.update_click_rate_factor(product_id, click_rate)


def get_user_level(user_id):
    """
    判定用户层级
    返回: "high_value" | "potential" | "browser"
    """
    orders = db.query(
        "SELECT COUNT(*) as cnt FROM user_behavior WHERE user_id=%s AND action_type='order'",
        (user_id,)
    )
    if orders and orders[0]["cnt"] > 0:
        return "high_value"

    carts = db.query(
        "SELECT COUNT(*) as cnt FROM user_behavior WHERE user_id=%s AND action_type='cart'",
        (user_id,)
    )
    if carts and carts[0]["cnt"] > 0:
        return "potential"

    return "browser"


def recommend_for_user(user_id):
    """
    为指定用户生成个性化推荐
    返回: {"user_id", "level", "level_name", "recommended_products": [...]}
    """
    level = get_user_level(user_id)
    level_names = {
        "high_value": "高价值用户",
        "potential": "潜在用户",
        "browser": "浏览用户"
    }

    products = heat_service.get_products()
    if not products:
        return {
            "user_id": user_id,
            "level": level,
            "level_name": level_names[level],
            "recommended_products": []
        }

    # 查询用户所有行为
    behaviors = db.query(
        "SELECT product_id, action_type FROM user_behavior WHERE user_id = %s",
        (user_id,)
    )

    # 计算每个商品的用户行为分
    product_scores = {}
    ordered_products = set()
    carted_products = set()
    action_weights = {"order": 5, "cart": 3, "click": 1}

    for b in behaviors:
        pid = b["product_id"]
        score = action_weights.get(b["action_type"], 0)
        product_scores[pid] = product_scores.get(pid, 0) + score
        if b["action_type"] == "order":
            ordered_products.add(pid)
        elif b["action_type"] == "cart":
            carted_products.add(pid)

    # 热度分归一化
    max_heat = max((p["heat"] for p in products), default=1) or 1
    heat_map = {p["id"]: p["heat"] / max_heat for p in products}

    # 生成推荐列表
    candidates = []
    for p in products:
        pid = p["id"]

        # 排除已下单商品
        if pid in ordered_products:
            continue

        # 行为分
        behavior_score = product_scores.get(pid, 0)

        # 加购未下单加权
        if pid in carted_products:
            behavior_score += 4

        # 融合热度分（0.4权重）
        heat_score = heat_map.get(pid, 0) * 10
        final_score = behavior_score * 0.6 + heat_score * 0.4

        reason = _get_recommend_reason(pid, level, carted_products, behavior_score)

        candidates.append({
            "product_id": pid,
            "product_name": p["name"],
            "heat": p["heat"],
            "score": round(final_score, 2),
            "reason": reason,
        })

    # 排序取Top-5
    candidates.sort(key=lambda x: x["score"], reverse=True)
    recommended = candidates[:5]

    return {
        "user_id": user_id,
        "level": level,
        "level_name": level_names[level],
        "recommended_products": recommended
    }


def _get_recommend_reason(product_id, level, carted_products, behavior_score):
    """生成推荐理由"""
    if product_id in carted_products:
        return "您已加购，赶紧下单吧"
    if level == "high_value":
        if behavior_score > 0:
            return "根据您的浏览偏好推荐"
        return "热门商品推荐"
    if level == "potential":
        if behavior_score > 0:
            return "您可能感兴趣"
        return "热销商品推荐"
    return "热门商品推荐"


def get_user_behaviors(user_id):
    """获取用户行为历史"""
    rows = db.query(
        "SELECT ub.user_id, ub.product_id, pi.product_name, ub.action_type, ub.created_at "
        "FROM user_behavior ub "
        "LEFT JOIN product_info pi ON ub.product_id = pi.product_id "
        "WHERE ub.user_id = %s ORDER BY ub.created_at DESC LIMIT 100",
        (user_id,)
    )
    for row in rows:
        if row.get("created_at"):
            row["created_at"] = row["created_at"].strftime("%Y-%m-%d %H:%M:%S")
    return rows


def get_behavior_summary():
    """获取行为统计概览"""
    total = db.query("SELECT COUNT(*) as cnt FROM user_behavior")
    users = db.query("SELECT COUNT(DISTINCT user_id) as cnt FROM user_behavior")
    by_type = db.query(
        "SELECT action_type, COUNT(*) as cnt FROM user_behavior GROUP BY action_type"
    )
    return {
        "total_behaviors": total[0]["cnt"] if total else 0,
        "total_users": users[0]["cnt"] if users else 0,
        "by_type": {row["action_type"]: row["cnt"] for row in by_type},
    }
