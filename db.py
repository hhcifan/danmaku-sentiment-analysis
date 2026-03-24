"""MySQL数据库管理模块 - 连接池 + 表初始化 + 通用CRUD"""
import pymysql
from pymysql import OperationalError, IntegrityError
from dbutils.pooled_db import PooledDB
from loguru import logger
import config


# ===================== 连接池 =====================
_pool = None


def get_pool():
    """获取/初始化连接池"""
    global _pool
    if _pool is None:
        _pool = PooledDB(
            creator=pymysql,
            mincached=config.POOL_MIN_CACHED,
            maxcached=config.POOL_MAX_CACHED,
            maxconnections=config.POOL_MAX_CONNECTIONS,
            blocking=True,
            host=config.MYSQL_CONFIG["host"],
            user=config.MYSQL_CONFIG["user"],
            password=config.MYSQL_CONFIG["password"],
            database=config.MYSQL_CONFIG["database"],
            charset=config.MYSQL_CONFIG["charset"],
            autocommit=True,
        )
        logger.success("MySQL连接池初始化成功")
    return _pool


def get_conn():
    """从连接池获取连接"""
    return get_pool().connection()


# ===================== 表初始化 =====================
def init_tables():
    """创建所有需要的数据库表"""
    conn = get_conn()
    try:
        cursor = conn.cursor()

        # 清洗后的弹幕表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cleaned_danmu (
            id INT AUTO_INCREMENT PRIMARY KEY,
            danmu_text TEXT NOT NULL,
            sentiment VARCHAR(10) NOT NULL,
            keywords TEXT,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_create_time (create_time),
            UNIQUE KEY uk_danmu_text (danmu_text(255))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 商品信息表（增加 pinned 和 click_rate_factor 字段）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_info (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_id INT NOT NULL,
            product_name VARCHAR(100) NOT NULL,
            mention_count INT DEFAULT 0,
            positive_mention INT DEFAULT 0,
            negative_mention INT DEFAULT 0,
            heat FLOAT DEFAULT 0.0,
            pinned TINYINT DEFAULT 0,
            click_rate_factor FLOAT DEFAULT 0.0,
            update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_product_id (product_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 尝试为旧表添加新字段
        try:
            cursor.execute("ALTER TABLE product_info ADD COLUMN pinned TINYINT DEFAULT 0")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE product_info ADD COLUMN click_rate_factor FLOAT DEFAULT 0.0")
        except Exception:
            pass

        # 复盘报告表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_report (
            id INT AUTO_INCREMENT PRIMARY KEY,
            total_danmu INT DEFAULT 0,
            positive_count INT DEFAULT 0,
            negative_count INT DEFAULT 0,
            neutral_count INT DEFAULT 0,
            hot_keywords TEXT,
            product_heat TEXT,
            report_content TEXT,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 用户行为记录表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_behavior (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL,
            product_id INT NOT NULL,
            action_type ENUM('click','cart','order') NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user_id (user_id),
            INDEX idx_product_action (product_id, action_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 商品转化数据表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversion_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_id INT NOT NULL,
            click_count INT DEFAULT 0,
            cart_count INT DEFAULT 0,
            order_count INT DEFAULT 0,
            click_rate FLOAT DEFAULT 0.0,
            cart_rate FLOAT DEFAULT 0.0,
            order_rate FLOAT DEFAULT 0.0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_product_id (product_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 敏感弹幕屏蔽日志表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensitive_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            original_text TEXT NOT NULL,
            filtered_text TEXT NOT NULL,
            matched_words VARCHAR(255),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 商品关键词反馈表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_keyword_feedback (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_id INT NOT NULL,
            keyword VARCHAR(100) NOT NULL,
            sentiment VARCHAR(10) NOT NULL,
            mention_count INT DEFAULT 1,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_prod_kw (product_id, keyword)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        conn.commit()
        logger.success("所有数据库表初始化成功")
    except OperationalError as e:
        logger.error(f"MySQL连接失败：{e}")
        raise
    except Exception as e:
        logger.error(f"MySQL表创建失败：{e}")
        raise
    finally:
        conn.close()


# ===================== 通用CRUD工具 =====================
def upsert(table_name, data, unique_key):
    """通用的数据插入/更新函数"""
    conn = get_conn()
    try:
        cursor = conn.cursor()

        if table_name == "cleaned_danmu" and "id" in data:
            del data["id"]

        cursor.execute(
            f"SELECT 1 FROM {table_name} WHERE {unique_key} = %s",
            (data[unique_key],)
        )
        exists = cursor.fetchone()

        if exists:
            update_cols = [k for k in data.keys() if k != unique_key]
            if not update_cols:
                return
            update_sql = f"UPDATE {table_name} SET {', '.join([f'{k}=%s' for k in update_cols])} WHERE {unique_key}=%s"
            update_vals = [data[k] for k in update_cols] + [data[unique_key]]
            cursor.execute(update_sql, update_vals)
        else:
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            cursor.execute(insert_sql, tuple(data.values()))

        conn.commit()
    except IntegrityError as e:
        logger.warning(f"{table_name}数据已存在：{e}")
    except Exception as e:
        logger.error(f"操作{table_name}失败：{e}")
        conn.rollback()
    finally:
        conn.close()


def insert(table_name, data):
    """插入一条记录"""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        cursor.execute(sql, tuple(data.values()))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"插入{table_name}失败：{e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def query(sql, params=None):
    """执行查询并返回结果列表（字典格式）"""
    conn = get_conn()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql, params or ())
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"查询失败：{e}")
        return []
    finally:
        conn.close()


def execute(sql, params=None):
    """执行非查询SQL"""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        logger.error(f"执行SQL失败：{e}")
        conn.rollback()
        return 0
    finally:
        conn.close()
