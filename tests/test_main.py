# tests/test_main.py
import pytest
import sys, os

# 念のため、このファイルがあるディレクトリからみたルートパスを追加
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from fetch_data import fetch_post_and_top_comments
from translate import translate_to_casual_japanese

def test_translation_flow():
    """
    fetch_data で取得したタイトルとコメントを翻訳し、
    ちゃんと結果が得られるかを簡易チェックするテスト。
    """

    # テスト用に特定のURLを用意
    test_url = "https://www.reddit.com/r/PTCGP/comments/1j1ee36/a_buy_all_button_would_be_nice/"
    
    # まず fetch_data で投稿データを取得
    post_data = fetch_post_and_top_comments(test_url, comment_limit=3)
    # 例としてコメント3件だけ取得

    # タイトル翻訳を試す
    original_title = post_data["title"]
    translated_title = translate_to_casual_japanese(original_title)
    
    # タイトルが空でなければ翻訳後も何かしら文字が返るはず
    assert len(translated_title) > 0, "Translated title should not be empty."

    # コメントを翻訳
    comments = post_data["comments"]
    for c in comments:
        original_body = c["body"]
        translated_body = translate_to_casual_japanese(original_body)
        # 簡易アサーション: 何かしらの訳文が得られる
        assert len(translated_body) > 0, f"Comment by {c['author']} failed to translate properly"

    print("Test passed: fetch -> translate flow is working")
