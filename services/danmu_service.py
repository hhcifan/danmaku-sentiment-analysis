"""弹幕采集服务 - 爬虫采集 + 消费线程"""
import queue
import re
import time
import threading
from collections import deque
from loguru import logger
from DrissionPage import WebPage, ChromiumOptions
import config
from services.sensitive_service import filter_sensitive, log_sensitive_block


# ===================== 全局状态 =====================
EXIT_FLAG = threading.Event()
DANMU_LOCK = threading.Lock()
JS_LOCK = threading.Lock()

DANMU_BUFFER = deque(maxlen=config.DANMU_BUFFER_MAX)
DANMU_SET = set()

# 丢弃计数器（监控用）
DANMU_DROP_COUNT = 0

# SocketIO 实例（由 app.py 注入）
_socketio = None


def set_socketio(sio):
    global _socketio
    _socketio = sio


def add_danmu(text):
    """添加不重复的弹幕到缓冲区"""
    global DANMU_DROP_COUNT
    if text and text not in DANMU_SET:
        if len(DANMU_SET) >= config.DANMU_SET_MAX:
            oldest = next(iter(DANMU_SET))
            DANMU_SET.remove(oldest)
        # 缓冲区满时记录丢弃
        if len(DANMU_BUFFER) >= config.DANMU_BUFFER_MAX:
            DANMU_DROP_COUNT += 1
        DANMU_SET.add(text)
        DANMU_BUFFER.append(text)
        return True
    return False


def get_drop_count():
    """获取丢弃弹幕计数"""
    return DANMU_DROP_COUNT


def get_buffer_batch(max_size):
    """从缓冲区取出一批弹幕"""
    with DANMU_LOCK:
        batch = []
        while DANMU_BUFFER and len(batch) < max_size:
            batch.append(DANMU_BUFFER.popleft())
        return batch


def add_manual_danmu(text):
    """手动添加弹幕（从前端或控制台输入）"""
    if not text:
        return False
    filtered_text, matched_words = filter_sensitive(text)
    if matched_words:
        log_sensitive_block(text, filtered_text, matched_words, _socketio)

    if not filtered_text:
        return False

    with DANMU_LOCK:
        return add_danmu(filtered_text)


