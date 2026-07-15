from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests


QUERY_ID = "-4_LMahNlI4MuLJ-EAFEog"
OPERATION = "TweetResultByRestId"

FEATURES = [
    "creator_subscriptions_tweet_preview_api_enabled",
    "premium_content_api_read_enabled",
    "communities_web_enable_tweet_community_results_fetch",
    "c9s_tweet_anatomy_moderator_badge_enabled",
    "responsive_web_grok_analyze_button_fetch_trends_enabled",
    "responsive_web_grok_analyze_post_followups_enabled",
    "rweb_cashtags_composer_attachment_enabled",
    "responsive_web_jetfuel_frame",
    "responsive_web_grok_share_attachment_enabled",
    "responsive_web_grok_annotations_enabled",
    "articles_preview_enabled",
    "responsive_web_edit_tweet_api_enabled",
    "rweb_conversational_replies_downvote_enabled",
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled",
    "view_counts_everywhere_api_enabled",
    "longform_notetweets_consumption_enabled",
    "responsive_web_twitter_article_tweet_consumption_enabled",
    "content_disclosure_indicator_enabled",
    "content_disclosure_ai_generated_indicator_enabled",
    "responsive_web_grok_show_grok_translated_post",
    "responsive_web_grok_analysis_button_from_backend",
    "post_ctas_fetch_enabled",
    "freedom_of_speech_not_reach_fetch_enabled",
    "standardized_nudges_misinfo",
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled",
    "longform_notetweets_rich_text_read_enabled",
    "longform_notetweets_inline_media_enabled",
    "responsive_web_grok_image_annotation_enabled",
    "responsive_web_grok_imagine_annotation_enabled",
    "responsive_web_grok_community_note_auto_translation_is_enabled",
    "responsive_web_enhance_cards_enabled",
]

FIELD_TOGGLES = [
    "withArticleRichContentState",
    "withArticlePlainText",
    "withArticleSummaryText",
    "withArticleVoiceOver",
    "withGrokAnalyze",
    "withDisallowedReplyControls",
    "withPayments",
    "withAuxiliaryUserLabels",
]


