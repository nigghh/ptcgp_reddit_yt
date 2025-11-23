# render_video.py
# - B案の render_plan.json + mp3群 から横動画(1920x1080)を生成
# - MoviePy v2対応（v1へ自動フォールバック）
# - 基本ログ付き（タイムライン長が0だと明確にエラー）
# 実行: python render_video.py

import os, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# ---- MoviePy import (v2推奨, v1 fallback) ----
try:
    import moviepy as mp      # v2
    from moviepy import vfx   # v2 effects
    V2 = True
except Exception:
    import moviepy.editor as mp  # v1
    V2 = False

# ====== Config ======
W, H = 1920, 1080          # 縦動画なら 1080, 1920
FPS = 30
BG_COLOR   = (16, 16, 20)
CARD_BG    = (28, 28, 36, 220)
TEXT_COLOR = (245, 245, 250)
META_COLOR = (200, 200, 210)
ACCENT     = (50, 120, 255)
SCENE_TAIL = 0.30
FADE_IN    = 0.18
TITLE_PAD  = 24

# 日本語フォント（必要に応じて修正）
FONT_PATH = r"C:\Windows\Fonts\meiryo.ttc"
TITLE_FONT_SIZE = 64
BODY_FONT_SIZE  = 42
META_FONT_SIZE  = 28

MAX_CARD_WIDTH = 1600
CARD_MARGIN_X  = 100
CARD_TOP_Y     = 200
LINE_GAP       = 18
CARD_INNER_X   = 36
CARD_INNER_Y   = 28

DATA_DIR  = Path("data")
TTS_DIR   = DATA_DIR / "tts"
PLAN_JSON = DATA_DIR / "render_plan.json"
OUT_PATH  = Path("output.mp4")

# ====== helpers ======
def with_start(clip, t):
    return clip.with_start(t) if V2 else clip.set_start(t)

def with_duration(clip, d):
    return clip.with_duration(d) if V2 else clip.set_duration(d)

def with_position(clip, pos):
    return clip.with_position(pos) if V2 else clip.set_position(pos)

def with_audio(clip, audio):
    return clip.with_audio(audio) if V2 else clip.set_audio(audio)

def fade_in(clip, seconds):
    if seconds <= 0:
        return clip
    if V2:
        return clip.with_effects([vfx.FadeIn(seconds)])
    else:
        return clip.fx(mp.vfx.fadein, seconds)

def load_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size=size)
    except Exception:
        return ImageFont.load_default()

def wrap_text_by_width(text, font, max_width, draw):
    # 日本語の折返し：1文字ずつ幅を見て改行
    lines, line = [], ""
    for ch in text:
        test = line + ch
        if draw.textlength(test, font=font) <= max_width:
            line = test
        else:
            if line: lines.append(line)
            line = ch
    if line: lines.append(line)
    return "\n".join(lines)

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

def render_comment_card(text_ja: str, author=None, score=None) -> np.ndarray:
    card_w = min(MAX_CARD_WIDTH, W - CARD_MARGIN_X*2)
    tmp = Image.new("RGBA", (W,H), (0,0,0,0))
    dr  = ImageDraw.Draw(tmp)
    body_font = load_font(BODY_FONT_SIZE)
    meta_font = load_font(META_FONT_SIZE)

    wrapped = wrap_text_by_width(text_ja, body_font, card_w - CARD_INNER_X*2, dr)
    body_bbox = dr.multiline_textbbox((0,0), wrapped, font=body_font, spacing=LINE_GAP)
    body_h = body_bbox[3] - body_bbox[1]

    meta_text = ""
    if author: meta_text += f"by {author}"
    if score is not None: meta_text += f"   ▲{score}"
    meta_h = meta_font.size + 6 if meta_text else 0

    card_h = CARD_INNER_Y*2 + body_h + (meta_h or 0)
    card = Image.new("RGBA", (card_w, card_h), (0,0,0,0))
    drc  = ImageDraw.Draw(card)
    drc.rounded_rectangle([(0,0),(card_w,card_h)], 18, fill=CARD_BG)

    y = CARD_INNER_Y
    if meta_text:
        drc.text((CARD_INNER_X, y), meta_text, fill=META_COLOR, font=meta_font)
        y += meta_h
    drc.multiline_text((CARD_INNER_X, y), wrapped, fill=TEXT_COLOR, font=body_font, spacing=LINE_GAP)

    return np.array(card.convert("RGB"))

