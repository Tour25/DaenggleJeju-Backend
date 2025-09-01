from types import SimpleNamespace
from typing import Dict, Optional, List
from datetime import timedelta
from django.utils.timezone import now as tz_now
from django.db.models import Q
from django.db.models import Count
from daenggle.models import DaenggleClip, DaenggleTag

def _pick_thumb(clip):
    t = clip.thumbnails or {}
    # YouTube가 주는 해상도 우선순위대로 고름
    for key in ("maxres", "standard", "high", "medium", "default"):
        url = (t.get(key) or {}).get("url")
        if url:
            return url
    # 그래도 없으면 기본값
    return f"https://i.ytimg.com/vi/{clip.video_id}/hqdefault.jpg"

def _clip_to_dto(clip) -> Dict:
    tag_names = [t.context_name for t in getattr(clip, "taggings_all", [])][:10]
    thumb = _pick_thumb(clip)
    return {
        "clipId": clip.id,
        "videoId": clip.video_id,
        "title": clip.title,
        "channelTitle": clip.channel_title,
        "publishedAt": clip.published_at,
        "durationSeconds": clip.duration_seconds,
        "viewCount": clip.view_count,
        "thumbnailUrl": thumb,
        "watchUrl": f"https://www.youtube.com/watch?v={clip.video_id}",
        "tags": tag_names,
    }

def list_shorts(
    feed_type: str,
    *,
    context_id: Optional[str] = None,
    keyword: Optional[str] = None,
    days: Optional[int] = None,
    max_duration: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
    sort: str = "rank",
) -> Dict:
    qs = DaenggleClip.objects.all()

    if feed_type == "trending":
        qs = qs.filter(tagging__category=DaenggleTag.Category.TREND)

    elif feed_type == "place":
        qs = qs.filter(tagging__category=DaenggleTag.Category.PLACE)
        if context_id:
            qs = qs.filter(tagging__context_id=context_id)

    elif feed_type == "accommodation":
        qs = qs.filter(tagging__category=DaenggleTag.Category.ACCOMMODATION)
        if context_id:
            qs = qs.filter(tagging__context_id=context_id)

    elif feed_type == "keyword":
        qs = qs.filter(tagging__category=DaenggleTag.Category.KEYWORD)
        if keyword:
            qs = qs.filter(tagging__context_name__iexact=keyword.strip())
    else:
        return {"items": [], "nextOffset": None, "hasMore": False}

    qs = qs.distinct()

    if days is not None:
        qs = qs.filter(published_at__gte=tz_now() - timedelta(days=int(days)))
    if max_duration is not None:
        qs = qs.filter(duration_seconds__lte=int(max_duration))

    if sort == "views":
        qs = qs.order_by("-view_count", "-published_at", "-id")
    elif sort == "recent":
        qs = qs.order_by("-published_at", "-view_count", "-id")
    else:
        qs = qs.order_by("-published_at", "-view_count", "-id")

    clips = list(qs[offset: offset + limit])

    tag_map: Dict[int, List[str]] = {}
    rows = (DaenggleTag.objects
            .filter(clip_id__in=[c.id for c in clips])
            .values("clip_id", "context_name"))
    for r in rows:
        tag_map.setdefault(r["clip_id"], []).append(r["context_name"])
    for c in clips:
        c.taggings_all = [SimpleNamespace(context_name=n) for n in tag_map.get(c.id, [])]

    items = [_clip_to_dto(c) for c in clips]
    next_offset = offset + limit
    has_more = len(items) == limit

    return {"items": items, "nextOffset": next_offset if has_more else None, "hasMore": has_more}
