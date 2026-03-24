"""转化数据录入 REST API"""
from flask import Blueprint, request, jsonify
import db
from services import heat_service

conversion_bp = Blueprint('conversion', __name__)


@conversion_bp.route('/api/conversions', methods=['POST'])
def upsert_conversion():
    """录入/更新商品转化数据"""
    data = request.get_json()
    if not data:
        return jsonify({"code": 1, "msg": "请求体为空"}), 400

    product_id = data.get("product_id")
    if not product_id:
        return jsonify({"code": 1, "msg": "product_id 不能为空"}), 400

    try:
        product_id = int(product_id)
    except (ValueError, TypeError):
        return jsonify({"code": 1, "msg": "product_id 必须是整数"}), 400

    click_count = int(data.get("click_count", 0))
    cart_count = int(data.get("cart_count", 0))
    order_count = int(data.get("order_count", 0))

    # 计算转化率
    click_rate = min(click_count / 100.0, 1.0) if click_count > 0 else 0.0
    cart_rate = cart_count / click_count if click_count > 0 else 0.0
    order_rate = order_count / click_count if click_count > 0 else 0.0

    db.upsert("conversion_data", {
        "product_id": product_id,
        "click_count": click_count,
        "cart_count": cart_count,
        "order_count": order_count,
        "click_rate": round(click_rate, 4),
        "cart_rate": round(cart_rate, 4),
        "order_rate": round(order_rate, 4),
    }, "product_id")

    # 更新热度中的点击率因子
    heat_service.update_click_rate_factor(product_id, click_rate)

    return jsonify({"code": 0, "msg": "转化数据更新成功"})


@conversion_bp.route('/api/conversions', methods=['GET'])
def get_all_conversions():
    """获取所有商品转化数据"""
    rows = db.query(
        "SELECT cd.product_id, pi.product_name, cd.click_count, cd.cart_count, "
        "cd.order_count, cd.click_rate, cd.cart_rate, cd.order_rate, cd.updated_at "
        "FROM conversion_data cd "
        "LEFT JOIN product_info pi ON cd.product_id = pi.product_id "
        "ORDER BY cd.product_id"
    )
    for row in rows:
        if row.get("updated_at"):
            row["updated_at"] = row["updated_at"].strftime("%Y-%m-%d %H:%M:%S")
    return jsonify({"code": 0, "data": rows})


@conversion_bp.route('/api/conversions/<int:product_id>', methods=['GET'])
def get_conversion(product_id):
    """获取单商品转化数据"""
    rows = db.query(
        "SELECT cd.product_id, pi.product_name, cd.click_count, cd.cart_count, "
        "cd.order_count, cd.click_rate, cd.cart_rate, cd.order_rate "
        "FROM conversion_data cd "
        "LEFT JOIN product_info pi ON cd.product_id = pi.product_id "
        "WHERE cd.product_id = %s",
        (product_id,)
    )
    if rows:
        return jsonify({"code": 0, "data": rows[0]})
    return jsonify({"code": 0, "data": None})
