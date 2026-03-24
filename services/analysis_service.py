"""弹幕分析服务 - 批量情感预测 + 分析主循环 + SocketIO推送"""
import os
import time
from collections import defaultdict
from loguru import logger
import torch
from transformers import AutoTokenizer

import config
import db
import train_sentiment_model
import dataset
from services import danmu_service, heat_service, keyword_service, suggestion_service


# 全局模型和 tokenizer
_model = None
_tokenizer = None
_socketio = None

# 分析线程引用
_analyze_thread = None

# 累计统计
TOTAL_STATS = {"正向": 0, "负向": 0, "中性": 0}


def set_socketio(sio):
    global _socketio
    _socketio = sio


def load_model():
    """加载BERT情感分类模型"""
    global _model, _tokenizer
    logger.info("加载BERT模型...")
    _tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)
    _model = train_sentiment_model.BertSentimentModel(num_classes=3).to(config.DEVICE)

    if os.path.exists(config.MODEL_PATH):
        try:
            _model.load_state_dict(
                torch.load(config.MODEL_PATH, map_location=config.DEVICE)
            )
            _model.eval()
            logger.success("已加载本地BERT模型")
        except Exception:
            logger.warning("本地模型加载失败，重新训练")
            _model = train_sentiment_model.train_sentiment_model(
                _model, _tokenizer, train_sentiment_model.augment_dataset(dataset)
            )
    else:
        logger.info("未找到本地模型，开始训练...")
        _model = train_sentiment_model.train_sentiment_model(
            _model, _tokenizer, train_sentiment_model.augment_dataset(dataset)
        )

    logger.success(f"模型加载完成，设备：{config.DEVICE}")


def batch_predict(danmu_list):
    """批量预测弹幕情感"""
    if not danmu_list or not _model or not _tokenizer:
        return []

    danmu_list = [d for d in danmu_list if d and len(d) > 0]
    if not danmu_list:
        return []

    inputs = _tokenizer(
        danmu_list, max_length=config.MAX_LEN,
        padding=True, truncation=True, return_tensors="pt"
    ).to(config.DEVICE)

    with torch.no_grad():
        logits = _model(**inputs)
        preds = torch.argmax(logits, dim=1).cpu().numpy()

    # 批量关键词提取（使用新的三层混合方案）
    all_keywords = keyword_service.extract_keywords_batch(danmu_list)

    results = []
    for text, p, kw_list in zip(danmu_list, preds, all_keywords):
        sentiment = config.ID2LABEL[p]
        kw_words = keyword_service.get_keyword_strings(kw_list)

        result_item = {
            "text": text,
            "sentiment": sentiment,
            "keywords": kw_words,
            "keywords_detail": kw_list,
            "time": time.strftime("%H:%M:%S")
        }
        results.append(result_item)

        # 写入数据库
        keywords_str = ",".join(kw_words)
        db.upsert("cleaned_danmu", {
            "danmu_text": text,
            "sentiment": sentiment,
            "keywords": keywords_str,
        }, "danmu_text")

        # 统计商品提及
        heat_service.count_product_mention(text, sentiment)

        # 记录商品关键词反馈（用于建议生成）
        suggestion_service.process_danmu_keywords(text, kw_list, sentiment)

    return results


def analyze_danmu_loop():
    """弹幕分析主循环"""
    global TOTAL_STATS
    logger.info(f"情感分析线程已启动（每{config.ANALYZE_INTERVAL}秒批量处理）")

    while not danmu_service.EXIT_FLAG.is_set():
        time.sleep(config.ANALYZE_INTERVAL)

        batch = danmu_service.get_buffer_batch(config.BATCH_SIZE)
        if not batch:
            continue

        results = batch_predict(batch)
        if not results:
            continue

        # 统计本批次
        batch_stat = defaultdict(int)
        for res in results:
            batch_stat[res["sentiment"]] += 1
            # 保存所有批次
            TOTAL_STATS[res["sentiment"]] = TOTAL_STATS.get(res["sentiment"], 0) + 1

        # 计算热度
        heat_ranking = heat_service.calculate_heat()
        total = sum(batch_stat.values())

        # 生成建议
        suggestions = suggestion_service.generate_suggestions()

        # 日志输出
        logger.info(f"\n{'=' * 60}")
        logger.info(f"【批量分析】共{total}条 | 正向：{batch_stat['正向']} | 负向：{batch_stat['负向']} | 中性：{batch_stat['中性']}")
        for i, p in enumerate(heat_ranking[:5]):
            logger.info(f"  热度第{i + 1}：{p['name']} | 热度：{p['heat']:.2f} | 提及：{p['mention_count']}")

        # 写入分析结果文件
        with open("抖音弹幕分析结果.txt", "a", encoding="utf-8") as f:
            f.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} 分析结果 ===\n")
            f.write(f"总弹幕：{total} | 正向：{batch_stat['正向']} | 负向：{batch_stat['负向']} | 中性：{batch_stat['中性']}\n")
            for i, p in enumerate(heat_ranking):
                f.write(f"  第{i + 1}名：{p['name']} | 热度：{p['heat']:.2f} | 总提及：{p['mention_count']} | 正向提及：{p['positive_mention']} | 负向提及：{p['negative_mention']}\n")
            for res in results:
                f.write(f"  [{res['time']}] [{res['sentiment']}] {res['text']} | 关键词：{res['keywords']}\n")

        # SocketIO 推送
        if _socketio:
            _emit_updates(results, batch_stat, heat_ranking, suggestions)

    logger.info("分析线程已退出")


