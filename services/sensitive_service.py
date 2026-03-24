"""敏感内容过滤服务 - 增强版"""
import re
import time
from loguru import logger
import db


# ===================== 分级敏感词库 =====================
# Level-1: 严格屏蔽（脏话、人身攻击）
LEVEL1_WORDS = [
    "垃圾", "滚", "操", "妈的", "去死", "傻逼", "智障", "艹", "肏", "尼玛",
    "废物", "狗东西", "贱人", "白痴", "脑残", "弱智", "神经病", "变态",
    "滚蛋", "混蛋", "王八蛋", "畜生", "禽兽", "人渣", "败类",
    "他妈", "卧槽", "草泥马", "nmsl", "sb", "cnm", "wtf",
    "死全家", "祖宗十八代", "下地狱", "不得好死"
]

# Level-2: 温和提醒（不当言论但非脏话）
LEVEL2_WORDS = [
    "骗子", "骗人", "黑心", "坑人", "割韭菜", "忽悠",
    "假的", "造假", "虚假宣传", "三无产品", "山寨",
    "举报", "投诉", "打假", "退款", "消协"
]


def filter_sensitive(text):
    """
    敏感词过滤和特殊字符清理
    返回: (filtered_text, matched_words) 元组
    - filtered_text: 过滤后的文本
    - matched_words: 命中的敏感词列表（为空表示未命中）
    """
    # 清理特殊字符
    cleaned = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', text)
    cleaned = re.sub(r'\s+', '', cleaned)

    if not cleaned:
        return cleaned, []

    matched = []
    result = cleaned

    # 按长度降序排列，确保较长的敏感词优先匹配
    all_words = sorted(LEVEL1_WORDS + LEVEL2_WORDS, key=len, reverse=True)

    for word in all_words:
        if word.lower() in result.lower():
            matched.append(word)
            result = re.sub(re.escape(word), "*" * len(word), result, flags=re.IGNORECASE)

    return result.strip(), matched


def log_sensitive_block(original_text, filtered_text, matched_words, socketio=None):
    """记录敏感弹幕屏蔽日志到数据库，并通过SocketIO推送"""
    if not matched_words:
        return

    try:
        db.insert("sensitive_log", {
            "original_text": original_text,
            "filtered_text": filtered_text,
            "matched_words": ",".join(matched_words),
        })
    except Exception as e:
        logger.error(f"写入敏感日志失败：{e}")

    # 通过SocketIO推送
    if socketio:
        try:
            socketio.emit("sensitive:blocked", {
                "original_text": original_text,
                "filtered_text": filtered_text,
                "matched_words": matched_words,
                "time": time.strftime("%H:%M:%S")
            })
        except Exception as e:
            logger.error(f"推送敏感日志失败：{e}")


def get_sensitive_logs(limit=50, offset=0):
    """获取敏感弹幕屏蔽日志"""
    rows = db.query(
        "SELECT original_text, filtered_text, matched_words, created_at "
        "FROM sensitive_log ORDER BY created_at DESC LIMIT %s OFFSET %s",
        (limit, offset)
    )
    for row in rows:
        if row.get("created_at"):
            row["created_at"] = row["created_at"].strftime("%Y-%m-%d %H:%M:%S")
        if row.get("matched_words"):
            row["matched_words"] = row["matched_words"].split(",")
    return rows


def clear_sensitive_logs():
    """清空敏感弹幕屏蔽日志"""
    try:
        db.execute("DELETE FROM sensitive_log")
        return True
    except Exception as e:
        logger.error(f"清空敏感日志失败：{e}")
        return False
