# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Career Radar（求职雷达）is a personal job-scraping tool that monitors campus/early-career job listings from company career pages. It uses Playwright to scrape, filters by keyword whitelist/blacklist, deduplicates via SQLite, and outputs a single CSV for Excel.

## Commands

```bash
# Install dependency (only external package)
pip install playwright
playwright install chromium

# Run the scraper
python radar.py
```

No tests, no build step, no linting configured. This is a personal utility split into two files.

## Architecture

**`config.py`** — all user-editable configuration (the only file users should modify):
- `EXCLUDE_KEYWORDS` / `INCLUDE_KEYWORDS` — blacklist/whitelist for job titles
- `TARGET_COMPANIES` — list of dicts with `name`, `url`, `selector`, `domain_prefix`
- `DB_FILE`, `OUTPUT_CSV`, `MARKER_NEW`, `MARKER_OLD`, `MAX_RETRIES`, `RETRY_DELAY`
- `logging.basicConfig()` — log to console + `radar.log`

**`radar.py`** — core scraping engine (imports from config.py, should rarely be edited):
1. **`main()`** — opens SQLite + Playwright browser, iterates `TARGET_COMPANIES`, calls `fetch_company_jobs()` per company, writes `求职雷达_总表.csv`.
2. **`fetch_company_jobs()`** — navigates to a company's URL, waits for a CSS selector, extracts title+href from each matching element, filters via `is_target_job()`, deduplicates against SQLite (SHA-256 hash of company+title+url), returns matched jobs. Has 3-retry loop for page load failures. Uses batch `executemany()` + single `commit()` for DB writes. Has fallback title extraction for Oracle HCM sites where `<a>` tags are empty — climbs to parent `<li>` and queries `.job-tile__title`.
3. **`is_target_job()`** — checks title against `EXCLUDE_KEYWORDS` (reject on match) then `INCLUDE_KEYWORDS` (require at least one match if non-empty). Case-insensitive.
4. **`init_db()`** — creates `seen_jobs` table if absent (`job_hash TEXT PK`, `company`, `title`, `link`, `date_added`).

## Output

- Console + `radar.log` (logging to both, INFO level).
- `求职雷达_总表.csv` — UTF-8 BOM encoded for Excel, columns: `状态 (Status)` (`ToT` = new, `[---历史---]` = seen), `公司 (Company)`, `职位 (Title)`, `申请链接 (Link)`. New jobs sorted to top.

## Adding a new company

Edit `config.py` → `TARGET_COMPANIES` — copy the commented template, fill in the 4 fields found by manually inspecting the target career page with browser DevTools.

## Editing configuration vs core logic

- **配置修改**（加公司、调黑白名单、改参数）→ 只编辑 `config.py`
- **核心逻辑修改**（抓取策略、Fallback、CSV输出）→ 编辑 `radar.py`
