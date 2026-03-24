"""全局配置模块"""
import warnings
import torch
import matplotlib

# ===================== 基础配置 =====================
warnings.filterwarnings("ignore")
matplotlib.use('Agg')

# 设备
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 浏览器路径
EDGE_PATH = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'

# 直播间地址
LIVE_URL ='https://live.douyin.com/646454278948'
# LIVE_URL = 'https://live.douyin.com/56299453014'

# BERT模型路径
MODEL_NAME = r"D:\PycharmProjects\ProductRecommendationSystem\models\models--hfl--chinese-roberta-wwm-ext\snapshots\chinese-roberta-wwm-ext"
MODEL_PATH = "bert_sentiment_model.pth"
MAX_LEN = 64
BATCH_SIZE = 64

# ===================== 线程配置 =====================
CONSUMER_THREAD_NUM = 8
ANALYZE_INTERVAL = 1.5
DANMU_BUFFER_MAX = 5000
DANMU_SET_MAX = 10000

# ===================== 自适应轮询配置 =====================
PRODUCER_POLL_MIN = 0.02        # 高压力时轮询间隔 20ms
PRODUCER_POLL_MAX = 0.05        # 正常轮询间隔 50ms
QUEUE_PRESSURE_THRESHOLD = 200  # 队列堆积压力阈值

# ===================== MySQL配置 =====================
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "050907",
    "database": "zhibo",
    "charset": "utf8mb4",
}

# 连接池配置
POOL_MIN_CACHED = 2
POOL_MAX_CACHED = 5
POOL_MAX_CONNECTIONS = 10

# ===================== Flask配置 =====================
SECRET_KEY = 'danmu_analysis_secret'
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 3000

# ===================== 标签映射 =====================
ID2LABEL = {0: "负向", 1: "正向", 2: "中性"}

# ===================== 日志配置 =====================
LOG_PATH = "runtime.log"
LOG_ROTATION = "500MB"
LEAK_LOG_PATH = "danmu_leak.log"

# ===================== 弹幕过滤关键词 =====================
FILTER_KEYWORDS = [
    "送出了", "加入了直播间", "关注了主播", "点赞了", "分享了",
    "来了", "关注了", "送给主播", "送了小心心", "欢迎来到",
    "直播间", "粉丝团", "加入粉丝团", "说", "进入直播间",
]
