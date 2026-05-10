# -*- coding: utf-8 -*-
import json
import logging
import os
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

DEFAULT_RSS_FEEDS = [
    {"name": "36kr", "url": "https://36kr.com/feed"},
    {"name": "tmtpost", "url": "https://www.tmtpost.com/rss.xml"},
    {"name": "bbc_business", "url": "https://feeds.bbci.co.uk/news/business/rss.xml"},
    {"name": "cnbc_finance", "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html"},
    {"name": "wsj_markets", "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"},
    {"name": "marketwatch_top", "url": "https://feeds.marketwatch.com/marketwatch/topstories/"},
    {"name": "techcrunch", "url": "https://techcrunch.com/feed/"},
]

TARGET_KEYWORDS = [
    "央行", "降息", "降准", "LPR", "美联储", "鲍威尔", "加息", "缩表", "财政部", "国债",
    "大盘", "沪深300", "纳指", "标普", "ETF", "中概股", "权重股", "成分股", "北向资金", "外资",
    "人工智能", "AI", "OpenAI", "英伟达", "Nvidia", "半导体", "芯片", "算力", "大模型",
    "新能源", "固态电池", "低空经济", "数字化转型",
    "CPI", "PPI", "GDP", "非农", "失业率", "财报", "营收", "净利润", "分红", "回购",
    "消费复苏", "零售", "房地产", "白酒", "医药",
]


def load_feeds() -> list[dict]:
    feeds_json = os.getenv("RSS_FEEDS_JSON", "").strip()
    if not feeds_json:
        return DEFAULT_RSS_FEEDS
    try:
        feeds = json.loads(feeds_json)
        valid = []
        for item in feeds:
            url = str(item.get("url", "")).strip()
            if not url:
                continue
            valid.append({
                "name": str(item.get("name", urlparse(url).netloc)).strip(),
                "url": url,
            })
        return valid or DEFAULT_RSS_FEEDS
    except json.JSONDecodeError:
        logger.warning("RSS_FEEDS_JSON 格式错误，使用默认源")
        return DEFAULT_RSS_FEEDS


def should_keep(title: str, content: str, keyword_filter: bool = True) -> bool:
    if not keyword_filter:
        return True
    text = f"{title}\n{content}"
    return any(kw.lower() in text.lower() for kw in TARGET_KEYWORDS)
