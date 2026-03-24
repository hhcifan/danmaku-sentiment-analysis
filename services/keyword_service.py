"""关键词提取服务 - jieba词性标注 + 情绪词典 + TF-IDF 三层混合"""
import jieba
import jieba.posseg as pseg
from sklearn.feature_extraction.text import TfidfVectorizer
from loguru import logger


# ===================== 电商直播领域情绪词典 =====================
POSITIVE_WORDS = {
    "喜欢", "好看", "漂亮", "划算", "便宜", "好用", "质量好", "性价比高",
    "真香", "爱了", "超爱", "好美", "精致", "高级", "实惠", "值得",
    "推荐", "回购", "种草", "心动", "必买", "闭眼入", "百搭",
    "舒服", "柔软", "显白", "显瘦", "大气", "时尚", "好穿",
    "太好了", "绝了",
    "好吃", "好喝", "正品", "靠谱", "良心", "物超所值",
    "买买买", "上链接", "要了", "拍了", "下单了", "已买", "已拍",
    "适合", "合适", "刚好", "满意", "完美", "惊艳", "好评"
}

NEGATIVE_WORDS = {
    "太贵", "贵了", "好贵", "死贵", "价格高", "贵死了", "买不起",
    "难看", "丑", "不好看", "差", "很差", "太差", "差评",
    "坑", "不值", "不划算", "不实惠", "虚高",
    "退货", "退款", "不想要", "后悔",
    "假货", "假的", "质量差", "做工差", "粗糙", "掉色", "起球",
    "不好用", "不好穿", "不舒服", "不合适", "偏小", "偏大",
    "色差", "不一样", "货不对版", "图片骗人",
    "发货慢", "物流慢", "等不了",
    "不推荐", "不建议", "别买", "避雷", "踩雷", "智商税"
}

ATTRIBUTE_WORDS = {
    "颜色", "尺寸", "材质", "包装", "价格", "质量", "款式",
    "快递", "物流", "售后", "客服", "发货", "尺码", "大小",
    "重量", "容量", "功能", "效果", "成分", "保质期", "品牌"
}

# 停用词集合（覆盖标点、代词、副词、连词、高频无义词、网络语气词、直播噪音词）
STOPWORDS = {
    # 标点符号
    '，', '。', '！', '？', '；', '：', '、', '（', '）', '【', '】', '《', '》', '"', '"',
    ',', '.', '!', '?', ';', ':', '(', ')', '[', ']', '<', '>', '~', '…', '—',
    # 代词
    '的', '了', '是', '我', '你', '他', '她', '它', '们', '在', '有', '就', '不',
    '我们', '你们', '他们', '自己', '人家', '别人', '这些', '那些',
    # 指示词 / 疑问词
    '这', '那', '这个', '那个', '这样', '那样', '这里', '那里', '这种', '那种',
    '什么', '怎么', '怎样', '哪个', '哪里', '哪些', '为什么', '谁', '多少',
    # 副词 / 连词 / 介词
    '也', '都', '还', '把', '被', '为', '与', '和', '对', '对于', '大家',
    '就是', '已经', '还是', '比较', '一直', '一定', '非常', '特别', '真的', '确实',
    '应该', '可能', '可以', '然后', '所以', '因为', '虽然', '但是', '不过', '而且',
    '如果', '或者', '以及', '关于', '通过', '按照', '根据', '除了',
    '很', '太', '最', '更', '越', '又', '再', '才', '只', '刚',
    # 量词 / 数量短语
    '一个', '一下', '一点', '一些', '一样', '一起', '有点', '有些',
    # 高频无义动词 / 助词
    '没有', '没', '知道', '看看', '来了', '去了', '说了', '想要', '觉得', '认为',
    '看到', '听说', '开始', '继续', '变成', '成为', '进行', '需要', '使用',
    '做', '弄', '搞', '整', '拿', '给', '让', '叫', '到', '去', '来', '上', '下',
    '好像', '感觉', '大概', '算了', '不会', '会', '能', '要',
    # 网络语气词 / 表情词
    '啊', '呢', '吧', '哦', '嗯', '哈', '呀', '吗', '嘛', '哇', '噢', '嘿',
    '哈哈', '哈哈哈', '嘿嘿', '呵呵', '嗯嗯', '哦哦', '好的', '行',
    'ok', 'OK', '666', '6', 'yyds', '1', '11', '111',
    # 直播场景噪音词
    '主播', '老师', '家人们', '宝宝们', '宝宝', '姐妹', '姐妹们', '兄弟', '兄弟们',
    '朋友们', '朋友', '大哥', '老板', '亲', '亲们', '宝子', '宝子们',
    '谢谢', '感谢', '欢迎', '关注', '点赞', '双击', '分享', '转发',
    '直播间', '直播', '在线', '上线', '下播', '刚来', '来了',
    '求求', '拜托', '请问', '想问', '问一下',
    # 其他高频无信息词
    '东西', '时候', '地方', '事情', '问题', '样子', '意思',
    '不错', '可以', '棒', '赞', '厉害', '牛', '香', '慢',
    '真的吗', '是吗', '对吧', '是不是', '有没有',
}

