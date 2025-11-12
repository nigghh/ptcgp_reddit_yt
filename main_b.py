
# main_b.py
import os
import json
import random
from typing import List, Dict, Any

from fetch_all import fetch_post_threads
from editor import plan_script_with_llm
from translate import translate_to_casual_japanese
from tts import generate_tts, POSTER_VOICE, COMMENT_VOICES

OUT_DIR = "data"
TTS_DIR = os.path.join(OUT_DIR, "tts")
os.makedirs(TTS_DIR, exist_ok=True)

def translate_selection(selection_ids: List[str], index: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """
    選ばれたコメント（ID）のみ翻訳してキャッシュ辞書を返す: {id: {"en":..., "ja":...}}
    """
    result = {}
    for cid in selection_ids:
        item = index[cid]
        en = item["body"]
        ja = translate_to_casual_japanese(en)
        result[cid] = {"en": en, "ja": ja}
    return result

def build_index(threads: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    全コメントを id -> オブジェクト で引けるようにする
    """
    idx = {}
    for th in threads:
        idx[th["top"]["id"]] = th["top"]
        for r in th["replies"]:
            idx[r["id"]] = r
    return idx

def flatten_scene_ids(plan: Dict[str, Any]) -> List[str]:
    ids = []
    for sc in plan["scenes"]:
        ids.extend(sc.get("comment_order", []))
    # 重複除去（順序保持）
    seen = set()
    dedup = []
    for x in ids:
        if x not in seen:
            seen.add(x)
            dedup.append(x)
    return dedup

def make_tts_files(title_ja: str, plan: Dict[str, Any], translations: Dict[str, Dict[str, str]]):
    # タイトル読み上げ
    generate_tts(title_ja, POSTER_VOICE, os.path.join(TTS_DIR, "title.mp3"))
    # 各コメント読み上げ（ランダムボイス）
    count = 1
    for sc in plan["scenes"]:
        for cid in sc.get("comment_order", []):
            ja = translations[cid]["ja"]
            voice = random.choice(COMMENT_VOICES)
            generate_tts(ja, voice, os.path.join(TTS_DIR, f"line_{count:03d}.mp3"))
            count += 1

def assemble_render_plan(plan: Dict[str, Any], translations: Dict[str, Dict[str, str]], index: Dict[str, Dict[str, Any]], title_ja: str) -> Dict[str, Any]:
    """
    動画編集ツール向けのレンダリング・キュー（画面描画順）
    - シーン切替で 'clear': true を入れる
    - 各行に日本語テキスト、元英語の短い引用、出典（author, score, permalink）
    """
    scenes_out = []
    for sc in plan["scenes"]:
        scene_items = []
        for cid in sc.get("comment_order", []):
            meta = index[cid]
            tr = translations[cid]
            scene_items.append({
                "text_ja": tr["ja"],
                "quote_en": tr["en"][:120],
                "author": meta.get("author"),
                "score": meta.get("score"),
                "permalink": meta.get("permalink")
            })
        scenes_out.append({
            "clear": True,
            "scene_title": sc.get("scene_title", ""),
            "items": scene_items
        })
    return {
        "title_ja": title_ja,
        "scenes": scenes_out
    }

def main():
    # 1) 入力URL
    url = os.environ.get("REDDIT_POST_URL", "").strip()
    if not url:
        # デフォルト例（差し替えてください）
        url = "https://www.reddit.com/r/PTCGP/comments/1orpru1/favorite_oldest_meta/"
        print(f"[i] REDDIT_POST_URL が未設定のためデフォルトURLを使用: {url}")

    # 2) 全スレッド取得（広告・画像リンク除外、返信含む）
    data = fetch_post_threads(url, max_threads=50, max_replies_per_thread=50)
    title_en = data["title"]
    print("[i] title:", title_en)
    print("[i] threads:", len(data["threads"]))

    # 3) LLMで「3分構成」の選抜・順序化
    plan = plan_script_with_llm(data["title"], data["threads"], target_duration_sec=180)
    # 例: {"scenes":[{"scene_title":"…","thread_top_id":"abc","comment_order":["abc","r1","r3"]}, ...]}
    with open(os.path.join(OUT_DIR, "plan.json"), "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    # 4) 選ばれたコメントだけ翻訳
    index = build_index(data["threads"])
    selection_ids = flatten_scene_ids(plan)
    translations = translate_selection(selection_ids, index)

    # タイトルも翻訳
    title_ja = translate_to_casual_japanese(title_en)

    # 5) TTS音声を生成
    make_tts_files(title_ja, plan, translations)

    # 6) レンダープランを保存（編集ツールへの入力）
    render_plan = assemble_render_plan(plan, translations, index, title_ja)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "render_plan.json"), "w", encoding="utf-8") as f:
        json.dump(render_plan, f, ensure_ascii=False, indent=2)

    # 7) ログ的なプレーンテキストも保存（確認用）
    with open(os.path.join(OUT_DIR, "script_preview.txt"), "w", encoding="utf-8") as f:
        f.write(f"【タイトル】\n{title_ja}\n\n")
        for i, sc in enumerate(plan["scenes"], 1):
            f.write(f"--- Scene {i}: {sc.get('scene_title','')} ---\n")
            for cid in sc.get("comment_order", []):
                f.write(f" - {translations[cid]['ja']}\n")
            f.write("\n")

    print("\n=== Done (B-plan pipeline) ===")
    print("Outputs:")
    print(" - data/plan.json            … LLMが選んだシーン構成")
    print(" - data/render_plan.json     … 画面描画用のキュー（シーン単位でクリア→新規描画）")
    print(" - data/script_preview.txt   … 台本ざっくり確認用")
    print(" - data/tts/title.mp3, line_*.mp3  … 音声ファイル")

if __name__ == "__main__":
    main()
