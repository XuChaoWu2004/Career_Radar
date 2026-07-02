"""
Career Radar 全球/海外岗位配置
运行方式: python radar.py -e global
"""
from config_base import *

# =========================================================================================
# 🎯 【配置区 2】：目标公司名单 —— 全球/海外
#
# 新增公司步骤：
# 1. 用浏览器打开目标官网，手动选好地点和岗位级别。
# 2. 复制浏览器上方的网址，填到 "url" 里。
# 3. 按 F12 用左上角"小鼠标"点一下岗位标题，找出独特的 CSS 特征，填到 "selector" 里。
# 4. 把大括号 {...} 复制一份，接在列表后面。
# =========================================================================================

TARGET_COMPANIES = [
# =========================================================================================
#     八大投行 Bulge Bracket
#     投递策略：上岸概率极低，学习切磋为主，多对自己的笔试面试做复盘，提高综合能力和面对HR的counter对策卡。通过率预期低于5%，中了比中彩票还牛逼。
# =========================================================================================
    {
        "name": "高盛 (Goldman Sachs)",
        "url": "https://higher.gs.com/campus?LOCATION=Hong%20Kong|Shanghai&page=1&sort=RELEVANCE",
        "selector": "a[href^='/roles/']",
        "domain_prefix": "https://higher.gs.com",
        "category": "Bulge Bracket"
    },
    {
        "name": "摩根大通 (JPMorgan Chase) - 香港",
        "url": "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs?location=Hong+Kong&locationId=300000000289330&locationLevel=country&mode=location",
        "selector": "a.job-grid-item__link",
        "domain_prefix": "",
        "extract_title": "el => { const li = el.closest('li'); if (!li) return ''; const titleEl = li.querySelector('.job-tile__title'); return titleEl?.textContent?.trim() || ''; }",
        "category": "Bulge Bracket"
    },
    {
        "name": "摩根大通 (JPMorgan Chase) - 上海",
        "url": "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs?location=Shanghai%2C+China&locationId=300000020278183&locationLevel=state&mode=location",
        "selector": "a.job-grid-item__link",
        "domain_prefix": "",
        "extract_title": "el => { const li = el.closest('li'); if (!li) return ''; const titleEl = li.querySelector('.job-tile__title'); return titleEl?.textContent?.trim() || ''; }",
        "category": "Bulge Bracket"
    },

    {
        "name": "摩根士丹利 (Morgan Stanley) - 全球/香港区",
        "url": "https://morganstanley.tal.net/vx/candidate/jobboard/vacancy/1/adv/?f_Item_Opportunity_13857_lk=748&ftq=Hong+Kong",
        "selector": "tr.search_res a.subject",
        "domain_prefix": "https://morganstanley.tal.net",
        "category": "Bulge Bracket"
    },
    {
        "name": "摩根士丹利中国 (Morgan Stanley China)",
        "url": "https://careers.morganstanley.com.cn/go/Students-&-Graduates/5466530/",
        "selector": "a.jobCardTitle",
        "domain_prefix": "https://careers.morganstanley.com.cn",
        "category": "Bulge Bracket"
    },
    {
        "name": "花旗银行 (Citi) - 中国大陆",
        "url": "https://jobs.citi.com/search-jobs/China/287/2/1814991/35/105/50/2",
        "selector": "li.sr-job-item a.sr-job-item__link",
        "domain_prefix": "https://jobs.citi.com",
        "category": "Bulge Bracket"
    },
    {
        "name": "花旗银行 (Citi) - 香港",
        "url": "https://jobs.citi.com/search-jobs/Hong%20Kong%20SAR/287/2/1819730/22x25/114x16667/50/2",
        "selector": "li.sr-job-item a.sr-job-item__link",
        "domain_prefix": "https://jobs.citi.com",
        "category": "Bulge Bracket"
    },
    {
        "name": "美银 (Bank of America) - 香港/中国",
        "url": "https://careers.bankofamerica.com/en-us/students/job-search?ref=search&start=0&rows=10&search=jobsByLocation&filters=programType%3DOff-cycle+internship%2CprogramType%3DSummer+internship&searchstring=Hong+Kong&searchstring=China",
        "selector": "div.job-search-results-listing__item a.job-search-tile__url",
        "domain_prefix": "https://careers.bankofamerica.com",
        "category": "Bulge Bracket"
    },
    {
        "name": "巴克莱 (Barclays) - 香港/中国",
        "url": "https://search.jobs.barclays/search-jobs/Hong%20Kong%20China/13015/2/1819730/22x25/114x16667/50/2",
        "selector": "a[href^='/job/']",
        "domain_prefix": "https://search.jobs.barclays",
        "category": "Bulge Bracket"
    },
    {
        "name": "瑞银 (UBS) - 香港/中国大陆",
        "url": "https://jobs.ubs.com/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25008&siteid=5131&PageType=searchResults&SearchType=linkquery&LinkID=15232#keyWordSearch=&locationSearch=Hong%20Kong%20SAR",
        "selector": "a.jobProperty.jobtitle",
        "domain_prefix": "https://jobs.ubs.com",
        "extract_location": "el => { const c = el.closest('.liner'); return c?.querySelector('.position3')?.textContent?.trim() || ''; }",
        "next_button_selector": "a#showMoreJobs",
        "category": "Bulge Bracket"
    },
    {
        "name": "德银 (Deutsche Bank) - 全球",
        "url": "https://careers.db.com/students-graduates/Search-Programmes/#/graduate/results/",
        "selector": "div.detail-entry a[href*='db.recsolu.com']",
        "domain_prefix": "https://db.recsolu.com",
        "extract_location": "el => { const div = el.querySelector('div'); return div?.textContent?.trim() || ''; }",
        "category": "Bulge Bracket"
    },
]