def write_leak_log(danmu_data):
    """记录漏爬的弹幕"""
    try:
        with open(config.LEAK_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {danmu_data}\n")
    except Exception as e:
        logger.error(f"写入漏爬日志失败：{e}")


def danmu_consumer(danmu_queue, filter_keywords):
    """弹幕消费线程"""
    logger.info(f"弹幕消费线程启动（线程ID：{threading.get_ident()}）")
    while not EXIT_FLAG.is_set():
        try:
            try:
                danmu_data = danmu_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if not danmu_data or not isinstance(danmu_data, dict):
                continue

            msg = f"[{danmu_data.get('time', '')}] {danmu_data.get('text', '')}"
            if not msg:
                write_leak_log(f"空数据：{danmu_data}")
                continue

            time_match = re.search(r"\[\d{2}:\d{2}:\d{2}] (.*)", msg)
            if not time_match:
                write_leak_log(f"格式错误：{msg}")
                continue
            full_text = time_match.group(1).strip()

            if any(keyword in full_text for keyword in filter_keywords):
                continue

            pure_danmu = ""
            colon_split = full_text.split("：", 1)
            if len(colon_split) == 2:
                pure_danmu = colon_split[1].strip()
            else:
                pure_danmu = full_text.strip()

            if pure_danmu:
                filtered_text, matched_words = filter_sensitive(pure_danmu)
                if matched_words:
                    log_sensitive_block(pure_danmu, filtered_text, matched_words, _socketio)

                with DANMU_LOCK:
                    if add_danmu(filtered_text):
                        with open("抖音原始弹幕.txt", "a", encoding="utf-8") as f:
                            f.write(f"[{time.strftime('%H:%M:%S')}] {pure_danmu}\n")

            danmu_queue.task_done()
        except Exception as e:
            logger.warning(f"消费线程异常（ID：{threading.get_ident()}）：{e}")
            continue

    logger.info(f"弹幕消费线程退出（线程ID：{threading.get_ident()}）")


def crawl_danmu(url=None):
    """弹幕爬虫"""
    url = url or config.LIVE_URL
    logger.info("正在启动浏览器...")
    co = ChromiumOptions()
    co.set_browser_path(config.EDGE_PATH)
    co.set_argument('--blink-settings=imagesEnabled=false')
    co.set_argument('--disable-media-autoplay')
    co.set_argument('--enable-javascript')
    co.set_argument('--disable-cache')
    co.set_argument('--disable-extensions')
    chrome = WebPage(chromium_options=co)
    tab = chrome.get_tab()
    danmu_queue = queue.Queue(maxsize=0)

    try:
        logger.info(f"访问直播间：{url}")
        chrome.get(url)

        selectors = ['.webcast-chatroom___list', '.chatroom-list', '.danmu-list']
        target_selector = None
        for sel in selectors:
            try:
                tab.wait.eles_loaded(sel, timeout=5)
                target_selector = sel
                break
            except Exception:
                continue
        if not target_selector:
            raise TimeoutError("未找到弹幕列表元素")
        logger.info(f"找到弹幕列表，选择器：{target_selector}")

        # 等待页面DOM稳定后再注入JS
        time.sleep(2)

        js = f"""
        window.danmuList = [];
        window.danmuMaxCache = 5000;
        window.danmuLastFetchTime = new Date().getTime();
        window.danmuObserverReady = false;

        (function tryInit(retries) {{
            const selectors = ['{target_selector}', '.webcast-chatroom___list', '.chatroom-list', '.danmu-list'];
            let target = null;
            for(let sel of selectors) {{
                target = document.querySelector(sel);
                if(target) break;
            }}
            if(!target) {{
                if(retries > 0) {{
                    setTimeout(() => tryInit(retries - 1), 500);
                }} else {{
                    console.error('弹幕列表元素未找到，已耗尽重试次数');
                }}
                return;
            }}
            const obs = new MutationObserver((muts) => {{
                let batchData = [];
                for(let m of muts){{
                    m.addedNodes.forEach(n => {{
                        if(n.nodeType === 1){{
                            const t = n.innerText.trim();
                            if(t){{
                                batchData.push({{
                                    time: new Date().toLocaleTimeString(),
                                    text: t,
                                    ts: new Date().getTime()
                                }});
                            }}
                        }}
                    }});
                }}
                if(batchData.length > 0){{
                    window.danmuList.push(...batchData);
                    if(window.danmuList.length > window.danmuMaxCache){{
                        const overCount = window.danmuList.length - window.danmuMaxCache;
                        const leakData = window.danmuList.splice(0, overCount);
                        if(!window.leakDanmu) window.leakDanmu = [];
                        window.leakDanmu.push(...leakData);
                    }}
                }}
            }});
            obs.observe(target, {{childList: true, subtree: true, attributes: false}});
            window.danmuObserverReady = true;
            console.log('弹幕监听已启动，目标元素：' + target.className);
        }})(20);

        window.getDanmu = function() {{
            const len = window.danmuList.length;
            if(len <= 10) return [];
            window.danmuLastFetchTime = new Date().getTime();
            return window.danmuList.splice(0, len - 10);
        }};
        window.getLeakDanmu = function() {{
            const leak = window.leakDanmu || [];
            window.leakDanmu = [];
            return leak;
        }};
        """
        tab.run_js(js)

        # 等待 Observer 就绪（最多10秒）
        for _ in range(20):
            ready = tab.run_js('return window.danmuObserverReady;')
            if ready:
                break
            time.sleep(0.5)

        if tab.run_js('return window.danmuObserverReady;'):
            logger.success("直播间弹幕监听成功！")
        else:
            raise TimeoutError("MutationObserver 初始化超时，未找到弹幕DOM元素")

        def danmu_producer():
            global DANMU_DROP_COUNT
            while not EXIT_FLAG.is_set():
                try:
                    with JS_LOCK:
                        danmu_list = tab.run_js('return window.getDanmu();')
                        leak_list = tab.run_js('return window.getLeakDanmu();')

                    if danmu_list and len(danmu_list) > 0:
                        for danmu in danmu_list:
                            try:
                                danmu_queue.put_nowait(danmu)
                            except queue.Full:
                                DANMU_DROP_COUNT += 1
                                write_leak_log(f"队列满漏爬：{danmu}")

                    if leak_list and len(leak_list) > 0:
                        logger.warning(f"检测到JS端漏爬弹幕：{len(leak_list)}条")
                        for leak in leak_list:
                            write_leak_log(f"JS溢出漏爬：{leak}")

                except Exception as e:
                    logger.warning(f"生产线程异常：{e}")

                # 自适应轮询：队列压力大时加快轮询
                q_size = danmu_queue.qsize()
                if q_size > config.QUEUE_PRESSURE_THRESHOLD:
                    time.sleep(config.PRODUCER_POLL_MIN)
                else:
                    time.sleep(config.PRODUCER_POLL_MAX)

        producer_thread = threading.Thread(target=danmu_producer, daemon=True)
        producer_thread.start()

        consumer_threads = []
        for i in range(config.CONSUMER_THREAD_NUM):
            t = threading.Thread(
                target=danmu_consumer,
                args=(danmu_queue, config.FILTER_KEYWORDS),
                daemon=True
            )
            t.start()
            consumer_threads.append(t)
        logger.info(f"启动{config.CONSUMER_THREAD_NUM}个弹幕消费线程")

        while not EXIT_FLAG.is_set():
            q_size = danmu_queue.qsize()
            if q_size > 500:
                logger.warning(f"弹幕队列堆积，当前长度：{q_size}条")
            time.sleep(1)

    except Exception as e:
        logger.error(f"爬虫异常：{e}")
        logger.warning("建议用手动模式演示")
    finally:
        # 仅关闭浏览器，不设置EXIT_FLAG（避免杀死分析线程）
        logger.info("开始优雅退出...")
        wait_time = 0
        while danmu_queue.qsize() > 0 and wait_time < 10:
            logger.info(f"剩余未处理弹幕：{danmu_queue.qsize()}条")
            danmu_queue.join()
            time.sleep(1)
            wait_time += 1
        chrome.quit()
        logger.info("浏览器已关闭")


def stop():
    """停止弹幕采集"""
    EXIT_FLAG.set()


def reset():
    """重置退出标志"""
    EXIT_FLAG.clear()


def is_running():
    """检查是否正在运行"""
    return not EXIT_FLAG.is_set()
