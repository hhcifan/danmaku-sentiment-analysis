"""用户行为录入 REST API"""
from flask import Blueprint, request, jsonify
from services import recommend_service

behavior_bp = Blueprint('behavior', __name__)


@behavior_bp.route('/api/behaviors', methods=['POST'])
def record_behavior():
    """录入用户行为"""
    data = request.get_json()
    if not data:
        return jsonify({"code": 1, "msg": "请求体为空"}), 400

    user_id = data.get("user_id", "").strip()
    product_id = data.get("product_id")
    action_type = data.get("action_type", "").strip()

    if not user_id or not product_id or not action_type:
        return jsonify({"code": 1, "msg": "user_id、product_id、action_type 不能为空"}), 400

    if action_type not in ("click", "cart", "order"):
        return jsonify({"code": 1, "msg": "action_type 必须是 click/cart/order"}), 400

    try:
        product_id = int(product_id)
    except (ValueError, TypeError):
        return jsonify({"code": 1, "msg": "product_id 必须是整数"}), 400

    recommend_service.record_behavior(user_id, product_id, action_type)
    return jsonify({"code": 0, "msg": "行为记录成功"})


@behavior_bp.route('/api/behaviors', methods=['GET'])
def get_behaviors():
    """查询用户行为历史"""
    user_id = request.args.get("user_id", "").strip()
    if not user_id:
        return jsonify({"code": 1, "msg": "请提供 user_id"}), 400

    behaviors = recommend_service.get_user_behaviors(user_id)
    return jsonify({"code": 0, "data": behaviors})


@behavior_bp.route('/api/behaviors/summary', methods=['GET'])
def get_summary():
    """获取行为统计概览"""
    summary = recommend_service.get_behavior_summary()
    return jsonify({"code": 0, "data": summary})
