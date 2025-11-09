# src/subtitle.py

import os
from PIL import Image, ImageDraw, ImageFont

def generate_subtitle_images(text_segments, output_filename="subtitle.png"):
    """
    テキストを単純に1枚の画像に書き出す。複数テキストがある場合は連続で書き込むイメージ。
    本来は音声のタイミングごとに画像を切り替える実装が望ましい。
    """

    if not text_segments:
        return None

    output_folder = os.path.join("data", "processed", "subtitles")
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, output_filename)

    # 画像のベースサイズ
    width, height = 1280, 720
    background_color = (0, 0, 0)  # 黒背景
    font_size = 40
    font_color = (255, 255, 255)  # 白文字

    # フォントのパスは環境に合わせて指定
    # Windows例: C:\Windows\Fonts\meiryo.ttc
    font_path = "C:/Windows/Fonts/meiryo.ttc"

    # 画像生成
    img = Image.new('RGB', (width, height), background_color)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, font_size)

    # テキストを連結
    text_to_draw = "\n".join(text_segments)

    # テキスト描画時のX,Yの開始位置(中央寄せの例: xは後で計算)
    y_position = height // 2

    # テキストの幅を取得（中央揃え用）
    text_w, text_h = draw.multiline_textsize(text_to_draw, font=font)
    x_position = (width - text_w) // 2

    # テキスト描画（中央揃え）
    draw.multiline_text((x_position, y_position), text_to_draw, font=font, fill=font_color, align="center")

    # 画像保存
    img.save(output_path)
    print(f"[Subtitle] Generated image: {output_path}")

    return output_path