def clean_filename(value: str) -> str:
    value = re.sub(r'[\\/:*?"<>|]', "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:100] or "twitter-article"


def extract_tweet_id(value: str) -> str:
    if re.fullmatch(r"\d+", value):
        return value
    match = re.search(r"/status/(\d+)", value)
    if not match:
        raise SystemExit(f"Cannot find tweet id in: {value}")
    return match.group(1)


def get_bearer_token(session: requests.Session) -> str:
    token = os.environ.get("X_GUEST_BEARER_TOKEN", "").strip()
    if token:
        return token

    response = session.get("https://x.com", headers={"user-agent": "Mozilla/5.0"}, timeout=30)
    response.raise_for_status()
    script_urls = re.findall(r'https://abs\.twimg\.com/responsive-web/client-web/[^"]+\.js', response.text)
    for script_url in script_urls:
        script = session.get(script_url, headers={"user-agent": "Mozilla/5.0"}, timeout=30)
        if not script.ok:
            continue
        match = re.search(r'Bearer ([A-Za-z0-9%_-]{80,})', script.text)
        if match:
            return match.group(1)

    raise RuntimeError("Cannot discover X bearer token. Set X_GUEST_BEARER_TOKEN and retry.")


def get_guest_token(session: requests.Session, bearer_token: str) -> str:
    response = session.post(
        "https://api.x.com/1.1/guest/activate.json",
        headers={"authorization": f"Bearer {bearer_token}", "user-agent": "Mozilla/5.0"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["guest_token"]


def fetch_article_json(tweet_id: str) -> dict:
    session = requests.Session()
    bearer_token = get_bearer_token(session)
    guest_token = get_guest_token(session, bearer_token)
    headers = {
        "authorization": f"Bearer {bearer_token}",
        "user-agent": "Mozilla/5.0",
        "x-guest-token": guest_token,
        "x-twitter-active-user": "yes",
        "x-twitter-client-language": "en",
    }
    query = urllib.parse.urlencode(
        {
            "variables": json.dumps(
                {
                    "tweetId": tweet_id,
                    "withCommunity": False,
                    "includePromotedContent": False,
                    "withVoice": False,
                },
                separators=(",", ":"),
            ),
            "features": json.dumps({name: True for name in FEATURES}, separators=(",", ":")),
            "fieldToggles": json.dumps({name: True for name in FIELD_TOGGLES}, separators=(",", ":")),
        }
    )
    response = session.get(f"https://x.com/i/api/graphql/{QUERY_ID}/{OPERATION}?{query}", headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def apply_bold(text: str, ranges: list[dict]) -> str:
    for row in sorted(ranges or [], key=lambda item: item.get("offset", 0), reverse=True):
        if row.get("style") != "Bold":
            continue
        start = row.get("offset", 0)
        end = start + row.get("length", 0)
        if 0 <= start < end <= len(text):
            text = text[:start] + "**" + text[start:end] + "**" + text[end:]
    return text


def media_urls(article: dict) -> dict[str, str]:
    result = {}
    cover = article.get("cover_media")
    if cover:
        result[str(cover.get("media_id"))] = cover.get("media_info", {}).get("original_img_url", "")
    for media in article.get("media_entities", []):
        result[str(media.get("media_id"))] = media.get("media_info", {}).get("original_img_url", "")
    return result


def local_media(downloads: Path, tweet_id: str) -> dict[str, Path]:
    gallery_json = downloads / f"{tweet_id}_gallery.json"
    if not gallery_json.exists():
        return {}
    gallery = json.loads(gallery_json.read_text(encoding="utf-8"))
    result = {}
    for item in gallery:
        if not (isinstance(item, list) and len(item) >= 3 and item[0] == 3):
            continue
        media_id = str(item[2].get("media_id", ""))
        num = item[2].get("num")
        matches = sorted(downloads.glob(f"{tweet_id}_{num}.*")) if num else []
        if media_id and matches:
            result[media_id] = matches[0]
    return result


def gallery_metadata(downloads: Path, tweet_id: str) -> dict:
    gallery_json = downloads / f"{tweet_id}_gallery.json"
    if not gallery_json.exists():
        return {}
    gallery = json.loads(gallery_json.read_text(encoding="utf-8"))
    if gallery and isinstance(gallery[0], list) and len(gallery[0]) >= 2 and isinstance(gallery[0][1], dict):
        return gallery[0][1]
    return {}


def interaction_counts(result: dict, gallery_meta: dict) -> dict:
    legacy = result.get("legacy", {})
    return {
        "likes": gallery_meta.get("favorite_count", legacy.get("favorite_count", "")),
        "retweets": gallery_meta.get("retweet_count", legacy.get("retweet_count", "")),
        "replies": gallery_meta.get("reply_count", legacy.get("reply_count", "")),
        "quotes": gallery_meta.get("quote_count", legacy.get("quote_count", "")),
        "views": gallery_meta.get("view_count", legacy.get("view_count", "")),
        "bookmarks": gallery_meta.get("bookmark_count", legacy.get("bookmark_count", "")),
    }


def interaction_table(counts: dict) -> list[str]:
    return [
        "## 原帖数据",
        "",
        "| 指标 | 数量 |",
        "|---|---:|",
        f"| 点赞 | {counts['likes']} |",
        f"| 转发 | {counts['retweets']} |",
        f"| 回复 | {counts['replies']} |",
        f"| 引用 | {counts['quotes']} |",
        f"| 浏览 | {counts['views']} |",
        f"| 收藏 | {counts['bookmarks']} |",
        "",
    ]


def make_asset(media_id: str, label: str, state: dict) -> str:
    if media_id in state["asset_paths"]:
        return state["asset_paths"][media_id]
    src = state["local_media"].get(media_id)
    if src and src.exists():
        index = len(state["asset_paths"]) + 1
        target = state["assets"] / f"{index:02d}-{label}{src.suffix.lower()}"
        shutil.copy2(src, target)
        path = f"{state['assets'].name}/{target.name}"
    else:
        path = state["remote_media"].get(media_id, "")
    state["asset_paths"][media_id] = path
    return path


def write_markdown(data: dict, url: str, root: Path) -> Path:
    tweet_id = extract_tweet_id(url)
    result = data["data"]["tweetResult"]["result"]
    article = result["article"]["article_results"]["result"]
    title = article["title"]
    article_id = article.get("rest_id", "")

    output = root / "markdown"
    downloads = root / "downloads"
    output.mkdir(parents=True, exist_ok=True)
    slug = clean_filename(title)
    md_path = output / f"{slug}-{tweet_id}.md"
    assets = output / f"{slug}-{tweet_id}.assets"
    assets.mkdir(parents=True, exist_ok=True)

    user = result.get("core", {}).get("user_results", {}).get("result", {})
    legacy = user.get("legacy", {})
    gallery_meta = gallery_metadata(downloads, tweet_id)
    username = legacy.get("screen_name") or gallery_meta.get("user", {}).get("name") or gallery_meta.get("author", {}).get("name") or "unknown"
    author = legacy.get("name") or gallery_meta.get("user", {}).get("nick") or gallery_meta.get("author", {}).get("nick") or username
    counts = interaction_counts(result, gallery_meta)

    state = {
        "assets": assets,
        "asset_paths": {},
        "local_media": local_media(downloads, tweet_id),
        "remote_media": media_urls(article),
    }
    entities = {str(item.get("key")): item.get("value", {}) for item in article["content_state"].get("entityMap", [])}

    lines = [
        "---",
        f'title: "{title.replace(chr(34), chr(39))}"',
        f'url: "{url}"',
        f'article_url: "http://x.com/i/article/{article_id}"',
        f'author: "{author} (@{username})"',
        f'tweet_id: "{tweet_id}"',
        f'article_id: "{article_id}"',
        f"likes: {counts['likes']}",
        f"retweets: {counts['retweets']}",
        f"replies: {counts['replies']}",
        f"quotes: {counts['quotes']}",
        f"views: {counts['views']}",
        f"bookmarks: {counts['bookmarks']}",
        f'converted_at: "{datetime.now().isoformat(timespec="seconds")}"',
        "---",
        "",
        f"# {title}",
        "",
        f"作者：{author} (@{username})",
        "",
        f"原帖：{url}",
        "",
        f"Article：http://x.com/i/article/{article_id}",
        "",
    ]
    lines.extend(interaction_table(counts))

    cover = article.get("cover_media")
    if cover and cover.get("media_id"):
        rel = make_asset(str(cover["media_id"]), "cover", state)
        if rel:
            lines.extend([f"![cover]({rel})", ""])

    for block in article["content_state"]["blocks"]:
        block_type = block.get("type")
        text = block.get("text", "")
        if block_type == "atomic":
            inserted = False
            for item in block.get("entityRanges") or []:
                entity = entities.get(str(item.get("key")), {})
                if entity.get("type") == "MEDIA":
                    for media in entity.get("data", {}).get("mediaItems", []):
                        rel = make_asset(str(media.get("mediaId")), "image", state)
                        if rel:
                            lines.extend([f"![]({rel})", ""])
                            inserted = True
                elif entity.get("type") == "TWEMOJI":
                    emoji = entity.get("data", {}).get("url")
                    if emoji:
                        lines.extend([f"![]({emoji})", ""])
                        inserted = True
                elif entity.get("type") == "MARKDOWN":
                    markdown = entity.get("data", {}).get("markdown", "").strip()
                    if markdown:
                        lines.extend([markdown, ""])
                        inserted = True
            if inserted:
                continue

        text = apply_bold(text, block.get("inlineStyleRanges") or [])
        if not text.strip():
            lines.append("")
        elif block_type == "header-one":
            lines.extend([f"# {text.strip().strip('*')}", ""])
        elif block_type == "header-two":
            lines.extend([f"## {text.strip().strip('*')}", ""])
        elif block_type == "header-three":
            lines.extend([f"### {text.strip().strip('*')}", ""])
        elif block_type == "unordered-list-item":
            lines.append(f"- {text.strip()}")
        elif block_type == "ordered-list-item":
            lines.append(f"1. {text.strip()}")
        else:
            lines.extend([text.strip(), ""])

    markdown = "\n".join(lines)
    markdown = re.sub(r"\n{4,}", "\n\n\n", markdown).strip() + "\n"
    md_path.write_text(markdown, encoding="utf-8")
    return md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch an X/Twitter Article via GraphQL and save it as Markdown.")
    parser.add_argument("url", help="X/Twitter status URL or tweet id.")
    parser.add_argument("--root", type=Path, default=Path.home() / "Desktop" / "twitter-cli")
    parser.add_argument("--save-json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tweet_id = extract_tweet_id(args.url)
    downloads = args.root / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    data = fetch_article_json(tweet_id)
    if args.save_json:
        (downloads / f"{tweet_id}_tweetresult.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(write_markdown(data, args.url, args.root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
