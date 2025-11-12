
# editor.py
import json
from typing import Dict, Any, List
import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")
client = openai.Client()

def _compact_text(t: str, limit: int = 360) -> str:
    t = (t or "").strip().replace("\n", " ")
    if len(t) <= limit:
        return t
    return t[:limit] + "…"

def plan_script_with_llm(title: str,
                         threads: List[Dict[str, Any]],
                         target_duration_sec: int = 180,
                         reading_chars_per_sec: float = 5.0,
                         max_threads_for_prompt: int = 28) -> Dict[str, Any]:
    """
    LLMに『3分の動画台本』を組ませる
    - 1シーン=1トピック（1つのトップコメントとその返信）
    - シーンごとにコメントを上から順に描画、次のシーンで一度クリア
    - 出力は選ばれたコメントIDの順序と、短いセクションタイトル
    返り値:
      {
        "scenes": [
          {"scene_title":"…","thread_top_id":"xxx","comment_order":["id_top","id_r1","id_r2"]}
        ],
        "budget_chars": int
      }
    """
    budget_chars = int(target_duration_sec * reading_chars_per_sec)

    # LLMに渡す情報量を抑制しつつ代表性を確保
    pick = threads[:max_threads_for_prompt]
    payload = []
    for th in pick:
        t = {
            "thread_id": th["top"]["id"],
            "top": {
                "id": th["top"]["id"],
                "score": th["top"]["score"],
                "author": th["top"]["author"],
                "text": _compact_text(th["top"]["body"]),
            },
            "replies": [
                {
                    "id": r["id"],
                    "score": r["score"],
                    "author": r["author"],
                    "text": _compact_text(r["body"]),
                }
                for r in th["replies"][:6]  # 各スレッドの上位返信を最大6件
            ]
        }
        payload.append(t)

    sys = """You are a senior YouTube script editor for a Japanese news-style channel covering Pokémon TCG.
- Input is English Reddit threads (top-level comment + replies).
- Goal: Design a 3-minute video (≈ budget_chars characters of **Japanese narration**) that highlights the most valuable discussion.
- Style: clear, neutral, fast-paced; avoid sarcasm unless explicit; no invented facts.
- Each scene covers one *thread* (top-level + selected replies). Within a scene, comments appear on screen from top to bottom; when scene changes, previous comments disappear.
- Choose threads to form a narrative arc: intro -> main angles (pro/cons/tips) -> closing takeaways.
- Favor higher-score comments, but include diversity (conflicting views, tips).
- Absolutely DO NOT fabricate quotes. Only use provided comment texts.
Return JSON strictly.
"""
    user = {
        "title": title,
        "budget_chars": budget_chars,
        "threads": payload
    }

    # LLMに「コメントIDの順序＋シーン構成」を出させる
    res = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)}
        ],
        temperature=0.3,
        response_format={"type":"json_object"},
        max_tokens=1200,
    )
    raw = res.choices[0].message.content
    plan = json.loads(raw)

    # 念のため最低限のバリデーション
    if "scenes" not in plan:
        raise ValueError("LLM output missing 'scenes'. Received: " + raw[:2000])

    return plan
