# main.py

import os
import random
from fetch_data import fetch_post_and_top_comments
from translate import translate_to_casual_japanese
from tts import generate_tts, POSTER_VOICE, COMMENT_VOICES

def main():
    # 1) Reddit投稿URLを指定
    url = "https://www.reddit.com/r/PTCGP/comments/1orpru1/favorite_oldest_meta/"

    # 2) データ取得（タイトル & コメント10件）
    post_data = fetch_post_and_top_comments(url, comment_limit=10)
    original_title = post_data["title"]
    comments = post_data["comments"]

    # 3) タイトルの翻訳
    translated_title = translate_to_casual_japanese(original_title)

    print("=== Original Title ===")
    print(original_title)
    print("\n=== Translated Title ===")
    print(translated_title)

    # 4) タイトルを音声ファイルにする (投稿者の声)
    os.makedirs("data/tts", exist_ok=True)  # 出力フォルダを確保
    title_audio_path = os.path.join("data", "tts", "title.mp3")
    generate_tts(translated_title, POSTER_VOICE, title_audio_path)

    # 5) コメントを英語→日本語翻訳し、音声化
    for i, c in enumerate(comments, start=1):
        original_body = c["body"].strip()
        translated_body = translate_to_casual_japanese(original_body)

        # (a) コンソール表示（英語／日本語）
        print(f"\n=== Comment #{i} by {c['author']} ===")
        print("Original:", original_body)
        print("Translated:", translated_body)

        # (b) TTS音声ファイル作成（ランダムな声）
        if translated_body:
            random_voice = random.choice(COMMENT_VOICES)
            comment_audio_path = os.path.join("data", "tts", f"comment_{i}.mp3")
            generate_tts(translated_body, random_voice, comment_audio_path)

    print("\n=== Done! ===")
    print("音声ファイルは data/tts/ に保存されました。")


if __name__ == "__main__":
    main()
