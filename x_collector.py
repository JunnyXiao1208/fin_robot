# -*- coding: utf-8 -*-
import hashlib
import json
import logging
import os
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

from ai import extract_market_signal
from configs.source_profiles import attach_source_category
from rss import (
    DB_PATH,
    SCRIPT_DIR,
    init_rss_db,
    save_raw_item,
    save_market_signal,
    update_sync_state,
)

load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

X_TRACKED_USERS: list[dict[str, Any]] = json.loads(
    os.getenv("X_TRACKED_USERS", "[]")
)

PROXY = os.getenv("HTTPS_PROXY", os.getenv("HTTP_PROXY", "")).strip()
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
BEARER = "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

USER_BY_SCREEN_NAME_QID = "IGgvgiOx4QZndDHuD3x9TQ"
USER_TWEETS_QID = "lrMzG9qPQHpqJdP3AbM-bQ"

USER_FEATURES = {
    "hidden_profile_subscriptions_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "subscriptions_verification_info_is_identity_verified_enabled": True,
    "subscriptions_verification_info_verified_since_enabled": True,
    "highlights_tweets_tab_ui_enabled": True,
    "responsive_web_twitter_article_notes_tab_enabled": True,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
}

TWEET_FEATURES = {
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
}

API_BASE = "https://x.com/i/api/graphql"


def detect_language(text: str) -> str:
    if not text:
        return "unknown"
    if re.search(r'[\u4e00-\u9fff]', text):
        return "zh"
    if re.search(r'[A-Za-z]', text):
        return "en"
    return "unknown"


def build_content_hash(source_type: str, source_name: str, content: str) -> str:
    payload = f"{source_type}|{source_name}|{content.strip()[:500]}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_session() -> requests.Session:
    auth_token = os.getenv("X_AUTH_TOKEN", "").strip()
    if not auth_token:
        logger.warning("X_AUTH_TOKEN 未配置")
        return None

    s = requests.Session()
    if PROXY:
        s.proxies.update({"https": PROXY, "http": PROXY})
    s.headers.update({"User-Agent": UA})
    s.cookies.set("auth_token", auth_token, domain=".x.com")

    r = s.get("https://x.com", timeout=30)
    if r.status_code != 200:
        logger.error(f"获取 x.com 失败: {r.status_code}")
        return None

    ct0 = s.cookies.get("ct0", domain=".x.com")
    if not ct0:
        logger.error("获取 ct0 失败")
        return None

    s.headers.update({
        "Authorization": BEARER,
        "x-csrf-token": ct0,
        "Content-Type": "application/json",
    })
    return s


def _get_user_id(session: requests.Session, screen_name: str) -> str | None:
    variables = json.dumps({
        "screen_name": screen_name,
        "withSafetyModeUserFields": True,
    })
    features = json.dumps(USER_FEATURES)

    try:
        r = session.get(
            f"{API_BASE}/{USER_BY_SCREEN_NAME_QID}/UserByScreenName",
            params={"variables": variables, "features": features},
            timeout=30,
        )
        if r.status_code != 200:
            logger.warning(f"  @{screen_name}: UserByScreenName {r.status_code}")
            return None
        data = r.json()
        result = data.get("data", {}).get("user", {}).get("result", {})
        user_id = result.get("rest_id", "")
        if user_id:
            return user_id
        logger.warning(f"  @{screen_name}: 无法获取 user_id")
        return None
    except Exception as e:
        logger.warning(f"  @{screen_name}: getUserID 异常: {e}")
        return None


