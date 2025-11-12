import os
import re
from dotenv import load_dotenv
import praw

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp")

def contains_image_extension(url: str) -> bool:
    """
    URLの中に .jpg, .png 等の画像拡張子が含まれていれば True
    (末尾だけでなくクエリ文字列などに埋まっていても含む)
    """
    lower = url.lower()
    for ext in IMAGE_EXTENSIONS:
        if ext in lower:
            return True
    return False

def has_image_link_in_body(text: str) -> bool:
    """
    コメント本文中に画像拡張子が含まれるURLがあるかを簡易判定する。
    URLらしき文字列をすべて抽出し、そのいずれかに画像拡張子があれば True
    """
    pattern = r'(https?://[^\s]+)'
    urls = re.findall(pattern, text)
    for u in urls:
        if contains_image_extension(u):
            return True
    return False

def fetch_post_and_top_comments(post_url: str, comment_limit=10):
    """
    指定したReddit投稿URLから、タイトルおよび
    「トップレベルコメント(TOPソート順)」を取得して返す。

    条件:
      - AutoModeratorのコメントは除外
      - 画像リンクを含むコメントも除外
      - 上から comment_limit 件まで取得（返信コメントは含めない）

    戻り値:
      {
        "title": "投稿タイトル",
        "comments": [
          {"id": "..", "body": "...", "author": "..."},
          ...
        ]
      }
    """

    # 1) .env読み込み
    load_dotenv()

    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "PokePokeScraper/1.0")

    # 2) praw設定
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent
    )

    # 3) Submissionオブジェクト取得
    submission = reddit.submission(url=post_url)
    # 4) トップソート順でコメントを取得
    submission.comment_sort = "top"
    submission.comments.replace_more(limit=0)  # "load more..."を排除、全コメント展開

    # 5) トップレベルコメントをフィルタしながら収集
    collected = []
    for c in submission.comments:
        # AutoModerator除外
        if c.author and c.author.name == "AutoModerator":
            continue
        # 画像リンク含むコメントは除外
        if has_image_link_in_body(c.body):
            continue

        author_name = c.author.name if c.author else "[deleted]"
        collected.append({
            "id": c.id,
            "body": c.body.strip(),
            "author": author_name
        })

        # 必要件数に達したら打ち切り
        if len(collected) >= comment_limit:
            break

    return {
        "title": submission.title,
        "comments": collected
    }


# 動作確認用(サンプルURL)
if __name__ == "__main__":
    test_url = "https://www.reddit.com/r/PTCGP/comments/1orpru1/favorite_oldest_meta/"
    data = fetch_post_and_top_comments(test_url, comment_limit=10)

    print("Title:", data["title"])
    print("---")
    print("Top-level Comments (top sort):")
    for i, com in enumerate(data["comments"], 1):
        print(f"{i}. [{com['author']}] {com['body'][:80]}...")
