# video_maker.py
# - render_plan.json + TTS mp3 から MP4 を生成（下部固定字幕版）
# - MoviePy v2対応（v1フォールバック）
# - 音声を確実に載せる、字幕色ランダム、中央画像フックあり
# 実行: python video_maker.py
# 出力: ./output.mp4

import os, json, random
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# ---- MoviePy import (v2推奨, v1 fallback) ----
try:
    import moviepy as mp      # v2
    V2 = True
except Exception:
    import moviepy.editor as mp  # v1
    V2 = False

# ====== Config ======
W, H   = 1920, 1080
FPS    = 30
BG_COLOR   = (16, 16, 20)    # 背景
CARD_BG    = (28, 28, 36, 220)  # 下部帯 背景(半透明)
TEXT_STROKE = (0, 0, 0)         # 文字縁取り（黒）
TEXT_COLORS = [                 # ランダム候補（高彩度 + BGとコントラスト担保）
    (245,245,250),  # ほぼ白
    (255,208,0),
    (76, 175, 255),
    (86, 255, 162),
    (255,132,132),
    (255, 92, 184),
    (180, 140, 255),
]
ACCENT     = (50, 120, 255)  # タイトル帯
SCENE_TAIL = 0.30
TITLE_PAD  = 24

# 下部帯のレイアウト
CAPTION_SIDE_MARGIN  = 80
CAPTION_BOTTOM_MARGIN= 60
CAPTION_INNER_X      = 36
CAPTION_INNER_Y      = 24
LINE_GAP             = 18
MAX_CAPTION_WIDTH    = W - CAPTION_SIDE_MARGIN*2

# 中央画像エリア（上下に余白。下部は字幕に被らないよう広めに）
CENTER_TOP_MARGIN    = 120
CENTER_BOTTOM_MARGIN = 280   # 字幕帯の高さ想定ぶん余裕を取る

# 日本語フォント
FONT_PATH        = r"C:\Windows\Fonts\meiryo.ttc"
TITLE_FONT_SIZE  = 64
BODY_FONT_SIZE   = 44

# 入出力
DATA_DIR  = Path("data")
TTS_DIR   = DATA_DIR / "tts"
PLAN_JSON = DATA_DIR / "render_plan.json"
IMAGES_DIR= DATA_DIR / "images"        # 画像フックのディレクトリ
OUT_PATH  = Path("output.mp4")

# ====== helpers (v1/v2差分吸収) ======
def with_start(clip, t):
    return clip.with_start(t) if V2 else clip.set_start(t)

def with_duration(clip, d):
    return clip.with_duration(d) if V2 else clip.set_duration(d)

def with_position(clip, pos):
    return clip.with_position(pos) if V2 else clip.set_position(pos)

def with_audio(clip, audio):
    return clip.with_audio(audio) if V2 else clip.set_audio(audio)

# ====== drawing ======
def load_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT_PATH, size=size)
    except Exception:
        return ImageFont.load_default()

