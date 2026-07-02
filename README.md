# Career Radar（求职雷达）

个人求职抓取工具——自动扫描公司校招/初级岗位页面，黑白名单过滤，SQLite 去重，输出 Excel 可读的 CSV。

## 快速开始

```bash
pip install playwright
playwright install chromium
python radar.py
```

输出：`求职雷达_总表.csv`（UTF-8 BOM，双击 Excel 打开），新岗位排在最前面。

## 文件说明

```
radar.py             # 抓取引擎，一般不需要改
config_base.py       # 公共配置：黑白名单关键词、系统参数
config_global.py     # 海外/全球公司列表（当前使用中）
config_cn.py         # 中国大陆公司列表（预留，空）
```

`radar.py` 第 33 行 `env = 'global'` 决定加载哪个配置。切换国内版改为 `'cn'`。

## 如何添加新公司

编辑 `config_global.py`（或 `config_cn.py`），在 `TARGET_COMPANIES` 列表里加一个字典：

```python
{
    "name": "公司名",                          # 必填，会出现在 CSV 里
    "url": "https://...",                     # 必填，带筛选条件的职位列表页 URL
    "selector": "a.xxx",                      # 必填，岗位链接的 CSS 选择器
    "domain_prefix": "https://company.com",   # 必填，补全相对链接用，无则 ""
}
```

**步骤**：
1. 浏览器打开目标官网，手动筛选好地点和级别
2. 复制 URL → 填 `url`
3. F12 → Ctrl+Shift+C 点岗位标题 → 找到唯一 CSS 特征 → 填 `selector`
4. 跑一次 `python radar.py`，看日志验证

### 常见可选字段

遇到以下情况时添加对应字段：

| 场景 | 字段 | 示例 |
|------|------|------|
| `<a>` 标签里没有文字（Oracle HCM） | `extract_title` | `"el => { const li = el.closest('li'); return li?.querySelector('.job-tile__title')?.textContent?.trim() \|\| ''; }"` |
| 页面有"加载更多"按钮 | `next_button_selector` | `"a#showMoreJobs"`（Taleo 系统） |
| 需要按城市过滤 | `extract_location` | `"el => { const c = el.closest('.liner'); return c?.querySelector('.position3')?.textContent?.trim() \|\| ''; }"` |
| 分组标签 | `category` | `"Bulge Bracket"` |
| 页面加载慢 | `selector_timeout` | `40000`（毫秒，默认 20000） |

## 黑白名单

编辑 `config_base.py`：

- **`EXCLUDE_KEYWORDS`**：命中任一 → 丢弃（senior、vp、director 等）
- **`INCLUDE_KEYWORDS`**：非空时，必须命中至少一个才保留（intern、graduate、2027 等）

不区分大小写，英文用单词边界匹配（`intern` 不会误命中 `international`）。

## 运行逻辑

`radar.py` 启动 → 加载配置 → 打开无头 Chromium → 逐家公司：

1. 打开 URL（失败重试 3 次）
2. 自动点掉 Cookie 弹窗（Accept All / Usercentrics / 等 13 种）
3. 等岗位卡片出现 → 等 networkidle
4. 滚动到底部 → 点"加载更多"/"Next" → 循环直到数量不再增长
5. 提取每个卡片的标题 + 链接 + 地点 → 黑白名单过滤 → 数据库去重
6. 输出 CSV

## 输出示例

| 分类 | 状态 | 公司 | 职位 | 申请链接 |
|------|------|------|------|----------|
| Bulge Bracket | [新岗位] | 高盛 (Goldman Sachs) | 2027 Summer Analyst | https://... |
| Bulge Bracket | [历史] | 摩根大通 (JPMorgan Chase) - 香港 | IB Analyst | https://... |
| Bulge Bracket | 未开放 | 花旗银行 (Citi) - 中国大陆 | | |
