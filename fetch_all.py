
# fetch_all.py
import os
import re
from typing import List, Dict, Any
from dotenv import load_dotenv
import praw

from fetch_data import has_image_link_in_body  # reuse existing helper

AD_KEYWORDS = [
    r"\b(sponso?red?|affiliate)\b",
    r"\b(discount|promo|coupon|deal)\b",
    r"\b(ref(erral)?\s*code)\b",
    r"\b(shop|store|merch)\b",
]

def looks_like_ad(text: str) -> bool:
    """
    ごく簡易な広告/アフィ判定（誤検知を避けるため弱め）
    """
    t = text.lower()
    if "http" in t and ("ref" in t or "coupon" in t or "promo" in t):
        return True
    for pat in AD_KEYWORDS:
        if re.search(pat, t, flags=re.IGNORECASE):
            return True
    return False

def fetch_post_threads(post_url: str, max_threads: int = 50, max_replies_per_thread: int = 50) -> Dict[str, Any]:
    """
    指定Reddit投稿の「トップレベルコメント＋その返信」をスレッド単位で取得する。
    - AutoModerator、[removed]/[deleted]は除外
    - 画像リンクを含むコメントを除外
    - 広告っぽい文面を除外（簡易）
    - 各スレッドで返信は score の高いものから max_replies_per_thread 件まで
    戻り値:
      {
        "title": str,
        "permalink": str,
        "threads": [
           {
             "top": {...},
             "replies": [{...}, ...],
             "score": float  # 代表スコア
           },
           ...
        ]
      }
    """
    load_dotenv()
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT", "PokePokeScraper/2.0")
    )
    submission = reddit.submission(url=post_url)
    submission.comment_sort = "top"
    submission.comments.replace_more(limit=None)  # 返信まで完全展開

    def valid_comment(c) -> bool:
        if c is None: return False
        if c.author and c.author.name == "AutoModerator": return False
        body = (c.body or "").strip()
        if not body or body in ("[deleted]", "[removed]"): return False
        if has_image_link_in_body(body): return False
        if looks_like_ad(body): return False
        return True

    # トップレベルコメントを収集（score順）
    top_level = [c for c in submission.comments if valid_comment(c)]
    top_level.sort(key=lambda x: getattr(x, "score", 0), reverse=True)
    top_level = top_level[:max_threads]

    threads = []
    for top in top_level:
        # 返信を平坦化してスコア順に切り出す
        replies = [r for r in top.replies.list() if valid_comment(r)]
        replies.sort(key=lambda x: getattr(x, "score", 0), reverse=True)
        replies = replies[:max_replies_per_thread]

        def to_obj(c):
            author_name = c.author.name if c.author else "[deleted]"
            return {
                "id": c.id,
                "author": author_name,
                "body": (c.body or "").strip(),
                "score": getattr(c, "score", 0),
                "created_utc": getattr(c, "created_utc", None),
                "permalink": f"https://www.reddit.com{getattr(c, 'permalink', '')}"
            }

        top_obj = to_obj(top)
        replies_obj = [to_obj(r) for r in replies]

        # 代表スコア: トップのscore + 返信上位5件の合計 * 0.5 + 返信数 * 0.3
        replies_top5 = sorted(replies_obj, key=lambda x: x["score"], reverse=True)[:5]
        score = top_obj["score"] + 0.5 * sum(r["score"] for r in replies_top5) + 0.3 * len(replies_obj)

        threads.append({
            "top": top_obj,
            "replies": replies_obj,
            "score": score
        })

    # 返信のない高スコア単発も活かせるようスコア順に並べる
    threads.sort(key=lambda x: x["score"], reverse=True)

    return {
        "title": submission.title,
        "permalink": f"https://www.reddit.com{submission.permalink}",
        "threads": threads
    }
