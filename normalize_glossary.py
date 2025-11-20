# normalize_glossary.py
# 入力: カンマ区切りの CSV（ヘッダ有り/無しどちらでもOK）
#       想定列: No, 日本語名, 英語名（順不同OK）
# 出力: en,ja,type,aliases（カンマ区切り/UTF-8）
import csv
import argparse

def guess_header(tokens):
    joined = " ".join(tokens).lower()
    return any(k in joined for k in ["日本", "和名", "英", "english", "ja", "jp", "en"])

def metric_ja(s):
    if not s: return 0.0
    total = len(s)
    non_ascii = sum(1 for ch in s if ord(ch) > 127)
    return non_ascii / max(1, total)

def metric_en(s):
    if not s: return 0.0
    letters = sum(1 for ch in s if ("A"<=ch<="Z") or ("a"<=ch<="z"))
    return letters / len(s)

def gen_aliases(en: str) -> str:
    if not isinstance(en, str):
        return ""
    s = en.strip()
    if not s:
        return ""
    variants = {
        s.replace("-", " "),
        s.replace("-", ""),
        s.replace(" ", ""),
        s.replace(".", ""),
        s.replace("’", "'").replace("‘", "'"),
        s.replace("’", "'").replace("‘", "'").replace(" ", ""),
    }
    variants.discard(s)
    variants = [v for v in variants if v]
    return ";".join(sorted(variants, key=len, reverse=True))

def normalize(in_path: str, out_path: str):
    # UTF-8 BOM 付きも吸収
    with open(in_path, "r", encoding="utf-8-sig", newline="") as fi:
        # まず生で全部読み込む（空行は除外）
        raw_lines = [ln.rstrip("\r\n") for ln in fi if ln.strip() != ""]
    if not raw_lines:
        raise ValueError("入力CSVが空です。")

    # カンマ区切り前提で分解（ExcelのCSVならOK）
    def split(line):
        return next(csv.reader([line], delimiter=","))

    first = split(raw_lines[0])
    has_header = guess_header(first)

    rows = []
    headers = first if has_header else None
    for ln in (raw_lines[1:] if has_header else raw_lines):
        rows.append(split(ln))

    # 列インデックスを決める
    def find_col_index_by_name(headers, candidates):
        if headers is None:
            return None
        lower = [h.lower() for h in headers]
        for i, h in enumerate(lower):
            if any(c in h for c in candidates):
                return i
        return None

    idx_ja = find_col_index_by_name(headers, ["日本", "和名", "ja", "jp"])
    idx_en = find_col_index_by_name(headers, ["英", "english", "en"])

    # ヘッダから見つからなければ中身の特徴で推定
    if idx_ja is None or idx_en is None:
        num_cols = max(len(r) for r in rows) if rows else 0
        scores_ja = [0.0]*num_cols
        scores_en = [0.0]*num_cols
        for r in rows[:50]:
            for i in range(num_cols):
                val = r[i] if i < len(r) else ""
                scores_ja[i] += metric_ja(val)
                scores_en[i] += metric_en(val)
        if idx_ja is None:
            idx_ja = max(range(num_cols), key=lambda i: scores_ja[i])
        if idx_en is None:
            cands = [i for i in range(num_cols) if i != idx_ja]
            idx_en = max(cands, key=lambda i: scores_en[i]) if cands else 0

    # 出力
    with open(out_path, "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(["en","ja","type","aliases"])
        for r in rows:
            en = (r[idx_en] if idx_en is not None and idx_en < len(r) else "").strip()
            ja = (r[idx_ja] if idx_ja is not None and idx_ja < len(r) else "").strip()
            if not en and not ja:
                continue
            w.writerow([en, ja, "pokemon", gen_aliases(en)])

    print(f"[OK] -> {out_path}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="入力CSV（No/日本語名/英語名）")
    ap.add_argument("--out", dest="out_path", required=True, help="出力CSV（en,ja,type,aliases）")
    args = ap.parse_args()
    normalize(args.in_path, args.out_path)