# 有效词性集合：名词、动名词、形容词、副词（不含纯动词 v）
VALID_POS = {'n', 'a', 'ad', 'an', 'vn', 'ns', 'nr', 'nt', 'nz', 'ag', 'ng'}


def extract_keywords_single(text, top_k=3):
    """
    对单条弹幕提取关键词（三层混合方案）
    返回: [{"word": "太贵", "sentiment": "负向"}, ...]
    """
    if not text or not text.strip():
        return []

    keywords = []
    seen_words = set()

    # ===== 第一层：情绪词典匹配（优先级最高）=====
    # 滑动窗口匹配 2-4 字短语
    for window_size in range(4, 1, -1):
        for i in range(len(text) - window_size + 1):
            phrase = text[i:i + window_size]
            if phrase in STOPWORDS:
                continue
            if phrase in POSITIVE_WORDS and phrase not in seen_words:
                keywords.append({"word": phrase, "sentiment": "正向"})
                seen_words.add(phrase)
            elif phrase in NEGATIVE_WORDS and phrase not in seen_words:
                keywords.append({"word": phrase, "sentiment": "负向"})
                seen_words.add(phrase)
            elif phrase in ATTRIBUTE_WORDS and phrase not in seen_words:
                keywords.append({"word": phrase, "sentiment": "中性"})
                seen_words.add(phrase)

    # 单字/双字词典匹配
    for word_set, sentiment in [(POSITIVE_WORDS, "正向"), (NEGATIVE_WORDS, "负向")]:
        for w in word_set:
            if len(w) <= 2 and w in text and w not in seen_words and w not in STOPWORDS:
                keywords.append({"word": w, "sentiment": sentiment})
                seen_words.add(w)

    # ===== 第二层：jieba 词性标注提取 =====
    words_with_pos = pseg.lcut(text)
    for word, flag in words_with_pos:
        if word in seen_words or word in STOPWORDS or len(word) < 2:
            continue
        if flag in VALID_POS or flag.startswith('a'):
            sentiment = "中性"
            if word in POSITIVE_WORDS:
                sentiment = "正向"
            elif word in NEGATIVE_WORDS:
                sentiment = "负向"
            keywords.append({"word": word, "sentiment": sentiment})
            seen_words.add(word)

    # ===== 第三层：TF-IDF 兜底 =====
    if len(keywords) < 1:
        tfidf_keywords = _extract_tfidf_single(text)
        for w in tfidf_keywords:
            if w not in seen_words and w not in STOPWORDS:
                sentiment = "中性"
                if w in POSITIVE_WORDS:
                    sentiment = "正向"
                elif w in NEGATIVE_WORDS:
                    sentiment = "负向"
                keywords.append({"word": w, "sentiment": sentiment})
                seen_words.add(w)

    # 最终防御性过滤：确保无停用词泄漏
    keywords = [kw for kw in keywords if kw["word"] not in STOPWORDS and len(kw["word"]) >= 2]
    return keywords[:top_k]


def extract_keywords_batch(texts, top_k=3):
    """批量提取关键词"""
    return [extract_keywords_single(text, top_k) for text in texts]


def _extract_tfidf_single(text, top_k=2):
    """TF-IDF提取（兜底方案）"""
    words = jieba.lcut(text)
    filtered = [w for w in words if w not in STOPWORDS and w.strip() and not w.isdigit() and len(w) >= 2]
    if not filtered:
        return []

    try:
        doc = ' '.join(filtered)
        tfidf = TfidfVectorizer()
        # 转换为特征矩阵
        matrix = tfidf.fit_transform([doc])
        # 获取所有特征词的列表
        features = tfidf.get_feature_names_out()
        # 转换为密集数组
        scores = matrix.toarray()[0]
        # 压缩为元组迭代器
        word_scores = sorted(zip(features, scores), key=lambda x: x[1], reverse=True)
        return [w for w, s in word_scores if s > 0][:top_k]
    except ValueError:
        return []


def get_keyword_strings(keywords_list):
    """将关键词列表转为逗号分隔的字符串（兼容旧格式）"""
    return [kw["word"] for kw in keywords_list]
