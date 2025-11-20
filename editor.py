# editor.py
# Purpose: Ask an LLM to design a ~3min video structure from Reddit threads.
# Input (from fetch_all.fetch_post_threads): a list of threads (top + replies)
# Output: {"scenes":[{"scene_title":"...", "comment_order":["id_top","id_r1", ...]}, ...]}
#
# Notes:
# - Strict JSON only. If the LLM doesn't return the required top-level "scenes", this function raises ValueError.
# - The OpenAI client is created INSIDE the function to ensure .env is loaded and OPENAI_API_KEY is available.
# - Model is configurable via env OPENAI_MODEL_EDITOR (default: gpt-4o-mini).

from __future__ import annotations
import json
from typing import Dict, Any, List
import os
from dotenv import load_dotenv

def _get_openai_client():
    """Create an OpenAI client after loading .env. Supports both new/old SDK styles."""
    load_dotenv()  # ensure OPENAI_API_KEY is available
    # Prefer new-style client if available
    try:
        from openai import OpenAI  # openai>=1.0
        return OpenAI()
    except Exception:
        # Fallback to legacy Client
        import openai  # type: ignore
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Create a .env with OPENAI_API_KEY=...")
        openai.api_key = api_key
        return openai.Client()  # type: ignore[attr-defined]

def _compact_text(t: str, limit: int = 360) -> str:
    """Trim text to keep prompts small; preserve one-line."""
    t = (t or "").strip().replace("\n", " ")
    if len(t) <= limit:
        return t
    return t[:limit] + "…"

def _default_model_name() -> str:
    return os.getenv("OPENAI_MODEL_EDITOR", "gpt-4o-mini")

def plan_script_with_llm(
    title: str,
    threads: List[Dict[str, Any]],
    target_duration_sec: int = 180,
    reading_chars_per_sec: float = 5.0,
    max_threads_for_prompt: int = 28,
    model: str | None = None,
) -> Dict[str, Any]:
    """
    Build a 3-minute scene plan.
    - Each scene corresponds to one thread (top-level + selected replies).
    - Within a scene, comments are rendered top-to-bottom in the returned 'comment_order'.
    - If the LLM fails to return the strict 'scenes' schema, this function raises ValueError.
    """
    client = _get_openai_client()
    model = model or _default_model_name()

    # Budget for narration length in Japanese (approximate)
    budget_chars = int(max(60, target_duration_sec * max(3.0, reading_chars_per_sec)))  # keep sane bounds

    # Reduce payload to control token usage
    pick = threads[:max_threads_for_prompt]
    payload: List[Dict[str, Any]] = []
    allowed_ids: set[str] = set()
    for th in pick:
        allowed_ids.add(th["top"]["id"])
        row = {
            "thread_id": th["top"]["id"],
            "top": {
                "id": th["top"]["id"],
                "score": th["top"]["score"],
                "author": th["top"]["author"],
                "text": _compact_text(th["top"]["body"]),
            },
            "replies": []
        }
        # Take up to 6 high-score replies (already sorted by fetcher)
        for r in th["replies"][:6]:
            row["replies"].append({
                "id": r["id"],
                "score": r["score"],
                "author": r["author"],
                "text": _compact_text(r["body"]),
            })
            allowed_ids.add(r["id"])
        payload.append(row)

    system = (
        "You are a senior YouTube script editor for a Japanese news-style channel covering Pokémon TCG.\n"
        "Follow these HARD RULES and do not deviate:\n"
        "1) Output ONLY JSON with a single top-level key \"scenes\". No extra keys, no prose.\n"
        "2) Each scene covers exactly ONE thread (top-level + its replies).\n"
        "3) For each scene, return:\n"
        "   - scene_title: short Japanese title (<=20 chars) summarizing the thread's angle.\n"
        "   - comment_order: an array of comment IDs (strings) from the provided input ONLY, in on-screen order (top to bottom).\n"
        "4) Design a 3-minute arc: intro -> key angles (pro/cons/tips) -> closing. Favor higher-score threads but keep diversity.\n"
        "5) No invented IDs, no new text. Use ONLY the IDs provided in the input JSON.\n"
        "6) Keep total narration budget around the provided 'budget_chars' (the caller will compose the narration later).\n"
    )

    # Give the model an explicit JSON schema to reduce drift
    schema_hint = {
        "scenes": [
            {
                "scene_title": "短い見出し",
                "comment_order": ["id_top", "id_reply1", "id_reply2"]
            }
        ]
    }

    user = {
        "title": title,
        "budget_chars": budget_chars,
        "threads": payload,
        "expected_schema_example": schema_hint,
    }

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
        max_tokens=1200,
    )

    raw = resp.choices[0].message.content
    try:
        plan = json.loads(raw)
    except Exception as e:
        raise ValueError(f"LLM output was not valid JSON. Raw (truncated): {raw[:1000]}") from e

    # Validate 'scenes'
    scenes = plan.get("scenes")
    if not isinstance(scenes, list):
        raise ValueError("LLM output missing 'scenes' list. Raw (truncated): " + raw[:1000])

    # Clean: keep only allowed IDs and non-empty scenes
    cleaned_scenes: List[Dict[str, Any]] = []
    for sc in scenes:
        title_ja = (sc.get("scene_title") or "").strip()
        order = [cid for cid in (sc.get("comment_order") or []) if cid in allowed_ids]
        if not order:
            # skip empty/invalid
            continue
        cleaned_scenes.append({
            "scene_title": title_ja,
            "comment_order": order
        })

    if not cleaned_scenes:
        raise ValueError("No valid scenes after cleaning. The model likely used unknown IDs or empty orders.")

    return {"scenes": cleaned_scenes}
