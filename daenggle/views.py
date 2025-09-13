from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from django.db.models import Q, Subquery
from rest_framework.permissions import IsAuthenticated
from daenggle.models import DaenggleClip, DaenggleTag

from rest_framework.exceptions import ValidationError
from common.exceptions import AppError

from daenggle.service.query import list_shorts
from members.models import MemberPreference
from daenggle.serializers import ShortsQuery, RegionShortsQuery, ConceptQuery
from daenggle.presets import CURATION_TILES as CONCEPT_PRESETS, REGION_NAME_BY_ID

class ShortsListView(APIView):
    @swagger_auto_schema(operation_summary="섹션별 댕글 영상 조회",
                         operation_description="섹션(장소/숙소/트렌드)별 댕글 영상 목록을 조회합니다.",
                         tags=["Daenggle"],
                         query_serializer=ShortsQuery)
    def get(self, request):
        s = ShortsQuery(data=request.query_params)
        s.is_valid(raise_exception=True)
        q = s.validated_data

        if q["type"] == "keyword" and not q.get("keyword"):
            raise AppError("type=keyword 인 경우 keyword는 필수입니다.",
                           status_code=400, code="KEYWORD_REQUIRED")

        res = list_shorts(
            q["type"],
            context_id=q.get("contextId") or None,
            keyword=q.get("keyword") or None,
            days=q.get("days"),
            max_duration=q.get("maxDuration"),
            limit=q["limit"],
            offset=q["offset"],
            sort=q["sort"],
        )
        request._resp_message = "섹션별 댕글 영상"
        return Response(res)


class RegionShortsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="지역 + 사용자 선호 여행 스타일 기반 댕글 영상",
        operation_description="contextId(지역) 별로 큐레이션 기반 사용자 여행 스타일에 어울리는 댕글 영상을 조회합니다.",
        tags=["Daenggle"],
        query_serializer=RegionShortsQuery,
    )
    def get(self, request):
        q = RegionShortsQuery(data=request.query_params)
        q.is_valid(raise_exception=True)
        d = q.validated_data


        try:
            pref = MemberPreference.objects.get(user=request.user)
            style_codes = list(pref.style_codes or [])
        except MemberPreference.DoesNotExist:
            style_codes = []


        clip_ids_sub = DaenggleTag.objects.filter(
            category=DaenggleTag.Category.PLACE,
            context_id=d["contextId"],
        ).values("clip_id")

        qs = DaenggleClip.objects.filter(id__in=Subquery(clip_ids_sub))


        if style_codes:
            q_any = Q()
            for code in style_codes:
                q_any |= Q(styles__contains=[code])
            qs = qs.filter(q_any)

        exclude_ids = d.get("excludeIds") or []
        if exclude_ids:
            qs = qs.exclude(video_id__in=list(set(exclude_ids)))


        sort = d["sort"]
        if sort == "recent":
            qs = qs.order_by("-published_at", "-id")
        elif sort == "views":
            qs = qs.order_by("-view_count", "-id")
        else:
            qs = qs.order_by("-published_at", "-view_count", "-id")

        limit = d["limit"]; offset = d["offset"]
        rows = list(qs[offset: offset + limit + 1])
        items = rows[:limit]
        has_more = len(rows) > len(items)


        data_items = [{
            "video_id": c.video_id,
            "title": c.title,
            "authorName": c.channel_title,
            "thumbnails": c.thumbnails,
            "styles": c.styles or [],
            "playbackUrl": f"https://www.youtube.com/watch?v={c.video_id}",
            "placePill": DaenggleTag.objects.filter(
                clip=c, category=DaenggleTag.Category.PLACE, context_id=d["contextId"]
            ).values_list("context_name", flat=True).first() or None,
            "caption": (c.description or "")[:140],
            "published_at": c.published_at,
            "duration_seconds": c.duration_seconds,
            "tags": c.tags or [],
        } for c in items]

        request._resp_message = "지역/스타일 기반 댕글 영상"
        return Response({
            "items": data_items,
            "nextCursor": "",
            "hasMore": has_more,
        })


def _cx_styles_any_q(style_codes):
    q = Q()
    for s in style_codes or []:
        q |= Q(styles__contains=[s])  # JSONField(list) ANY-OF
    return q


def _cx_keywords_any_q(keywords):
    q = Q()
    for kw in keywords or []:
        k = (kw or "").strip()
        if not k:
            continue
        q |= (Q(title__icontains=k) | Q(description__icontains=k) | Q(tags__contains=[k]))
    return q


def _cx_apply_place_filter(qs, place_context_ids):
    if not place_context_ids:
        return qs
    sub = DaenggleTag.objects.filter(
        category=DaenggleTag.Category.PLACE,
        context_id__in=place_context_ids,
    ).values("clip_id")
    return qs.filter(id__in=Subquery(sub))


def _cx_pick_thumb(thumbnails: dict, target_w: int = 720):
    order = ["maxres", "standard", "high", "medium", "default"]
    for k in order:
        t = (thumbnails or {}).get(k)
        if t and t.get("url") and (t.get("width") or 0) >= target_w:
            return t["url"]
    for k in order:
        t = (thumbnails or {}).get(k)
        if t and t.get("url"):
            return t["url"]
    return None


class ConceptShortsView(APIView):
    @swagger_auto_schema(
        operation_summary="컨셉별 영상 추천 (컨셉당 N개)",
        tags=["Daenggle"],
        query_serializer=ConceptQuery,
    )
    def get(self, request):
        s = ConceptQuery(data=request.query_params)
        s.is_valid(raise_exception=True)
        q = s.validated_data

        req_keys = set(q.get("conceptKeys") or [])
        concepts = [c for c in CONCEPT_PRESETS if not req_keys or c["key"] in req_keys]
        limit = q["limitPerConcept"]

        shelves = []
        for concept in concepts:
            filters = concept.get("filters") or {}

            sub_concept = DaenggleTag.objects.filter(
                category=DaenggleTag.Category.KEYWORD,
                context_id=f"CONCEPT_{concept['key']}",
            ).values("clip_id")

            qs = DaenggleClip.objects.filter(id__in=Subquery(sub_concept))

            qs = qs.order_by("-published_at", "-view_count", "-id")
            clips = list(qs[:limit])

            if not clips:
                qs2 = DaenggleClip.objects.all()

                kw_q = _cx_keywords_any_q(filters.get("keywords_any") or [])
                if kw_q:
                    qs2 = qs2.filter(kw_q)
                qs2 = qs2.order_by("-published_at", "-view_count", "-id")
                clips = list(qs2[:limit])

            place_pill = None
            ctxs = filters.get("place_context_ids") or []
            if len(ctxs) == 1:
                place_pill = REGION_NAME_BY_ID.get(ctxs[0])

            items = [{
                "clipId": c.id,
                "videoId": c.video_id,
                "title": c.title,
                "channelTitle": c.channel_title,
                "publishedAt": c.published_at,
                "durationSeconds": c.duration_seconds,
                "viewCount": c.view_count,
                "thumbnailUrl": _cx_pick_thumb(c.thumbnails, 720),
                "watchUrl": f"https://www.youtube.com/watch?v={c.video_id}",
                "tags": c.tags or [],
                "styles": c.styles or [],
                "placePill": place_pill,
            } for c in clips]

            shelves.append({
                "key": concept["key"],
                "title": concept["title"],
                "hashtag": concept.get("hashtag"),
                "items": items,
            })

        request._resp_message = "컨셉별 영상 추천"
        return Response({"shelves": shelves})