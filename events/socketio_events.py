"""SocketIO 事件定义"""
from loguru import logger
from services import danmu_service, recommend_service


def register_events(socketio):
    """注册所有 SocketIO 事件"""

    @socketio.on('connect')
    def handle_connect():
        logger.info("前端客户端已连接")

    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info("前端客户端已断开")

    @socketio.on('danmu:manual_input')
    def handle_manual_input(data):
        """处理前端手动输入的弹幕"""
        text = data.get("text", "").strip() if data else ""
        if text:
            success = danmu_service.add_manual_danmu(text)
            if success:
                logger.info(f"手动弹幕已添加：{text}")
            else:
                logger.warning(f"手动弹幕为空或重复：{text}")

    @socketio.on('behavior:record')
    def handle_behavior_record(data):
        """处理前端快捷行为录入"""
        if not data:
            return
        user_id = data.get("user_id", "").strip()
        product_id = data.get("product_id")
        action_type = data.get("action_type", "").strip()

        if not user_id or not product_id or action_type not in ("click", "cart", "order"):
            return

        try:
            product_id = int(product_id)
        except (ValueError, TypeError):
            return

        recommend_service.record_behavior(user_id, product_id, action_type)

        # 推送更新后的推荐结果
        result = recommend_service.recommend_for_user(user_id)
        socketio.emit("recommend:update", result)

    @socketio.on('recommend:request')
    def handle_recommend_request(data):
        """处理推荐请求"""
        user_id = data.get("user_id", "").strip() if data else ""
        if user_id:
            result = recommend_service.recommend_for_user(user_id)
            socketio.emit("recommend:update", result)

    @socketio.on('danmu:clear')
    def handle_danmu_clear():
        """处理前端清空弹幕请求"""
        with danmu_service.DANMU_LOCK:
            danmu_service.DANMU_BUFFER.clear()
            danmu_service.DANMU_SET.clear()
        logger.info("前端请求清空弹幕缓冲区")
