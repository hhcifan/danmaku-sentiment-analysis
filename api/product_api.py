"""商品管理 REST API"""
from flask import Blueprint, request, jsonify
from services import heat_service

product_bp = Blueprint('product', __name__)


@product_bp.route('/api/products', methods=['GET'])
def get_products():
    """获取所有商品列表"""
    products = heat_service.get_products()
    return jsonify({"code": 0, "data": products})


@product_bp.route('/api/products', methods=['POST'])
def add_product():
    """添加商品"""
    data = request.get_json()
    if not data:
        return jsonify({"code": 1, "msg": "请求体为空"}), 400

    product_id = data.get("product_id")
    product_name = data.get("product_name", "").strip()

    if not product_id or not product_name:
        return jsonify({"code": 1, "msg": "商品ID和名称不能为空"}), 400

    try:
        product_id = int(product_id)
    except (ValueError, TypeError):
        return jsonify({"code": 1, "msg": "商品ID必须是整数"}), 400

    success = heat_service.add_product(product_id, product_name)
    if success:
        return jsonify({"code": 0, "msg": f"商品 {product_name} 添加成功"})
    else:
        return jsonify({"code": 1, "msg": f"商品ID {product_id} 已存在"}), 400


@product_bp.route('/api/products/<int:product_id>/pin', methods=['PUT'])
def pin_product(product_id):
    """置顶/取消置顶商品"""
    data = request.get_json()
    pinned = data.get("pinned", False) if data else False
    ranking = heat_service.pin_product(product_id, pinned)
    # 返回最新排名数据，前端无需再次请求
    heat_data = [
        {"id": p["id"], "name": p["name"], "heat": p["heat"],
         "mention_count": p["mention_count"],
         "positive_mention": p["positive_mention"],
         "negative_mention": p["negative_mention"],
         "pinned": p.get("pinned", 0)}
        for p in ranking
    ]
    return jsonify({"code": 0, "msg": "操作成功", "data": heat_data})


@product_bp.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """删除商品"""
    heat_service.remove_product(product_id)
    return jsonify({"code": 0, "msg": "删除成功"})
