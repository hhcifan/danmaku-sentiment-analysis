"""复盘报告生成服务 - 含转化率关联分析"""
import re
from datetime import datetime
from collections import defaultdict
from loguru import logger
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use('Agg')
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

import db


def generate_report():
    """生成复盘报告（含转化率关联分析）"""
    logger.info("正在生成复盘报告...")

    stats = {
        "total_danmu": 0,
        "positive_count": 0,
        "negative_count": 0,
        "neutral_count": 0,
        "keyword_stats": defaultdict(int),
        "product_stats": defaultdict(lambda: {"mention_count": 0, "heat": 0.0, "positive": 0, "negative": 0}),
        "time_segments": defaultdict(lambda: {"pos": 0, "neg": 0, "neu": 0}),
    }

    # 从分析结果文件读取数据
    try:
        with open("抖音弹幕分析结果.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()

        current_batch_time = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            time_match = re.search(r"=== (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) 分析结果 ===", line)
            if time_match:
                current_batch_time = time_match.group(1)

            total_match = re.search(r"总弹幕：(\d+)", line)
            pos_match = re.search(r"正向：(\d+)", line)
            neg_match = re.search(r"负向：(\d+)", line)
            neu_match = re.search(r"中性：(\d+)", line)

            if total_match and pos_match and neg_match and neu_match:
                stats["total_danmu"] += int(total_match.group(1))
                stats["positive_count"] += int(pos_match.group(1))
                stats["negative_count"] += int(neg_match.group(1))
                stats["neutral_count"] += int(neu_match.group(1))

                if current_batch_time:
                    hour = current_batch_time.split()[1].split(":")[0] + "点"
                    stats["time_segments"][hour]["pos"] += int(pos_match.group(1))
                    stats["time_segments"][hour]["neg"] += int(neg_match.group(1))
                    stats["time_segments"][hour]["neu"] += int(neu_match.group(1))

            kw_match = re.search(r"关键词：([^|]+)", line)
            if kw_match:
                keywords = kw_match.group(1).strip().strip('[]').split(', ')
                for kw in keywords:
                    kw = kw.strip().strip("'\"")
                    if kw:
                        stats["keyword_stats"][kw] += 1

            product_match = re.search(
                r"第\d+名：(.+?) \| 热度：(\d+\.\d+) \| 总提及：(\d+) \| 正向提及：(\d+) \| 负向提及：(\d+)", line)
            if product_match:
                name = product_match.group(1)
                stats["product_stats"][name]["heat"] = float(product_match.group(2))
                stats["product_stats"][name]["mention_count"] = int(product_match.group(3))
                stats["product_stats"][name]["positive"] = int(product_match.group(4))
                stats["product_stats"][name]["negative"] = int(product_match.group(5))

    except FileNotFoundError:
        logger.warning("分析结果文件不存在")
    except Exception as e:
        logger.error(f"读取分析数据失败：{e}")

    # ===== 获取转化数据 =====
    conversion_data = db.query(
        "SELECT cd.product_id, pi.product_name, cd.click_count, cd.cart_count, "
        "cd.order_count, cd.click_rate, cd.cart_rate, cd.order_rate "
        "FROM conversion_data cd "
        "LEFT JOIN product_info pi ON cd.product_id = pi.product_id"
    )
    conversion_map = {row["product_name"]: row for row in conversion_data if row.get("product_name")}

    # ===== 构建报告内容 =====
    total = max(stats["total_danmu"], 1)
    pos_rate = stats["positive_count"] / total * 100
    neg_rate = stats["negative_count"] / total * 100
    neu_rate = stats["neutral_count"] / total * 100

    report = f"""# 电商直播弹幕分析复盘报告
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
报告编号：{datetime.now().strftime('%Y%m%d%H%M%S')}
{'=' * 60}

## 一、核心数据概览
- 累计分析弹幕总数：{stats['total_danmu']:,} 条
- 正向情绪：{stats['positive_count']:,} 条（{pos_rate:.1f}%）
- 负向情绪：{stats['negative_count']:,} 条（{neg_rate:.1f}%）
- 中性情绪：{stats['neutral_count']:,} 条（{neu_rate:.1f}%）
- 整体情绪健康度：{"优秀" if pos_rate > 60 else "良好" if pos_rate > 40 else "需优化"}

## 二、时间维度分析
"""
    for hour, seg in sorted(stats["time_segments"].items()):
        seg_total = seg["pos"] + seg["neg"] + seg["neu"]
        if seg_total == 0:
            continue
        seg_pos_rate = seg["pos"] / seg_total * 100
        report += f"- {hour}：总弹幕 {seg_total:,} 条 | 正向率 {seg_pos_rate:.1f}%\n"

    report += "\n## 三、关键词热度TOP8\n"
    top_keywords = sorted(stats["keyword_stats"].items(), key=lambda x: x[1], reverse=True)[:8]
    for i, (kw, count) in enumerate(top_keywords, 1):
        report += f"{i}. {kw}：提及 {count} 次\n"

    report += "\n## 四、商品热度分析\n"
    top_products = sorted(stats["product_stats"].items(), key=lambda x: x[1]["heat"], reverse=True)
    for i, (name, info) in enumerate(top_products, 1):
        if info["mention_count"] == 0:
            continue
        pos_r = info["positive"] / info["mention_count"] * 100 if info["mention_count"] > 0 else 0
        report += (
            f"{i}. {name}\n"
            f"   - 热度值：{info['heat']:.2f}\n"
            f"   - 总提及：{info['mention_count']:,} 次\n"
            f"   - 正向提及：{info['positive']} 次（{pos_r:.1f}%）\n"
            f"   - 负向提及：{info['negative']} 次\n"
        )

    # ===== 新增：转化率关联分析 =====
    report += "\n## 五、弹幕情绪与转化率关联分析\n"
    if conversion_map:
        report += "| 商品 | 正向提及率 | 点击数 | 加购数 | 下单数 | 下单转化率 | 关联评价 |\n"
        report += "|------|-----------|--------|--------|--------|-----------|----------|\n"

        for name, info in top_products:
            if info["mention_count"] == 0:
                continue
            conv = conversion_map.get(name, {})
            pos_r = info["positive"] / info["mention_count"] * 100 if info["mention_count"] > 0 else 0
            clicks = conv.get("click_count", 0) or 0
            carts = conv.get("cart_count", 0) or 0
            orders = conv.get("order_count", 0) or 0
            order_rate = conv.get("order_rate", 0) or 0

            if pos_r > 50 and order_rate > 0.05:
                evaluation = "情绪转化效率高"
            elif pos_r > 50 and order_rate <= 0.05:
                evaluation = "情绪好但转化低，检查价格或流程"
            elif pos_r <= 30 and order_rate > 0.05:
                evaluation = "转化尚可但口碑需改善"
            elif pos_r <= 30:
                evaluation = "需调整话术或商品策略"
            else:
                evaluation = "表现均衡"

            report += f"| {name} | {pos_r:.1f}% | {clicks} | {carts} | {orders} | {order_rate:.1%} | {evaluation} |\n"
    else:
        report += "暂无转化数据，请通过前端录入商品转化数据。\n"

    # ===== 运营优化建议 =====
    report += "\n## 六、运营优化建议\n"
    if neg_rate > 30:
        report += "- 负面情绪占比过高，建议：\n"
        report += "  1. 重点回应用户负面反馈（如价格、质量问题）\n"
        report += "  2. 增加优惠活动，提升用户满意度\n"
        report += "  3. 调整商品讲解话术，突出核心卖点\n"
    elif pos_rate > 60:
        report += "- 正向情绪占比优秀，建议：\n"
        report += "  1. 加大主推商品的讲解力度\n"
        report += "  2. 适时上架限时优惠，促进转化\n"
        report += "  3. 复制当前讲解节奏，保持用户积极性\n"
    else:
        report += "- 情绪分布均衡，建议：\n"
        report += "  1. 重点推广热度最高的商品\n"
        report += "  2. 针对高频关键词进行专项讲解\n"
        report += "  3. 增加互动环节，提升用户参与度\n"

    # 保存报告文件
    try:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        with open(f"直播复盘报告_{timestamp}.txt", "w", encoding="utf-8") as f:
            f.write(report)
        with open("直播复盘报告.txt", "w", encoding="utf-8") as f:
            f.write(report)
        logger.success(f"复盘报告已生成：直播复盘报告_{timestamp}.txt")
    except Exception as e:
        logger.error(f"写入报告文件失败：{e}")

    # 保存到数据库
    try:
        db.insert("review_report", {
            "total_danmu": stats["total_danmu"],
            "positive_count": stats["positive_count"],
            "negative_count": stats["negative_count"],
            "neutral_count": stats["neutral_count"],
            "hot_keywords": ",".join([f"{k}:{v}" for k, v in top_keywords[:5]]),
            "product_heat": ",".join([f"{n}:{info['heat']:.2f}" for n, info in top_products[:5]]),
            "report_content": report,
        })
        logger.debug("复盘报告已写入MySQL")
    except Exception as e:
        logger.error(f"复盘报告写入MySQL失败：{e}")

    # 生成图表
    _plot_sentiment(stats)

    return report


def _plot_sentiment(stats):
    """生成情感分布图表"""
    sentiment_stats = {
        "正向": stats["positive_count"],
        "负向": stats["negative_count"],
        "中性": stats["neutral_count"],
    }

    if sum(sentiment_stats.values()) == 0:
        return

    plt.figure(figsize=(8, 6))
    plt.pie(
        sentiment_stats.values(),
        labels=sentiment_stats.keys(),
        colors=['#66b3ff', '#ff9999', '#99ff99'],
        autopct='%1.1f%%',
        startangle=90,
        explode=(0.05, 0, 0),
        shadow=True
    )
    plt.title('直播弹幕情感分布')
    plt.axis('equal')
    plt.savefig('sentiment_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    logger.success("情感分布图已生成")


def get_latest_report():
    """获取最新复盘报告"""
    rows = db.query(
        "SELECT report_content, create_time FROM review_report ORDER BY create_time DESC LIMIT 1"
    )
    if rows:
        row = rows[0]
        if row.get("create_time"):
            row["create_time"] = row["create_time"].strftime("%Y-%m-%d %H:%M:%S")
        return row
    return None


def get_reports(limit=10, offset=0):
    """获取报告列表"""
    rows = db.query(
        "SELECT id, total_danmu, positive_count, negative_count, neutral_count, "
        "create_time FROM review_report ORDER BY create_time DESC LIMIT %s OFFSET %s",
        (limit, offset)
    )
    for row in rows:
        if row.get("create_time"):
            row["create_time"] = row["create_time"].strftime("%Y-%m-%d %H:%M:%S")
    return rows


def get_report_by_id(report_id):
    """按 ID 获取单条报告"""
    rows = db.query(
        "SELECT id, report_content, create_time FROM review_report WHERE id = %s",
        (report_id,)
    )
    if rows:
        row = rows[0]
        if row.get("create_time"):
            row["create_time"] = row["create_time"].strftime("%Y-%m-%d %H:%M:%S")
        return row
    return None


def delete_report(report_id):
    """删除单条报告"""
    try:
        db.execute("DELETE FROM review_report WHERE id = %s", (report_id,))
        return True
    except Exception as e:
        logger.error(f"删除报告失败：{e}")
        return False


def batch_delete_reports(ids):
    """批量删除报告"""
    if not ids:
        return 0
    try:
        placeholders = ','.join(['%s'] * len(ids))
        db.execute(f"DELETE FROM review_report WHERE id IN ({placeholders})", tuple(ids))
        return len(ids)
    except Exception as e:
        logger.error(f"批量删除报告失败：{e}")
        return 0


def clear_all_reports():
    """清空所有报告"""
    try:
        db.execute("DELETE FROM review_report")
        return True
    except Exception as e:
        logger.error(f"清空报告失败：{e}")
        return False
