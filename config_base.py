"""
Career Radar 基础配置 —— 黑白名单、系统参数、日志等共享配置。
config_global.py 和 config_cn.py 均从此文件继承。
"""
import os
import logging

# 脚本所在目录的绝对路径，所有输出文件都落在这个目录下
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================================================================================
# 🛠️ 【配置区 1】：关键词黑白名单 (如何新增/修改？)
#
# 1. 黑名单 (EXCLUDE_KEYWORDS)：
#    - 只要岗位的标题里包含这里的任何一个词，就直接扔掉（不要高级岗位）。
#    - 新增方法：在方括号里加引号和英文逗号，例如加一个 "manager"，变成：['vp', 'manager']
#    - 注意：不区分大小写，写小写即可。
#
# 2. 白名单 (INCLUDE_KEYWORDS)：
#    - 如果这里不是空的，那么岗位标题【必须】包含这里的至少一个词，否则扔掉。
#    - 新增方法：和黑名单一样。比如想加上2028年的，变成：['2027', '2028']
# =========================================================================================

EXCLUDE_KEYWORDS = [
    'senior', 'vp', 'vice president', 'director',
    'manager', 'lead', 'experienced',
    '高级', '总监', '经理', '主管', '首席', '专家', '合伙人',
    'head', 'supervisor', 'principal', 'avp', 'svp',
]
INCLUDE_KEYWORDS = [
    # -- 英文 --
    'student', 'intern', 'summer', 'graduate', 'early career',
    'campus', 'internship', 'off-cycle', 'spring', 'fall', 'autumn', 'PTA', 'BA', 'challenge'
    # -- 中文 --
    '暑期', '实习', '校招', '管培生', '校园招聘',
    '日常', '继任', '应届生', '分析师', '研究员', '投研', '行研', '商分',
    # -- 年份 --
    '2026', '2027', '2028',
]

# 目标地理位置（公司配置 extract_location 时启用，从卡片定位元素提取后匹配）
TARGET_LOCATIONS = [
    'Hong Kong', 'Shanghai', 'Beijing', 'Shenzhen', 'Guangzhou',
    'China', 'Asia', 'APAC',
    '香港', '上海', '北京', '深圳', '广州',
]

# =========================================================================================
# ⚙️ 系统基础配置 (一般不需要修改)
# =========================================================================================

DB_FILE = os.path.join(BASE_DIR, 'jobs_database.db')

# ---- CSV 输出 ----
OUTPUT_CSV = r'E:\OneDrive\MYGO\2027wip\求职雷达_总表.csv'

MARKER_NEW = '[新岗位]'
MARKER_OLD = '[历史]'
MARKER_NO_JOBS = '未开放'

MAX_RETRIES = 3                            # 单页抓取最大重试次数
RETRY_DELAY = 2                            # 重试间隔（秒）

# 超时配置（毫秒）：可按公司单独覆盖，用于国内站/慢速站点
GOTO_TIMEOUT = 60000                       # page.goto 导航超时
SELECTOR_TIMEOUT = 20000                   # wait_for_selector 等待岗位卡片超时
IDLE_TIMEOUT = 10000                       # networkidle 等待超时

# ------------------------------------------------------------------
# 日志配置：同时输出到控制台和 radar.log 文件，方便排查历史问题
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, 'radar.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
