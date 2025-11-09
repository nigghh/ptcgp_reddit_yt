# tts.py
import openai
import os
import random

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.Client(api_key=OPENAI_API_KEY)

# 投稿者 & コメントごとの voice を定義
POSTER_VOICE = "alloy"  # 投稿者は落ち着いたナレーション風
COMMENT_VOICES = ["nova", "onyx", "shimmer", "fable"]  # コメントはランダムな声を使用

def generate_tts(text: str, voice: str, filename: str):
    """
    text を指定の voice で音声ファイル(filename)に出力する。
    OpenAIの音声合成API (client.audio.speech.create) を想定。
    """
    if not text.strip():
        print("⚠️ テキストが空のためTTSをスキップします。")
        return

    response = client.audio.speech.create(
        model="tts-1-hd",
        voice=voice,
        input=text
    )
    with open(filename, "wb") as f:
        f.write(response.content)

    print(f"✅ 音声ファイル作成: {filename} (voice='{voice}')")
