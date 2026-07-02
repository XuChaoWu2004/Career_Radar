import sqlite3
import hashlib
import re
import os
import sys
import csv
import time
import logging
import importlib
from playwright.sync_api import sync_playwright, Page

# 确保脚本所在目录在 sys.path 中，这样无论从哪里运行都能找到配置模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ---- Placeholder：纯为 PyCharm 静态分析消红线，运行时被动态注入覆写 ----
TARGET_COMPANIES = []
EXCLUDE_KEYWORDS = []
INCLUDE_KEYWORDS = []
TARGET_LOCATIONS = []
BASE_DIR = ""
DB_FILE = ""
OUTPUT_CSV = ""
MARKER_NEW = ""
MARKER_OLD = ""
MARKER_NO_JOBS = ""
MAX_RETRIES = 0
RETRY_DELAY = 0
GOTO_TIMEOUT = 0
SELECTOR_TIMEOUT = 0
IDLE_TIMEOUT = 0

# ---- 动态加载配置（覆写上方所有 placeholder） ----
env = 'global'
config_module = importlib.import_module(f'config_{env}')
for attr in dir(config_module):
    if not attr.startswith('_'):
        globals()[attr] = getattr(config_module, attr)

logger = logging.getLogger(__name__)


# =========================================================================================
# 数据库初始化
# =========================================================================================
def init_db() -> sqlite3.Connection:
    """创建 SQLite 数据库和 seen_jobs 表（如果不存在），返回连接对象。"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hloseen_jobs (
            job_hash TEXT PRIMARY KEY,
            company TEXT,
            title TEXT,
            link TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn


# =========================================================================================
# 关键词匹配（英文用单词边界，中文用子串匹配）
# =========================================================================================
def _keyword_matches(keyword: str, text: str) -> bool:
    """
    检测 keyword 是否在 text 中命中。
    - 纯 ASCII 关键词：使用正则 \b 单词边界，避免 'intern' 误命中 'international'
    - 含中文等非 ASCII 关键词：使用简单子串匹配
    """
    if not keyword:  # 防御：空关键词会误匹配任何文本
        return False
    if keyword.isascii():
        return bool(re.search(r'\b' + re.escape(keyword) + r'\b', text))
    else:
        return keyword in text


# =========================================================================================
# 黑白名单过滤
# =========================================================================================
def is_target_job(title: str) -> bool:
    """
    先走黑名单 -- 命中任一排除词则返回 False。
    再走白名单 -- 如果白名单非空，必须命中至少一个词才返回 True。
    """
    title_lower = title.lower()

    for kw in EXCLUDE_KEYWORDS:
        if _keyword_matches(kw, title_lower):
            return False

    if INCLUDE_KEYWORDS:
        if not any(_keyword_matches(kw, title_lower) for kw in INCLUDE_KEYWORDS):
            return False

    return True


# =========================================================================================
# 动态加载辅助：滚动 + 点击 Load More，触发分页/懒加载
# =========================================================================================
def _scroll_to_load_all(page: Page, selector: str, company_name: str,
                        next_button_selector: str = None) -> None:
    """持续滚动并尝试点击 Load More / Next，直到 selector 匹配的元素数量不再增长。

    Args:
        next_button_selector: 公司专属的翻页/加载更多按钮选择器（优先于通用选择器）。
    """
    start_count = len(page.locator(selector).all())
    try:
        prev_count = start_count
        for i in range(30):
            # 先滚到底，触发懒加载
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.8)

            clicked = False

            # ---- 优先级 1：公司专属翻页选择器 ----
            if next_button_selector:
                try:
                    # 用 wait_for_selector 等按钮出现（比 is_visible 更可靠）
                    btn = page.wait_for_selector(next_button_selector, state='attached', timeout=3000)
                    if btn:
                        # 跳过 Playwright click() —— 岗位卡片可能遮挡按钮，导致可点击性检查失败
                        # 直接走原生 JS click，触发 Angular ng-click 最可靠
                        btn.evaluate("el => el.click()")
                        logger.info("[%s] 🔘 点击专属翻页 [%s]", company_name, next_button_selector)
                        clicked = True
                except Exception:
                    pass  # 按钮不存在，不是错误

            # ---- 优先级 2：通用 Load More / Show More ----
            if not clicked:
                try:
                    load_more = page.locator(
                        "button:has-text('Load More'), button:has-text('Show More'), "
                        "a:has-text('Load More'), a:has-text('Show More'), "
                        "[class*='load-more'], [class*='show-more']"
                    ).first
                    if load_more.is_visible(timeout=1500):
                        load_more.evaluate("el => el.click()")
                        clicked = True
                except Exception:
                    pass

            # ---- 优先级 3：通用 Next 翻页 ----
            if not clicked:
                try:
                    next_btn = page.locator(
                        "a:has-text('Next'), button:has-text('Next'), "
                        "[aria-label='Next'], [aria-label='next page'], "
                        "a#showMoreJobs, a.showMoreJobs, "
                        "[id*='showMore'] a:has-text('Next'), "
                        "[class*='pagination'] a:has-text('>'), "
                        "[class*='pagination'] a:has-text('Next'), "
                        "[class*='pager'] a:has-text('>'), "
                        "[class*='pager'] a:has-text('Next')"
                    ).first
                    if next_btn.is_visible(timeout=1500):
                        next_btn.evaluate("el => el.click()")
                        clicked = True
                except Exception:
                    pass

            if clicked:
                # 等待新一批岗位渲染：轮询 selector 数量增长，最多等 10 秒
                for _ in range(20):
                    time.sleep(0.5)
                    current = len(page.locator(selector).all())
                    if current > prev_count:
                        break
                time.sleep(0.5)

            current_count = len(page.locator(selector).all())
            if current_count == prev_count:
                break
            prev_count = current_count

        final_count = len(page.locator(selector).all())
        if final_count > start_count:
            logger.info("[%s] 📄 动态加载完成: %d → %d 个岗位", company_name, start_count, final_count)
        else:
            logger.debug("[%s] 动态加载完毕，selector 匹配数: %d", company_name, final_count)
    except Exception:
        pass


# =========================================================================================
# 单家公司抓取（带重试）
# =========================================================================================
def fetch_company_jobs(
    page: Page,
    conn: sqlite3.Connection,
    company_config: dict
) -> list[dict]:
    """
    访问一家公司的招聘页面，筛选出符合黑白名单的岗位。
    支持失败自动重试（MAX_RETRIES 次）。
    """
    company_name = company_config["name"]
    target_url = company_config["url"]
    selector = company_config["selector"]
    prefix = company_config["domain_prefix"]
    category = company_config.get("category", "Other")

    jobs_found: list[dict] = []
    cursor = conn.cursor()
    logger.info("正在扫描 [%s] ...", company_name)

    # ---- 页面导航（网络错误可重试） ----
    goto_timeout = company_config.get("goto_timeout", GOTO_TIMEOUT)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            page.goto(target_url, timeout=goto_timeout, wait_until='domcontentloaded')
            break  # 导航成功
        except Exception as e:
            logger.warning("[%s] 第 %d/%d 次导航失败: %s", company_name, attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                logger.error("[%s] 已达最大重试次数，跳过该公司", company_name)
                return jobs_found

    # ---- Cookie 同意弹窗处理：等待 JS 渲染后优先 Allow All ----
    page.wait_for_timeout(2500)  # 等待 JS 注入 cookie 弹窗
    COOKIE_BUTTONS = [
        "#system-ialert-button",             # Barclays 专用
        "text=Accept All Cookies",
        "text=Allow All Cookies",
        "text=Accept All",
        "text=Allow All",
        "text=Accept Cookies",
        "text=Accept",
        "text=I Agree",
        "button[data-testid='uc-accept-all-button']",     # Usercentrics 全部接受
        "#usercentrics-root button:has-text('Accept')",
        "#usercentrics-root button:has-text('全部接受')",
        "#usercentrics-root [aria-label='Accept all']",
    ]
    for btn_text in COOKIE_BUTTONS:
        try:
            btn = page.locator(btn_text).first
            if btn.is_visible(timeout=1000):
                btn.click()
                logger.info("[%s] ✅ 已处理 Cookie 弹窗 [%s]", company_name, btn_text)
                page.wait_for_timeout(1500)
                break
        except Exception:
            continue

    # 二次检查：Usercentrics 可能后加载
    try:
        uc_btn = page.locator("#usercentrics-root button:has-text('Accept')").first
        if uc_btn.is_visible(timeout=3000):
            uc_btn.click()
            logger.info("[%s] ✅ 二次处理 Usercentrics 弹窗", company_name)
            page.wait_for_timeout(1500)
    except Exception:
        pass

    # ---- 等待岗位元素（超时 = 页面无岗位，不重试） ----
    selector_timeout = company_config.get("selector_timeout", SELECTOR_TIMEOUT)
    try:
        page.wait_for_selector(selector, timeout=selector_timeout, state='attached')
    except Exception:
        logger.info("[%s] 未检测到岗位卡片（selector 超时），按 0 岗位处理", company_name)
        return jobs_found

    # 等待网络空闲以获取动态渲染的完整列表（超时不致命）
    idle_timeout = company_config.get("idle_timeout", IDLE_TIMEOUT)
    try:
        page.wait_for_load_state('networkidle', timeout=idle_timeout)
    except Exception:
        logger.debug("[%s] networkidle 等待超时，继续使用已加载的 DOM", company_name)

    # 触发懒加载 / 无限滚动 / Load More，拉取全部岗位
    _scroll_to_load_all(page, selector, company_name,
                        next_button_selector=company_config.get("next_button_selector"))

    logger.info("[%s] 页面加载成功", company_name)

    # ---- 抓取岗位列表 ----
    try:
        job_links = page.locator(selector).all()
        logger.info("[%s] 截获 %d 个岗位元素，正在执行黑白名单过滤...", company_name, len(job_links))
    except Exception as e:
        logger.error("[%s] 无法定位岗位元素 (selector 可能已失效): %s", company_name, e)
        return jobs_found

    # 用集合做本轮去重——同一个页面里可能出现重复 DOM 元素
    seen_hashes: set[str] = set()
    new_inserts: list[tuple[str, str, str, str]] = []

    # 读取可选的自定义提取表达式（在 config.py 中按需配置）
    extract_title_js = company_config.get("extract_title")
    extract_link_js = company_config.get("extract_link")
    extract_location_js = company_config.get("extract_location")

    for link_element in job_links:
        try:
            # 标题提取：有自定义 JS 就用，否则默认 inner_text()
            if extract_title_js:
                title = (link_element.evaluate(extract_title_js) or "").strip()
            else:
                title = link_element.inner_text().strip()

            # 链接提取：有自定义 JS 就用，否则默认 get_attribute("href")
            if extract_link_js:
                raw_url = link_element.evaluate(extract_link_js) or ""
            else:
                raw_url = link_element.get_attribute("href")

            # 地理位置提取与过滤（仅配置了 extract_location 的公司启用）
            if extract_location_js:
                location = (link_element.evaluate(extract_location_js) or "").strip()
                if location and TARGET_LOCATIONS:
                    if not any(_keyword_matches(kw, location.lower()) for kw in TARGET_LOCATIONS):
                        continue  # 地理位置不在目标范围内，静默跳过

            if not title or not raw_url:
                continue

            # 拼接完整的 URL
            if raw_url.startswith("http"):
                url = raw_url
            elif raw_url.startswith("/"):
                url = f"{prefix}{raw_url}"
            else:
                url = f"{prefix}/{raw_url}"

            # 剔除回车换行，防止 CSV 格式错乱
            title = title.replace('\n', ' | ').replace('\r', '')

            # 黑白名单过滤
            if not is_target_job(title):
                continue

            # 查重：公司 + 标题 + 链接 → SHA-256 指纹
            raw_string = f"{company_name}_{title}_{url}"
            job_hash = hashlib.sha256(raw_string.encode('utf-8')).hexdigest()[:32]

            # 本轮已见过的跳过
            if job_hash in seen_hashes:
                continue
            seen_hashes.add(job_hash)

            # 数据库历史查重
            cursor.execute("SELECT 1 FROM seen_jobs WHERE job_hash = ?", (job_hash,))

            if cursor.fetchone():
                status = MARKER_OLD
            else:
                status = MARKER_NEW
                new_inserts.append((job_hash, company_name, title, url))

            jobs_found.append({
                '状态 (Status)': status,
                '公司 (Company)': company_name,
                '职位 (Title)': title,
                '申请链接 (Link)': url,
                '分类 (Category)': category
            })

        except Exception as e:
            # 单条解析失败不致命，记录日志后继续下一条
            logger.debug("[%s] 跳过一条岗位 (解析异常): %s", company_name, e)
            continue

    # ---- 批量写入新岗位（一次 commit） ----
    if new_inserts:
        cursor.executemany(
            "INSERT INTO seen_jobs (job_hash, company, title, link) VALUES (?, ?, ?, ?)",
            new_inserts
        )
        conn.commit()
        logger.info("[%s] 发现 %d 个全新岗位，已写入数据库", company_name, len(new_inserts))

    logger.info("[%s] 过滤后保留 %d 个岗位（本轮新: %d / 历史旧: %d）",
                company_name, len(jobs_found), len(new_inserts), len(jobs_found) - len(new_inserts))

    return jobs_found


# =========================================================================================
# 主入口
# =========================================================================================
def main() -> None:
    logger.info("🚀 求职雷达启动！")
    conn = init_db()
    all_scraped_jobs: list[dict] = []

    # 确保数据库连接和浏览器都能妥善关闭
    try:
        with sync_playwright() as p:
            # headless=True 表示完全在后台隐形运行，不会弹窗打扰你。想看过程可以改回 False
            browser = p.chromium.launch(headless=True, args=[
                '--disable-gpu',
                '--disable-extensions',
                '--disable-background-networking',
                '--disable-sync',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--mute-audio',
            ])
            try:
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                )
                page = context.new_page()

                for idx, company_config in enumerate(TARGET_COMPANIES):
                    jobs = fetch_company_jobs(page, conn, company_config)
                    all_scraped_jobs.extend(jobs)

                    # 即使该公司没有任何匹配岗位（或页面加载失败），也插入一行占位，
                    # 方便在 Excel 中确认该公司已被扫描
                    if not jobs:
                        all_scraped_jobs.append({
                            '状态 (Status)': MARKER_NO_JOBS,
                            '公司 (Company)': company_config["name"],
                            '职位 (Title)': '',
                            '申请链接 (Link)': '',
                            '分类 (Category)': company_config.get("category", "Other")
                        })

                    # 公司间隔冷却，避免触发反爬
                    if idx < len(TARGET_COMPANIES) - 1:
                        time.sleep(RETRY_DELAY)

            finally:
                browser.close()
                logger.info("浏览器已关闭")
    finally:
        conn.close()
        logger.info("数据库连接已关闭")

    # ---- 输出 CSV ----
    if all_scraped_jobs:
        new_count = sum(1 for job in all_scraped_jobs if job['状态 (Status)'] == MARKER_NEW)
        all_scraped_jobs.sort(key=lambda x: 0 if x['状态 (Status)'] == MARKER_NEW else 1)

        print(f"\n🎉 全网扫描完毕！符合过滤条件的目标岗位共计: {len(all_scraped_jobs)} 个。")
        print(f"🔥 今日全新放出: {new_count} 个")
        print("-" * 40)

        try:
            os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
            with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['分类 (Category)', '状态 (Status)', '公司 (Company)', '职位 (Title)', '申请链接 (Link)']
                )
                writer.writeheader()
                writer.writerows(all_scraped_jobs)
            print(f"📁 数据已覆写至: {OUTPUT_CSV}")
            print(f"💡 提示：打开 Excel，按 Ctrl+F 搜索 '{MARKER_NEW}' 即可直达最新岗位！")
        except PermissionError:
            print(f"⚠️ 保存失败！请检查 {OUTPUT_CSV} 是否正在被 Excel 打开。请关闭表格后重新运行！")
    else:
        print("\n📭 扫描完毕。全网都没有找到符合黑白名单的岗位。")


if __name__ == "__main__":
    main()
