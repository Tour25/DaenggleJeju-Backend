import base64, json
from typing import List, Optional, Tuple
from django.db.models import Q, Subquery
from django.utils.dateparse import parse_datetime
from daenggle.models import DaenggleClip, DaenggleTag

def _enc_cursor(ts_iso: str, pk: int) -> str:
    return base64.urlsafe_b64encode(json.dumps({"ts": ts_iso, "id": pk}).encode()).decode()

def _dec_cursor(cur: str) -> Optional[Tuple[str, int]]:
    if not cur:
        return None
    try:
        obj = json.loads(base64.urlsafe_b64decode(cur.encode()).decode())
        return obj["ts"], int(obj["id"])
    except Exception:
        return None

def _apply_cursor(qs, cursor: str):
    qs = qs.order_by("-published_at", "-id")
    cur = _dec_cursor(cursor or "")
    if cur:
        ts_iso, pk = cur
        ts = parse_datetime(ts_iso)
        if ts:
            qs = qs.filter(Q(published_at__lt=ts) | (Q(published_at=ts) & Q(id__lt=pk)))
    return qs

def _styles_any_q(style_codes: List[str]) -> Q:
    q = Q()
    for s in style_codes or []:
        q |= Q(styles__contains=[s])
    return q

def build_region_feed(
    *, context_id: str, style_codes: List[str], limit: int = 5,
    cursor: str = "", exclude_video_ids: List[str] = None,
):

    exclude_video_ids = exclude_video_ids or []

    clip_ids_sub = DaenggleTag.objects.filter(
        category=DaenggleTag.Category.PLACE,
        context_id=context_id
    ).values("clip_id")

    qs = DaenggleClip.objects.filter(id__in=Subquery(clip_ids_sub))

    if style_codes:
        qs = qs.filter(_styles_any_q(style_codes))

    if exclude_video_ids:
        qs = qs.exclude(video_id__in=list(set(exclude_video_ids)))

    qs = _apply_cursor(qs, cursor)

    rows = list(qs[:limit + 1])
    items = rows[:limit]
    has_more = len(rows) > len(items)

    next_cursor = ""
    if items:
        tail = items[-1]
        next_cursor = _enc_cursor(tail.published_at.isoformat(), tail.id)

    return items, next_cursor, has_more
