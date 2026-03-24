"""复盘报告 REST API"""
from flask import Blueprint, request, jsonify
from services import report_service

report_bp = Blueprint('report', __name__)


@report_bp.route('/api/reports/generate', methods=['POST'])
def generate_report():
    """生成复盘报告"""
    report_content = report_service.generate_report()
    return jsonify({"code": 0, "msg": "报告生成成功", "data": {"content": report_content}})


@report_bp.route('/api/reports/latest', methods=['GET'])
def get_latest():
    """获取最新报告"""
    report = report_service.get_latest_report()
    return jsonify({"code": 0, "data": report})


@report_bp.route('/api/reports/batch-delete', methods=['POST'])
def batch_delete():
    """批量删除报告"""
    data = request.get_json() or {}
    ids = data.get("ids", [])
    if not ids or not isinstance(ids, list):
        return jsonify({"code": 1, "msg": "请提供要删除的报告ID列表"}), 400
    count = report_service.batch_delete_reports(ids)
    return jsonify({"code": 0, "msg": f"已删除 {count} 条报告"})


@report_bp.route('/api/reports/<int:report_id>', methods=['GET'])
def get_report(report_id):
    """获取单条报告"""
    report = report_service.get_report_by_id(report_id)
    if report:
        return jsonify({"code": 0, "data": report})
    return jsonify({"code": 1, "msg": "报告不存在"}), 404


@report_bp.route('/api/reports/<int:report_id>', methods=['DELETE'])
def delete_report(report_id):
    """删除单条报告"""
    success = report_service.delete_report(report_id)
    if success:
        return jsonify({"code": 0, "msg": "报告已删除"})
    return jsonify({"code": 1, "msg": "删除失败"}), 500


@report_bp.route('/api/reports', methods=['GET'])
def get_reports():
    """获取报告列表"""
    reports = report_service.get_reports()
    return jsonify({"code": 0, "data": reports})


@report_bp.route('/api/reports', methods=['DELETE'])
def clear_reports():
    """清空所有报告"""
    success = report_service.clear_all_reports()
    if success:
        return jsonify({"code": 0, "msg": "所有报告已清空"})
    return jsonify({"code": 1, "msg": "清空失败"}), 500