def start_analysis_loop():
    """启动（或重启）分析线程"""
    global _analyze_thread
    import threading
    if _analyze_thread and _analyze_thread.is_alive():
        logger.info("分析线程已在运行，无需重启")
        return
    _analyze_thread = threading.Thread(target=analyze_danmu_loop, daemon=True)
    _analyze_thread.start()
    logger.info("分析线程已（重新）启动")


def is_analysis_running():
    """检查分析线程是否在运行"""
    return _analyze_thread is not None and _analyze_thread.is_alive()


def _emit_updates(results, batch_stat, heat_ranking, suggestions):
    """通过 SocketIO 推送实时数据"""
    try:
        # 推送新弹幕
        _socketio.emit("danmu:new", [
            {"text": r["text"], "sentiment": r["sentiment"],
             "keywords": r["keywords"], "time": r["time"]}
            for r in results
        ])

        # 推送情绪统计
        total = sum(TOTAL_STATS.values()) or 1
        _socketio.emit("emotion:update", {
            "positive": TOTAL_STATS.get("正向", 0),
            "negative": TOTAL_STATS.get("负向", 0),
            "neutral": TOTAL_STATS.get("中性", 0),
            "total": sum(TOTAL_STATS.values()),
            "positive_rate": round(TOTAL_STATS.get("正向", 0) / total * 100, 1),
            "negative_rate": round(TOTAL_STATS.get("负向", 0) / total * 100, 1),
            "neutral_rate": round(TOTAL_STATS.get("中性", 0) / total * 100, 1),
        })

        # 推送热度排名
        _socketio.emit("heat:update", [
            {"id": p["id"], "name": p["name"], "heat": p["heat"],
             "mention_count": p["mention_count"],
             "positive_mention": p["positive_mention"],
             "negative_mention": p["negative_mention"],
             "pinned": p.get("pinned", 0)}
            for p in heat_ranking
        ])

        # 推送建议
        _socketio.emit("suggestion:update", suggestions)

        # 推送系统状态
        _socketio.emit("system:status", {
            "running": danmu_service.is_running(),
            "danmu_count": sum(TOTAL_STATS.values()),
            "buffer_size": len(danmu_service.DANMU_BUFFER),
            "drop_count": danmu_service.get_drop_count(),
        })
    except Exception as e:
        logger.error(f"SocketIO推送失败：{e}")


def get_snapshot():
    """获取当前系统快照数据"""
    heat_ranking = heat_service.get_heat_ranking()
    suggestions = suggestion_service.generate_suggestions()
    total = sum(TOTAL_STATS.values()) or 1

    return {
        "emotion": {
            "positive": TOTAL_STATS.get("正向", 0),
            "negative": TOTAL_STATS.get("负向", 0),
            "neutral": TOTAL_STATS.get("中性", 0),
            "total": sum(TOTAL_STATS.values()),
            "positive_rate": round(TOTAL_STATS.get("正向", 0) / total * 100, 1),
            "negative_rate": round(TOTAL_STATS.get("负向", 0) / total * 100, 1),
            "neutral_rate": round(TOTAL_STATS.get("中性", 0) / total * 100, 1),
        },
        "heat_ranking": [
            {"id": p["id"], "name": p["name"], "heat": p["heat"],
             "mention_count": p["mention_count"],
             "positive_mention": p["positive_mention"],
             "negative_mention": p["negative_mention"],
             "pinned": p.get("pinned", 0)}
            for p in heat_ranking
        ],
        "suggestions": suggestions,
        "system": {
            "running": danmu_service.is_running(),
            "danmu_count": sum(TOTAL_STATS.values()),
        }
    }
