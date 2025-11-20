# glossary_translator.py
from __future__ import annotations
import re
from typing import List, Tuple, Dict

from translate import translate_to_casual_japanese as _base_translate

PLACEHOLDER_PREFIX = "⟦P"
PLACEHOLDER_SUFFIX = "⟧"

def _mask_terms(text: str, patterns: List[Tuple[re.Pattern, str]]):
    placeholder_map: Dict[str, str] = {}
    masked = text
    for idx, (pat, ja) in enumerate(patterns):
        placeholder = f"{PLACEHOLDER_PREFIX}{idx}{PLACEHOLDER_SUFFIX}"
        if placeholder in masked:
            continue
        masked, count = pat.subn(placeholder, masked)
        if count > 0:
            placeholder_map[placeholder] = ja
    return masked, placeholder_map

def _unmask(text: str, placeholder_map: Dict[str, str]) -> str:
    out = text
    for ph, ja in placeholder_map.items():
        out = out.replace(ph, ja)
    return out

def _post_fix_english_terms(text: str, patterns: List[Tuple[re.Pattern, str]]) -> str:
    out = text
    for pat, ja in patterns:
        out = pat.sub(ja, out)
    return out

def translate_to_casual_japanese_glossary(en_text: str, patterns: List[Tuple] | None = None) -> str:
    if not patterns:
        return _base_translate(en_text)
    masked, ph_map = _mask_terms(en_text, patterns)
    ja = _base_translate(masked)      # ★既存の翻訳関数をそのまま再利用
    ja = _unmask(ja, ph_map)          # プレースホルダを日本語へ戻す
    ja = _post_fix_english_terms(ja, patterns)  # 念のため最終置換
    return ja
