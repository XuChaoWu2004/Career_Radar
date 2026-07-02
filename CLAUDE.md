# CLAUDE.md

## 项目概述

求职雷达：Playwright 无头浏览器抓取公司校招页面 → 黑白名单过滤 → SQLite 去重 → CSV 输出。

## 文件结构

```
radar.py            # 抓取引擎（一般不改）
config_base.py      # 公共配置：关键词、系统参数、日志
config_global.py    # 海外公司列表（当前 env='global'）
config_cn.py        # 国内公司列表（空，预留）
```

`radar.py:33` 的 `env = 'global'` 决定加载哪个配置。切换环境改这一行。

## 运行

```bash
pip install playwright && playwright install chromium
python radar.py
```

Windows + Git Bash 注意：`%LOCALAPPDATA%\Microsoft\WindowsApps\python` 是 Store 假货，会挡真正 Python 的 PATH。真货在 `E:/Python/python/python.exe`。

## 添加新公司

编辑 `config_global.py`（或 `config_cn.py`）的 `TARGET_COMPANIES`，加字典：

**必填**：
- `name` — CSV 显示名
- `url` — 带筛选条件的职位列表页
- `selector` — 岗位链接的 CSS 选择器
- `domain_prefix` — 补全相对链接（无则 `""`）

**常用可选**：
- `extract_title` — JS 表达式，`<a>` 标签空时（Oracle HCM）从父级取标题
- `extract_location` — JS 表达式，提取地点文本后与 `TARGET_LOCATIONS` 匹配
- `next_button_selector` — 翻页按钮选择器（Taleo 系统用 `"a#showMoreJobs"`）
- `category` — 分组标签
- `selector_timeout` / `goto_timeout` / `idle_timeout` — 超时覆盖（毫秒）

## 配置 vs 引擎

- **改配置**（加公司、调关键词、超时）→ 只动 `config_base.py` / `config_global.py` / `config_cn.py`
- **改引擎**（抓取策略、翻页逻辑、输出格式）→ 动 `radar.py`

## 引擎关键逻辑

`radar.py` 主流程：逐家公司 → 打开 URL（3 次重试）→ 自动关 Cookie 弹窗 → 等 selector → networkidle → `_scroll_to_load_all()` 滚动+点翻页 → 提取元素 → `is_target_job()` 过滤 → SHA-256 去重（内存 + SQLite）→ CSV。

**翻页机制**（`_scroll_to_load_all`）：三层 fallback
1. 公司专属 `next_button_selector`
2. 通用 Load More / Show More 按钮
3. 通用 Next 翻页链接

所有点击用 `evaluate("el => el.click()")` 而非 Playwright `click()`——因为 Angular `ng-click` 的按钮常被岗位卡片遮挡，Playwright 的可点击性检查会失败。

**平台特征**：
- Oracle HCM（JPMorgan）：`<a>` 空标签，需 `extract_title` 爬到 `<li>` 取 `.job-tile__title`
- Taleo TGnewUI（UBS、Morgan Stanley）：Angular 翻页，`a#showMoreJobs`
- Usercentrics cookie（大摩、德银）：主检查 + 二次补充检查