def _get_user_tweets(session: requests.Session, user_id: str, count: int = 5) -> list[dict]:
    variables = json.dumps({
        "userId": user_id, "count": count,
        "includePromotedContent": True,
        "withQuickPromoteEligibilityTweetFields": True,
        "withVoice": True, "withV2Timeline": True,
    })
    features = json.dumps(TWEET_FEATURES)

    try:
        r = session.get(
            f"{API_BASE}/{USER_TWEETS_QID}/UserTweets",
            params={"variables": variables, "features": features},
            timeout=30,
        )
        if r.status_code != 200:
            logger.warning(f"  UserTweets: {r.status_code}")
            return []
        data = r.json()
        user_result = data.get("data", {}).get("user", {}).get("result", {})
        if not user_result:
            logger.warning(f"  UserTweets: no user result")
            return []
        if "timeline" not in user_result:
            logger.warning(f"  UserTweets: no timeline")
            return []
        instructions = (user_result
                        .get("timeline", {}).get("timeline", {}).get("instructions", []))

        tweets = []
        for inst in instructions:
            for entry in inst.get("entries", []):
                entry_id = entry.get("entryId", "")
                if not entry_id.startswith("tweet-"):
                    continue
                item = entry.get("content", {}).get("itemContent", {})
                tweet_result = item.get("tweet_results", {}).get("result", {})
                if not tweet_result:
                    continue
                legacy = tweet_result.get("legacy", {})
                if not legacy:
                    continue
                tweets.append(legacy)
        return tweets
    except Exception as e:
        logger.warning(f"  UserTweets 异常: {e}")
        return []


def collect_x_raw_items(count_per_user: int = 5) -> list[dict[str, Any]]:
    if not X_TRACKED_USERS:
        logger.warning("X_TRACKED_USERS 未配置，跳过 X 采集")
        return []

    session = _build_session()
    if not session:
        logger.warning("X 会话初始化失败，跳过")
        return []

    all_items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for user_cfg in X_TRACKED_USERS:
        screen_name = str(user_cfg.get("user", "")).strip()
        if not screen_name:
            continue

        logger.info(f"@{screen_name}: 查询用户信息...")
        user_id = _get_user_id(session, screen_name)
        if not user_id:
            continue

        logger.info(f"  user_id={user_id}, 拉取推文...")
        tweets = _get_user_tweets(session, user_id, count=count_per_user)
        if not tweets:
            continue
        logger.info(f"  {len(tweets)} 条推文")

        weight = float(user_cfg.get("weight", 0.0))
        tags = user_cfg.get("tags", [])

        for tweet in tweets:
            tweet_id = tweet.get("id_str", "")
            if tweet_id in seen_ids:
                continue
            seen_ids.add(tweet_id)

            content = (tweet.get("full_text", "") or "").strip()
            if not content:
                continue

            content_hash = build_content_hash("x", screen_name, content)
            language = detect_language(content)

            item = {
                "item_id": str(uuid.uuid4()),
                "source_type": "x",
                "source_name": screen_name,
                "source_id": screen_name,
                "external_id": tweet_id,
                "author": screen_name,
                "title": "",
                "content": content[:2000],
                "url": f"https://x.com/{screen_name}/status/{tweet_id}",
                "published_at": tweet.get("created_at", ""),
                "language": language,
                "content_hash": content_hash,
                "metadata": {
                    "retweet_count": tweet.get("retweet_count", 0),
                    "favorite_count": tweet.get("favorite_count", 0),
                    "reply_count": tweet.get("reply_count", 0),
                    "is_retweet": bool(tweet.get("retweeted_status")),
                    "weight": weight,
                    "tags": tags,
                },
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            attach_source_category(item)
            all_items.append(item)

        time.sleep(3)

    logger.info(f"本轮 X 共得到 {len(all_items)} 条推文")
    return all_items


async def ingest_x_items(count_per_user: int = 5) -> dict[str, int]:
    init_rss_db()
    raw_items = collect_x_raw_items(count_per_user=count_per_user)
    if not raw_items:
        return {"fetched": 0, "saved": 0, "signals": 0, "skipped": 0}

    stats = {"fetched": len(raw_items), "saved": 0, "signals": 0, "skipped": 0}
    conn = sqlite3.connect(DB_PATH)
    try:
        for raw_item in raw_items:
            saved = save_raw_item(conn, raw_item)
            if not saved:
                stats["skipped"] += 1
                continue

            stats["saved"] += 1
            signal = await extract_market_signal(
                text=raw_item["content"],
                source_type="x",
                author=raw_item["author"],
            )
            save_market_signal(conn, raw_item, signal)
            stats["signals"] += 1

        update_sync_state(conn, source_key="x:default", status="ok", last_cursor=str(stats["saved"]))
        conn.commit()
        logger.info(f"X 闭环完成: {stats}")
        return stats
    except Exception as e:
        conn.rollback()
        update_sync_state(conn, source_key="x:default", status="error", error_message=str(e)[:300])
        conn.commit()
        logger.error(f"X 入库流程失败: {e}")
        raise
    finally:
        conn.close()
