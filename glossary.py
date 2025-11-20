# glossary.py
# - CSV(en,ja,type,aliases) を読み込んで Term に変換
# - 表記ゆれ(aliases)は CSV が空でも自動で補完
from __future__ import annotations
import csv, re
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Term:
    en: str
    ja: str
    aliases: List[str]
    typ: str = "term"

def load_glossary(path: str) -> List[Term]:
    """
    読み込み対象は基本 'en,ja,type,aliases' の正規化CSV。
    - aliases は ';' 区切り（空でもOK）
    - BOM付きUTF-8も可
    """
    terms: List[Term] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"ヘッダ行を検出できませんでした: {path}")
        # 必須列チェック（最低 en, ja が必要）
        fields = {c.lower(): c for c in reader.fieldnames}
        col_en = fields.get("en")
        col_ja = fields.get("ja")
        col_aliases = fields.get("aliases")
        col_type = fields.get("type")

        if not col_en or not col_ja:
            raise ValueError(f"'en' と 'ja' 列が必要です。見つかったヘッダ: {reader.fieldnames}")

        for row in reader:
            en = (row.get(col_en) or "").strip()
            ja = (row.get(col_ja) or "").strip()
            typ = (row.get(col_type) or "term").strip() if col_type else "term"
            aliases_raw = (row.get(col_aliases) or "").strip() if col_aliases else ""
            aliases = [a.strip() for a in aliases_raw.split(";") if a.strip()] if aliases_raw else []
            if en and ja:
                terms.append(Term(en=en, ja=ja, aliases=aliases, typ=typ))
    return terms

def _escape_for_alt(s: str) -> str:
    # 正規表現用にエスケープし、空白は柔軟一致にする
    s = re.escape(s)
    s = s.replace(r"\ ", r"\s+")
    return s

def _derive_aliases(s: str) -> List[str]:
    """英語名から代表的な表記ゆれを自動生成（CSVのaliasesが空でも拾う）"""
    v = set()
    s1 = s
    v.add(s1.replace("-", " "))
    v.add(s1.replace("-", ""))
    v.add(s1.replace(" ", ""))
    v.add(s1.replace(".", ""))
    s2 = s1.replace("’", "'").replace("‘", "'")
    v.add(s2)
    v.add(s2.replace(" ", ""))
    # Farfetch’d 等のアポストロフィ除去
    if "’" in s1 or "'" in s1:
        v.add(s1.replace("’", "").replace("'", ""))
    # Mr. 系
    if "Mr. " in s1:
        v.add(s1.replace("Mr. ", "Mr "))
        v.add(s1.replace("Mr. ", "Mr"))
    # TCG接尾辞の結合/小文字
    for token in ["EX", "GX", "V", "VMAX", "VSTAR"]:
        v.add(s1.replace(" "+token, token))
        v.add(s1.replace(token+" ", token))
        t_low = token.lower()
        v.add(s1.replace(" "+t_low, token))
        v.add(s1.replace(t_low+" ", token))
    return [x for x in v if x and x != s]

def compile_glossary_patterns(terms: List[Term]) -> List[Tuple[re.Pattern, str]]:
    """
    各Termについて、英語名+aliases+自動派生aliasesを1本のregexにまとめ、
    日本語名へ置換するための (pattern, ja) リストを返す。
    """
    patterns: List[Tuple[re.Pattern, str]] = []
    for t in terms:
        alts = [t.en] + (t.aliases or []) + _derive_aliases(t.en)
        alts = sorted(set(a for a in alts if a), key=len, reverse=True)
        if not alts:
            continue
        alt_pat = "|".join(_escape_for_alt(a) for a in alts)
        pat = re.compile(rf"(?<![A-Za-z0-9_])(?:{alt_pat})(?![A-Za-z0-9_])", re.IGNORECASE)
        patterns.append((pat, t.ja))
    # 多別名の語を先に処理
    patterns.sort(key=lambda pj: pj[0].pattern.count("|"), reverse=True)
    return patterns

__all__ = ["Term", "load_glossary", "compile_glossary_patterns"]
