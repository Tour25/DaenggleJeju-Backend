import re
from collections import defaultdict
from typing import Iterable, List, Dict, Tuple, Optional
from members.constants import STYLE_CHOICES, STYLE_KEYWORDS


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()

def infer_styles(
    *,
    title: str,
    description: str,
    tags: Iterable[str],
    category: Optional[str] = None,
    context_name: str = "",
    min_score: int = 1,
    max_labels: int = 3,
) -> Tuple[List[str], Dict[str, Dict]]:

    text = " ".join([
        _norm(title),
        _norm(description),
        _norm(context_name),
        _norm(" ".join(tags or [])),
    ])

    scores = defaultdict(int)
    hits: Dict[str, List[str]] = {code: [] for code, _ in STYLE_CHOICES}

    for code, _ in STYLE_CHOICES:
        for kw in STYLE_KEYWORDS.get(code, []):
            if _norm(kw) and _norm(kw) in text:
                scores[code] += 1
                hits[code].append(kw)

    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    styles = [code for code, sc in ranked if sc >= min_score][:max_labels]
    meta = {code: {"score": scores[code], "hits": hits[code]} for code in styles}
    return styles, meta
