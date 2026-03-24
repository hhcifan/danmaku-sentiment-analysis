"""仪表盘数据 + 系统控制 REST API"""
import threading
from flask import Blueprint, request, jsonify
from services import analysis_service, danmu_service, recommend_service
from services.sensitive_service import get_sensitive_logs, clear_sensitive_logs
import config
import db

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/api/dashboard/snapshot', methods=['GET'])
def get_snapshot():
    """获取当前系统全量快照"""
    snapshot = analysis_service.get_snapshot()
    return jsonify({"code": 0, "data": snapshot})


@dashboard_bp.route('/api/dashboard/sensitive-log', methods=['GET'])
def get_sensitive_log():
    """获取敏感弹幕屏蔽日志"""
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    logs = get_sensitive_logs(limit, offset)
    return jsonify({"code": 0, "data": logs})


@dashboard_bp.route('/api/dashboard/sensitive-log', methods=['DELETE'])
def clear_sensitive_log():
    """清空敏感弹幕屏蔽日志"""
    success = clear_sensitive_logs()
    if success:
        return jsonify({"code": 0, "msg": "敏感日志已清空"})
    return jsonify({"code": 1, "msg": "清空失败"}), 500


@dashboard_bp.route('/api/dashboard/recommend', methods=['GET'])
def get_recommend():
    """获取用户推荐结果"""
    user_id = request.args.get("user_id", "").strip()
    if not user_id:
        return jsonify({"code": 1, "msg": "请提供 user_id"}), 400
    result = recommend_service.recommend_for_user(user_id)
    return jsonify({"code": 0, "data": result})


@dashboard_bp.route('/api/system/start', methods=['POST'])
def start_system():
    """启动弹幕采集"""
    data = request.get_json() or {}
    mode = data.get("mode", "manual")

    danmu_service.reset()

    # 确保分析线程在运行（停止后重启时需要重新创建）
    analysis_service.start_analysis_loop()

    if mode == "crawl":
        url = data.get("url", "").strip() or config.LIVE_URL
        if not url.startswith(("http://", "https://")):
            return jsonify({"code": 1, "msg": "无效的直播间地址"}), 400
        t = threading.Thread(target=danmu_service.crawl_danmu, args=(url,), daemon=True)
        t.start()
    # manual模式通过SocketIO的danmu:manual_input事件输入

    return jsonify({"code": 0, "msg": f"系统已启动（模式：{mode}）"})


@dashboard_bp.route('/api/system/stop', methods=['POST'])
def stop_system():
    """停止弹幕采集"""
    danmu_service.stop()
    return jsonify({"code": 0, "msg": "系统已停止"})


@dashboard_bp.route('/api/system/status', methods=['GET'])
def get_status():
    """获取系统运行状态"""
    return jsonify({
        "code": 0,
        "data": {
            "running": danmu_service.is_running(),
            "danmu_count": sum(analysis_service.TOTAL_STATS.values()),
            "buffer_size": len(danmu_service.DANMU_BUFFER),
        }
    })


@dashboard_bp.route('/api/dashboard/recent-danmu', methods=['GET'])
def get_recent_danmu():
    """获取已分析弹幕（支持游标分页，用于历史弹幕加载）"""
    limit = request.args.get("limit", 20, type=int)
    before_id = request.args.get("before_id", 0, type=int)

    # 多查一条用于判断是否还有更多
    fetch_limit = limit + 1

    if before_id > 0:
        rows = db.query(
            "SELECT id, danmu_text, sentiment, keywords, create_time "
            "FROM cleaned_danmu WHERE id < %s ORDER BY id DESC LIMIT %s",
            (before_id, fetch_limit)
        )
    else:
        rows = db.query(
            "SELECT id, danmu_text, sentiment, keywords, create_time "
            "FROM cleaned_danmu ORDER BY id DESC LIMIT %s",
            (fetch_limit,)
        )

    has_more = len(rows) > limit
    rows = rows[:limit]  # 截取实际需要的条数

    items = []
    for row in reversed(rows):  # 按时间正序返回
        kw_str = row.get("keywords", "") or ""
        items.append({
            "id": row["id"],
            "text": row["danmu_text"],
            "sentiment": row["sentiment"],
            "keywords": [k for k in kw_str.split(",") if k],
            "time": row["create_time"].strftime("%H:%M:%S") if row.get("create_time") else "",
        })

    oldest_id = rows[-1]["id"] if rows else 0  # rows 是 DESC 排序，最后一条是最老的

    return jsonify({
        "code": 0,
        "data": {
            "items": items,
            "has_more": has_more,
            "oldest_id": oldest_id,
        }
    })
