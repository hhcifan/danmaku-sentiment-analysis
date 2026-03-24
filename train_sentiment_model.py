import os
import random
import warnings
import dataset
import jieba
# 配置Hugging Face国内镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["TRANSFORMERS_CACHE"] = "D:/PycharmProjects/ProductRecommendationSystem/models"

import torch  # >-<
import torch.nn as nn  # >-<
import matplotlib.pyplot as plt
from loguru import logger
from transformers import AutoTokenizer, AutoModel

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL_NAME = "D:\PycharmProjects\ProductRecommendationSystem\models\models--hfl--chinese-roberta-wwm-ext\snapshots\chinese-roberta-wwm-ext"
MAX_LEN = 64
BATCH_SIZE = 16


id2label = {0: "负向", 1: "正向", 2: "中性"}

# ===================== 4. 情感分类模型 =====================
class BertSentimentModel(nn.Module):
    def __init__(self, num_classes=3):
        super().__init__()
        self.bert = AutoModel.from_pretrained(MODEL_NAME)
        self.drop = nn.Dropout(0.1)
        self.fc = nn.Linear(self.bert.config.hidden_size, num_classes)

    def forward(self, input_ids, attention_mask, token_type_ids=None):
        out = self.bert(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids)
        out = self.drop(out.last_hidden_state[:, 0, :])
        return self.fc(out)


def augment_dataset(dataset):
    """
    对文本数据集进行增强和扩充
    """

    # 定义文本增强函数
    def augment_text(text):
        # 同义词典
        synonym_dict = {
            "好看": ["漂亮", "养眼", "美观", "绝了"],
            "垃圾": ["差劲", "拉胯", "不行", "烂"],
            "喜欢": ["中意", "稀罕", "爱了", "超爱"],
            "难看": ["丑", "磕碜", "没眼看", "丑爆"],
            "好用": ["好使", "给力", "赞"],
            "牛逼": ["厉害", "强", "牛"],
            "一般": ["普通", "还行", "凑合"]
        }

        # 分词
        words = jieba.lcut(text)

        # 同义词替换
        for i, w in enumerate(words):
            if w in synonym_dict and random.random() < 0.3:
                words[i] = random.choice(synonym_dict[w])

        # 随机插入语气词（修复了原代码中语气词插入逻辑位置错误的问题）
        stop_words = ["啊", "呀", "呢", "吧", "哇", "哦", "噢"]
        if random.random() < 0.2 and len(words) > 0:
            insert_pos = random.randint(0, len(words))
            words.insert(insert_pos, random.choice(stop_words))

        return "".join(words)

    # 3. 扩充数据集
    augmented_dataset = []
    for text, label in dataset.dataset:
        # 添加原始样本
        augmented_dataset.append((text, label))
        # 50%概率添加增强后的样本
        if random.random() < 0.5:
            augmented_text_data = augment_text(text)
            augmented_dataset.append((augmented_text_data, label))

    # 打乱数据集
    random.shuffle(augmented_dataset)

    return augmented_dataset


def train_sentiment_model(model, tokenizer, dataset):
    logger.info("开始训练BERT情感分类模型...")
    train_size = int(0.9 * len(dataset))
    train_data = dataset[:train_size]
    val_data = dataset[train_size:]
    # 优化器
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5)
    # 损失函数
    loss_fn = nn.CrossEntropyLoss()

    model.train()

    for epoch in range(3):
        total_loss = 0.0
        for i in range(0, len(train_data), BATCH_SIZE):
            batch_data = train_data[i:i + BATCH_SIZE]
            texts = [item[0] for item in batch_data]
            labels = torch.tensor([item[1] for item in batch_data]).to(DEVICE)

            inputs = tokenizer(texts, max_length=MAX_LEN, padding=True, truncation=True, return_tensors="pt").to(DEVICE)
            outputs = model(**inputs)
            loss = loss_fn(outputs, labels)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        model.eval()
        val_correct = val_total = 0
        with torch.no_grad():
            for i in range(0, len(val_data), BATCH_SIZE):
                batch_data = val_data[i:i + BATCH_SIZE]
                texts = [item[0] for item in batch_data]
                labels = torch.tensor([item[1] for item in batch_data]).to(DEVICE)
                inputs = tokenizer(texts, max_length=MAX_LEN, padding=True, truncation=True, return_tensors="pt").to(
                    DEVICE)
                outputs = model(**inputs)
                preds = torch.argmax(outputs, dim=1)  # 对每个样本的输出（形状[batch_size, num_classes]），在类别维度（dim=1）取最大值的索引，即预测的类别；
                val_correct += (preds == labels).sum().item()
                val_total += len(labels)
        val_acc = val_correct / val_total if val_total > 0 else 0
        logger.success(f"第{epoch + 1}轮 | 损失：{total_loss / len(train_data):.4f} | 准确率：{val_acc:.4f}")
        model.train()

    torch.save(model.state_dict(), "bert_sentiment_model.pth")
    logger.success("模型已保存：bert_sentiment_model.pth")
    model.eval()
    return model



# ===================== 7. 主函数改造 =====================
def main():
    logger.add("runtime.log", rotation="500MB", encoding="utf-8", level="DEBUG")
    logger.info("===== 电商直播弹幕分析系统启动 =====")
    logger.info(f"设备：{DEVICE}")

    logger.info("加载BERT模型...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = BertSentimentModel(num_classes=3).to(DEVICE)

    if os.path.exists("bert_sentiment_model.pth"):
        try:
            model.load_state_dict(torch.load("bert_sentiment_model.pth", map_location=DEVICE))
            model.eval()
            logger.success("✅ 已加载本地模型")
        except:
            logger.warning("本地模型加载失败，重新训练")
            model = train_sentiment_model(model, tokenizer, augment_dataset(dataset))
    else:
        model = train_sentiment_model(model, tokenizer, augment_dataset(dataset))



if __name__ == "__main__":
    main()