def wrap_text_by_width(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> str:
    """日本語折返し + 元テキスト内の改行を尊重"""
    text = (text or "").replace("\r\n","\n").replace("\r","\n")
    out_lines = []
    for para in text.split("\n"):
        if para == "":
            out_lines.append("")
            continue
        line = ""
        for ch in para:
            test = line + ch
            if draw.textlength(test, font=font) <= max_width:
                line = test
            else:
                if line: out_lines.append(line)
                line = ch
        if line: out_lines.append(line)
    return "\n".join(out_lines)

def render_title_image(title_ja: str) -> np.ndarray:
    img = Image.new("RGBA", (W, H), BG_COLOR + (255,))
    dr  = ImageDraw.Draw(img)
    font = load_font(TITLE_FONT_SIZE)
    band_h = TITLE_FONT_SIZE + TITLE_PAD*2
    dr.rectangle([(0,0),(W,band_h)], fill=ACCENT + (255,))
    tw = dr.textlength(title_ja, font=font)
    tx = max(TITLE_PAD, (W - tw)//2)
    dr.text((tx, TITLE_PAD), title_ja, fill=(255,255,255), font=font)
    return np.array(img.convert("RGB"))

def pick_text_color(seed_value: int) -> Tuple[int,int,int]:
    r = random.Random(seed_value)
    # 先頭は白寄りにする頻度高め（聞きやすさ優先）
    palette = TEXT_COLORS[:]
    return r.choice(palette)

def render_bottom_caption(text_ja: str, seed_color: int) -> np.ndarray:
    """
    画面下部に固定表示する字幕パネルの画像（横幅可変）を返す
    """
    # 作業キャンバス
    tmp = Image.new("RGBA", (W, H), (0,0,0,0))
    dr  = ImageDraw.Draw(tmp)
    font = load_font(BODY_FONT_SIZE)

    wrapped = wrap_text_by_width(text_ja, font, MAX_CAPTION_WIDTH - CAPTION_INNER_X*2, dr)
    bbox = dr.multiline_textbbox((0,0), wrapped, font=font, spacing=LINE_GAP, align="left")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    panel_w = min(MAX_CAPTION_WIDTH, text_w + CAPTION_INNER_X*2)
    panel_h = text_h + CAPTION_INNER_Y*2

    # パネル
    panel = Image.new("RGBA", (panel_w, panel_h), (0,0,0,0))
    d = ImageDraw.Draw(panel)
    radius = 18
    d.rounded_rectangle([(0,0),(panel_w, panel_h)], radius, fill=CARD_BG)

    # テキスト（黒縁取り）
    color = pick_text_color(seed_color)
    d.multiline_text(
        (CAPTION_INNER_X, CAPTION_INNER_Y),
        wrapped,
        fill=color,
        font=font,
        spacing=LINE_GAP,
        align="left",
        stroke_width=3,
        stroke_fill=TEXT_STROKE,
    )

    # 返り値はRGB array
    return np.array(panel.convert("RGB"))

def make_center_image_clip(img_path: Path, start: float, end: float):
    """
    中央画像（各セリフの表示中だけ出す）。存在しなければNone。
    """
    if not img_path or not img_path.exists():
        return None

    # 表示領域
    area_top = CENTER_TOP_MARGIN
    area_bottom = H - CENTER_BOTTOM_MARGIN
    area_h = max(100, area_bottom - area_top)
    area_w = W - 2*CAPTION_SIDE_MARGIN

    # PILで開いてフィットさせる（余白は上下左右に黒）
    img = Image.open(str(img_path)).convert("RGB")
    iw, ih = img.size
    # アスペクト比を保ちつつエリアに収まるようスケール
    scale = min(area_w / iw, area_h / ih)
    new_w = int(iw * scale)
    new_h = int(ih * scale)
    img_resized = img.resize((new_w, new_h), Image.LANCZOS)

    # キャンバスに中央貼り
    canvas = Image.new("RGB", (W, H), BG_COLOR)
    x = (W - new_w)//2
    y = area_top + (area_h - new_h)//2
    canvas.paste(img_resized, (x, y))

    clip = mp.ImageClip(np.array(canvas))
    clip = with_start(clip, start)
    clip = with_duration(clip, max(0.01, end - start))
    return clip

def find_center_image(scene_idx: int, line_idx_in_scene: int) -> Optional[Path]:
    """
    画像フック（存在すれば使う）:
      data/images/scene_{ss}_line_{lll}.jpg / .png
    """
    ss = f"{scene_idx:02d}"
    ll = f"{line_idx_in_scene:03d}"
    for ext in (".jpg", ".png", ".jpeg"):
        p = IMAGES_DIR / f"scene_{ss}_line_{ll}{ext}"
        if p.exists():
            return p
    return None

# ====== main ======
def main():
    print(f"[i] CWD: {os.getcwd()}")
    if not PLAN_JSON.exists():
        raise FileNotFoundError(f"{PLAN_JSON} が見つかりません")
    with open(PLAN_JSON, "r", encoding="utf-8") as f:
        plan = json.load(f)

    scenes: List[dict] = plan.get("scenes", [])
    print(f"[i] scenes: {len(scenes)}")

    audio_tracks = []
    visuals = []
    t = 0.0
    total_lines_global = 0

    # タイトル
    title_mp3 = TTS_DIR / "title.mp3"
    if title_mp3.exists():
        a = mp.AudioFileClip(str(title_mp3))
        a = with_start(a, t)
        print(f"[i] title.mp3: {a.duration:.2f}s @ {t:.2f}s")
        audio_tracks.append(a)

        title_img = render_title_image(plan.get("title_ja", ""))
        title_clip = mp.ImageClip(title_img)
        title_clip = with_duration(title_clip, a.duration)
        title_clip = with_start(title_clip, t)
        visuals.append(title_clip)
        t += a.duration + 0.2

    # 各シーン
    global_line_counter = 1
    for s, scene in enumerate(scenes, 1):
        rows = scene.get("items", [])
        print(f"[i] scene {s}: {len(rows)} items")

        # 1周目：時刻だけ出してから区切り計算
        timeline: List[Tuple[dict, float, float]] = []  # (row, start, dur)
        scene_start_t = t
        for i, row in enumerate(rows, 1):
            mp3_path = TTS_DIR / f"line_{global_line_counter:03d}.mp3"
            if not mp3_path.exists():
                raise FileNotFoundError(f"{mp3_path} がありません（TTS未生成？）")
            a = mp.AudioFileClip(str(mp3_path))
            a = with_start(a, t)
            print(f"    - {mp3_path.name}: {a.duration:.2f}s @ {t:.2f}s")
            audio_tracks.append(a)

            timeline.append((row, t, a.duration))
            t += a.duration
            total_lines_global += 1
            global_line_counter += 1

        scene_end = t + SCENE_TAIL

        # 2周目：下部固定字幕 & 画像を作成
        for i, (row, start_t, dur) in enumerate(timeline, 1):
            # 表示区間は「次のセリフの開始」まで（最後は scene_end）
            end_t = timeline[i][1] if i < len(timeline) else scene_end

            # 下部字幕
            caption_img = render_bottom_caption(
                text_ja=row.get("text_ja",""),
                seed_color=(s*1000 + i)
            )
            caption_clip = mp.ImageClip(caption_img)
            # 底部中央寄せ
            cap_x = (W - caption_img.shape[1]) // 2
            cap_y = H - CAPTION_BOTTOM_MARGIN - caption_img.shape[0]
            caption_clip = with_position(caption_clip, (cap_x, cap_y))
            caption_clip = with_start(caption_clip, start_t)
            caption_clip = with_duration(caption_clip, max(0.01, end_t - start_t))
            visuals.append(caption_clip)

            # 中央画像（あれば）
            img_path = find_center_image(s, i)
            center_clip = make_center_image_clip(img_path, start_t, end_t)
            if center_clip is not None:
                visuals.append(center_clip)

        # シーンの“間”
        t = scene_end

    total_dur = t
    print(f"[i] total lines: {total_lines_global}")
    print(f"[i] total duration: {total_dur:.2f}s")
    if total_dur <= 0:
        raise RuntimeError("タイムラインが0秒です。render_plan.json / tts/line_*.mp3 を確認してください。")

    # 背景 & オーディオ合成（音声は確実に付ける）
    bg = mp.ColorClip(size=(W, H), color=BG_COLOR, duration=total_dur)
    final_audio = mp.CompositeAudioClip(audio_tracks)
    final_audio = with_duration(final_audio, total_dur)

    comp = mp.CompositeVideoClip([bg] + visuals)
    comp = with_audio(comp, final_audio)
    comp = with_duration(comp, total_dur)

    out_abs = os.path.abspath(str(OUT_PATH))
    print(f"[i] write to: {out_abs}")
    comp.write_videofile(
        out_abs,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        audio_fps=48000,        # 音声ストリームはこれで付く
        bitrate="6000k",
        threads=4,
        preset="medium",
        temp_audiofile="temp-audio.m4a",
        remove_temp=True,
    )
    print("[i] DONE.")


if __name__ == "__main__":
    main()
