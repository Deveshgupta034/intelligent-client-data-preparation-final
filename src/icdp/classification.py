from __future__ import annotations
import re
import pandas as pd

try:
    from rapidfuzz.fuzz import ratio
except ImportError:
    from difflib import SequenceMatcher
    def ratio(a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio() * 100

TARGETS = ["Ignore", "Country", "Region", "Channel", "City/State", "Category", "Brand", "SKU", "Fact", "Time Period"]

ALIASES = {
    "Country": ["country", "market", "nation", "country name"],
    "Region": ["region", "zone", "territory", "sales zone", "sales territory"],
    "Channel": ["channel", "trade channel", "trade type", "sales channel", "dist channel"],
    "City/State": ["city", "state", "location", "ship to city", "destination city", "province"],
    "Category": ["category", "product group", "segment", "prod group"],
    "Brand": ["brand", "brand name", "brand desc"],
    "SKU": ["sku", "item code", "material", "product id", "item number", "product code"],
    "Fact": ["fact", "measure", "metric", "sales value", "units", "volume", "quantity"]
}

TIME = [
    r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[ _-]?\d{2,4}$",
    r"^\d{4}[ _-]?(0?[1-9]|1[0-2])$",
    r"^q[1-4][ _-]?\d{2,4}$",
    r"^\d{4}[ _-]?q[1-4]$",
    r"^(week|wk)[ _-]?\d+([ _-]?\d{2,4})?$",
    r"^\d{4}[ _-]?(week|wk)[ _-]?\d+$",
    r"^w\d{1,2}[ _-]?\d{2,4}$",
    r"^\d{4}$"
]

# Pre-compile regexes for high performance
COMPILED_TIME_PATTERNS = [re.compile(p, re.IGNORECASE) for p in TIME]
NORM_DELIMS = re.compile(r"[_/\\|-]+")
NORM_SPACES = re.compile(r"\s+")

# Pre-tokenize aliases to eliminate per-column split/set allocations
PRECOMPUTED_ALIASES = {
    f: [(a, set(a.split()), len(set(a.split()))) for a in aliases]
    for f, aliases in ALIASES.items()
}

def norm(x) -> str:
    s = NORM_DELIMS.sub(" ", str(x).strip().lower())
    return NORM_SPACES.sub(" ", s).strip()

def _score_field(n: str, precomputed: list[tuple[str, set[str], int]]) -> float:
    tokens = set(n.split())
    best = 0.0
    for a, a_tokens, a_len in precomputed:
        if n == a:
            return 1.0
        if a_tokens.issubset(tokens):
            best = max(best, 0.95)
        elif a_len == 1 and next(iter(a_tokens)) in tokens:
            best = max(best, 0.92)
        else:
            r = ratio(n, a) / 100.0
            if r >= 0.70:
                best = max(best, r)
    return best

def classify_columns(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c in df.columns:
        n = norm(c)
        if any(p.match(n) for p in COMPILED_TIME_PATTERNS):
            field, score, method = "Time Period", 1.0, "Time rule"
        else:
            score, field = max((_score_field(n, precomputed), f) for f, precomputed in PRECOMPUTED_ALIASES.items())
            if score < 0.45:
                field, method = "Ignore", "AI review"
            else:
                method = "Rule/Dictionary" if score >= 0.85 else "AI candidate"
                
        rows.append({
            "Source Column": str(c),
            "NIQ Field": field,
            "Confidence": round(score, 3),
            "Method": method,
            "User Confirmed": score >= 0.9
        })
    return pd.DataFrame(rows)

def ai_classify_unresolved(df: pd.DataFrame, mapping: pd.DataFrame, ai_client) -> tuple[pd.DataFrame, dict[str, int]]:
    cols_to_check = []
    samples = {}
    for _, r in mapping.iterrows():
        c = r["Source Column"]
        if not r["User Confirmed"] and (r["Confidence"] < 0.85 or r["NIQ Field"] == "Ignore"):
            cols_to_check.append(c)
            if c in df.columns:
                vals = [str(x).strip() for x in df[c].dropna().unique() if str(x).strip()]
                samples[c] = vals[:4]
            else:
                samples[c] = []

    if not cols_to_check:
        return mapping, {"Prompt Tokens": 0, "Completion Tokens": 0, "Total Tokens": 0}

    recs, usage = ai_client.recommend_classification(samples)
    updated = mapping.copy()
    
    for i, r in updated.iterrows():
        c = r["Source Column"]
        if c in recs:
            rec = recs[c]
            field = rec.get("field", "Ignore")
            if field in TARGETS:
                updated.at[i, "NIQ Field"] = field
                # Safe confidence parsing (handles percentages, strings, or numbers)
                raw_conf = rec.get("confidence", 0.85)
                try:
                    conf = float(str(raw_conf).replace("%", "").strip())
                    if conf > 1.0 and conf <= 100.0:
                        conf /= 100.0
                except (ValueError, TypeError):
                    conf = 0.85
                    
                updated.at[i, "Confidence"] = min(1.0, max(0.0, conf))
                updated.at[i, "Method"] = "Azure AI Luna"
                updated.at[i, "User Confirmed"] = updated.at[i, "Confidence"] >= 0.9

    return updated, usage
