# translate.py

import os
from dotenv import load_dotenv
import openai

# .env をロード
load_dotenv()

# OpenAI API の設定
openai.api_key = os.getenv("OPENAI_API_KEY")

# 新しいクライアントインスタンスを作成
client = openai.Client()


def translate_to_casual_japanese(text: str) -> str:
    """
    英語の text を gpt-4-turbo で「フランクな友達との雑談風」日本語に翻訳して返す。
    """
    if not text.strip():
        return ""

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a translator that translates English text into Japanese. "
                        "No polite or formal speech is allowed. Use a friendly, colloquial tone, "
                        "as if talking to a close friend. Keep it concise and natural."
                    )
                },
                {
                    "role": "user",
                    "content": f"Translate this into casual Japanese:\n\n{text}"
                }
            ],
            temperature=0.7,
            max_tokens=300
        )
        translated = response.choices[0].message.content.strip()
        return translated

    except Exception as e:
        print(f"Translation error: {e}")
        return ""
