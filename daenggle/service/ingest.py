import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from django.conf import settings
from django.db import transaction, IntegrityError
from django.utils.dateparse import parse_datetime

from integrations.youtube.client import YouTubeClient
from daenggle.models import DaenggleClip, DaenggleTag
from .style_rules import infer_styles

ISO = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")

def iso_to_seconds(s: Optional[str]) -> Optional[int]:
    if not s:
        return None
    m = ISO.match(s)
    if not m:
        return None
    h, m_, s_ = m.groups()
    return int(h or 0) * 3600 + int(m_ or 0) * 60 + int(s_ or 0)

def days_ago_rfc3339(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

def _to_int(v):
    try:
        return int(v)
    except Exception:
        return None

@transaction.atomic
def _upsert_batch(
    items: List[Dict],
    *,
    category: str,
    keyword: str = "",
    context_id: str = "",
    context_name: str = "",
    max_duration_seconds: Optional[int] = 60,
) -> int:
    saved = 0
    seen = set()  # (video_id, category, context_id)

    for it in items:
        vid = it.get("id")
        if not vid:
            continue

        sn = it.get("snippet", {}) or {}
        cd = it.get("contentDetails", {}) or {}
        st = it.get("statistics", {}) or {}

        key = (vid, category, context_id or "")
        if key in seen:
            continue
        seen.add(key)

        dur = iso_to_seconds(cd.get("duration"))
        if max_duration_seconds is not None and dur is not None and dur > max_duration_seconds:
            continue

        published_at = parse_datetime(sn.get("publishedAt") or "") or datetime.now(timezone.utc)

        clip, _ = DaenggleClip.objects.update_or_create(
            video_id=vid,
            defaults=dict(
                title=(sn.get("title") or "")[:255],
                description=sn.get("description") or "",
                channel_title=sn.get("channelTitle") or "",
                published_at=published_at,
                duration_seconds=dur,
                view_count=_to_int(st.get("viewCount")),
                like_count=_to_int(st.get("likeCount")),
                thumbnails=sn.get("thumbnails") or {},
                tags=sn.get("tags") or [],
                etag=(it.get("etag") or "")[:128],
            ),
        )

        styles, meta = infer_styles(
            title=sn.get("title") or "",
            description=sn.get("description") or "",
            tags=sn.get("tags") or [],
            category=category,
            context_name=context_name,
            min_score=1,
            max_labels=3,
        )
        if styles and (clip.styles != styles or getattr(clip, "style_meta", {}) != meta):

            DaenggleClip.objects.filter(pk=clip.pk).update(styles=styles, style_meta=meta)

        try:
            tag, created = DaenggleTag.objects.get_or_create(
                clip=clip,
                category=category,
                context_id=context_id or "",
                defaults={
                    "keyword": keyword or "",
                    "context_name": context_name or "",
                },
            )
        except IntegrityError:

            tag = DaenggleTag.objects.get(
                clip=clip, category=category, context_id=context_id or ""
            )
            created = False

        if context_name and tag.context_name != context_name:
            DaenggleTag.objects.filter(pk=tag.pk).update(context_name=context_name)

        saved += 1

    return saved

def sync_keywords(
    keywords: List[str],
    *,
    days: int = 60,
    pages: int = 1,
    max_duration_seconds: Optional[int] = 60,
    category: str = DaenggleTag.Category.KEYWORD,
    context_id: str = "",
    context_name: str = "",
) -> Dict:

    client = YouTubeClient()
    published_after = days_ago_rfc3339(days)

    runs = []
    total_found = 0
    total_saved = 0

    for kw in [k.strip() for k in (keywords or []) if k and k.strip()]:
        all_ids: List[str] = []
        next_token: Optional[str] = None

        for _ in range(max(1, pages)):
            resp = client.search_video_ids(
                q=kw,
                published_after_iso=published_after,
                page_token=next_token,
                max_results=50,
                order="date",
                region_code=getattr(settings, "YOUTUBE_REGION_CODE", None),
                relevance_lang=getattr(settings, "YOUTUBE_RELEVANCE_LANG", None),
            )
            all_ids.extend(resp["video_ids"])
            next_token = resp.get("next_page_token")
            if not next_token:
                break

        seen = set()
        deduped_ids: List[str] = []
        for vid in all_ids:
            if vid and vid not in seen:
                seen.add(vid)
                deduped_ids.append(vid)

        saved = 0

        for i in range(0, len(deduped_ids), 50):
            batch_ids = deduped_ids[i : i + 50]
            details = client.get_videos_details(batch_ids)
            saved += _upsert_batch(
                details,
                category=category,
                keyword=kw,
                context_id=context_id,
                context_name=context_name,
                max_duration_seconds=max_duration_seconds,
            )

        runs.append({"keyword": kw, "found": len(deduped_ids), "saved": saved})
        total_found += len(deduped_ids)
        total_saved += saved

    return {"runs": runs, "totalFound": total_found, "totalSaved": total_saved}