# ====== main ======
def main():
    print(f"[i] CWD: {os.getcwd()}")
    if not PLAN_JSON.exists():
        raise FileNotFoundError(f"{PLAN_JSON} が見つかりません")

    with open(PLAN_JSON, "r", encoding="utf-8") as f:
        plan = json.load(f)
    scenes = plan.get("scenes", [])
    print(f"[i] scenes: {len(scenes)}")

    audio_tracks = []
    visuals = []
    t = 0.0
    total_lines = 0

    # タイトル
    title_mp3 = TTS_DIR / "title.mp3"
    if title_mp3.exists():
        a = mp.AudioFileClip(str(title_mp3))
        a = with_start(a, t)
        print(f"[i] title.mp3: {a.duration:.2f}s")
        audio_tracks.append(a)

        img = render_title_image(plan.get("title_ja",""))
        clip = mp.ImageClip(img)
        clip = with_duration(clip, a.duration)
        clip = with_start(clip, t)
        visuals.append(clip)
        t += a.duration + 0.2

    # 各シーン
    line_idx = 1
    for s, scene in enumerate(scenes, 1):
        rows = scene.get("items", [])
        print(f"[i] scene {s}: {len(rows)} items")
        scene_clips = []
        y = CARD_TOP_Y
        for row in rows:
            mp3_path = TTS_DIR / f"line_{line_idx:03d}.mp3"
            if not mp3_path.exists():
                raise FileNotFoundError(f"{mp3_path} がありません（TTS未生成？）")
            a = mp.AudioFileClip(str(mp3_path))
            a = with_start(a, t)
            audio_tracks.append(a)

            card_img = render_comment_card(
                text_ja=row.get("text_ja",""),
                author=row.get("author"),
                score=row.get("score"),
            )
            card_clip = mp.ImageClip(card_img)
            card_clip = with_start(card_clip, t)
            card_clip = with_position(card_clip, (CARD_MARGIN_X, y))
            card_clip = with_duration(card_clip, 1e9)
            card_clip = fade_in(card_clip, FADE_IN)
            scene_clips.append(card_clip)
            visuals.append(card_clip)

            y += (Image.fromarray(card_img).height + 20)
            t += a.duration
            total_lines += 1
            line_idx += 1

        # シーン末の“間”と、表示延長
        scene_end = t + SCENE_TAIL
        for i, sc in enumerate(scene_clips):
            nd = scene_end - sc.start  # v1/v2どちらでも .start は使える
            scene_clips[i] = with_duration(sc, nd)
        t = scene_end

    total_dur = t
    print(f"[i] total lines: {total_lines}")
    print(f"[i] total duration: {total_dur:.2f}s")
    if total_dur <= 0:
        raise RuntimeError("タイムラインが0秒です。render_plan.json / tts/line_*.mp3 を確認してください。")

    bg = mp.ColorClip(size=(W, H), color=BG_COLOR, duration=total_dur)
    final_audio = mp.CompositeAudioClip(audio_tracks)
    final_audio = with_duration(final_audio, total_dur)

    comp = mp.CompositeVideoClip([bg] + visuals)
    comp = with_audio(comp, final_audio)

    out_abs = os.path.abspath(str(OUT_PATH))
    print(f"[i] write to: {out_abs}")
    comp.write_videofile(
        out_abs,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate="6000k",
        threads=4,
        preset="medium",
        temp_audiofile="temp-audio.m4a",
        remove_temp=True,
    )
    print("[i] DONE.")

if __name__ == "__main__":
    main()
