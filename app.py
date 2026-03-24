"""应用入口 - Flask + SocketIO + 后台线程调度"""
import threading
from loguru import logger
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS

import config
import db
from api.product_api import product_bp
from api.behavior_api import behavior_bp
from api.conversion_api import conversion_bp
from api.report_api import report_bp
from api.dashboard_api import dashboard_bp
from events.socketio_events import register_events
from services import analysis_service, danmu_service, heat_service, report_service


def create_app():
    """创建 Flask 应用"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = config.SECRET_KEY

    # CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

    # 注册蓝图
    app.register_blueprint(product_bp)
    app.register_blueprint(behavior_bp)
    app.register_blueprint(conversion_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(dashboard_bp)

    # 注册 SocketIO 事件
    register_events(socketio)

    # 注入 SocketIO 到各服务
    analysis_service.set_socketio(socketio)
    danmu_service.set_socketio(socketio)
    heat_service.set_socketio(socketio)

    return app, socketio


def main():
    """主函数"""
    logger.add(config.LOG_PATH, rotation=config.LOG_ROTATION, encoding="utf-8", level="DEBUG")
    logger.info("===== 电商直播弹幕情绪感知商品推荐系统启动 =====")
    logger.info(f"设备：{config.DEVICE}")

    # 初始化数据库
    try:
        db.init_tables()
    except Exception as e:
        logger.error(f"数据库初始化失败：{e}")
        logger.warning("系统将继续运行，但数据库功能不可用")

    # 从数据库加载商品
    heat_service.load_products_from_db()
    logger.info(f"已加载 {len(heat_service.PRODUCTS)} 个商品")

    # 加载 BERT 模型
    analysis_service.load_model()

    # 创建应用
    app, socketio = create_app()

    # 启动分析线程（通过 analysis_service 管理生命周期）
    analysis_service.start_analysis_loop()
    logger.info("分析线程已启动")

    # 启动 Flask + SocketIO
    logger.success(f"系统启动成功！")
    logger.info(f"后端地址：http://localhost:{config.FLASK_PORT}")
    logger.info(f"前端开发服务器请运行：cd frontend && npm run dev")
    logger.info("手动弹幕输入请通过前端界面操作，自动爬取弹幕请在前端启动爬虫模式")

    try:
        socketio.run(
            app,
            host=config.FLASK_HOST,
            port=config.FLASK_PORT,
            debug=False,
            use_reloader=False,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        logger.info("检测到用户中断...")
    finally:
        danmu_service.stop()
        report_service.generate_report()
        logger.info("===== 系统正常退出 =====")


if __name__ == "__main__":
    main()
