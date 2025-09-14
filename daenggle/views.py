from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from django.utils import timezone

from django.db.models import Count
from django.contrib.contenttypes.models import ContentType
from scraps.models import Scrap

from django.db.models import Q, Subquery
from rest_framework.permissions import IsAuthenticated
from daenggle.models import DaenggleClip, DaenggleTag

from members.models import MemberPreference
from .serializers import RegionShortsQuery, ConceptQuery, TrendingShortsQuery, AccommodationShortsQuery
from .presets import CURATION_TILES as CONCEPT_PRESETS, REGION_NAME_BY_ID

def _order_by(sort: str):
    if sort == "views":
        return ["-view_count", "-id"]
    if sort == "recent":
        return ["-published_at", "-id"]
    return ["-published_at", "-view_count", "-id"]

def _fmt_yymmdd(dt):
    if not dt:
        return None
    return timezone.localtime(dt).strftime("%y-%m-%d")

def _scrap_maps_for_clips(user, clip_pk_list):
    if not clip_pk_list:
        return {}, set()
    ct = ContentType.objects.get_for_model(DaenggleClip)

    counts = (Scrap.objects
              .filter(content_type=ct, object_id__in=clip_pk_list)
              .values("object_id").annotate(cnt=Count("id")))
    scrap_count_map = {r["object_id"]: r["cnt"] for r in counts}

    user_scrapped_set = set()
    if getattr(user, "is_authenticated", False):
        user_scrapped_set = set(
            Scrap.objects.filter(user=user, content_type=ct, object_id__in=clip_pk_list)
                         .values_list("object_id", flat=True)
        )
    return scrap_count_map, user_scrapped_set


class AccommodationShortsView(APIView):
    @swagger_auto_schema(
        operation_summary="숙소 댕글 영상 조회",
        operation_description="ACCOMMODATION 태그 기반. contextId를 주면 해당 숙소, 비우면 숙소 전체 추천.",
        tags=["Daenggle"],
        query_serializer=AccommodationShortsQuery,
    )
    def get(self, request):
        s = AccommodationShortsQuery(data=request.query_params)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        tag_qs = DaenggleTag.objects.filter(category=DaenggleTag.Category.ACCOMMODATION)

        clip_ids_sub = tag_qs.values("clip_id")
        qs = DaenggleClip.objects.filter(id__in=Subquery(clip_ids_sub))

        qs = qs.order_by(*_order_by(d["sort"]))
        limit, offset = d["limit"], d["offset"]
        rows = list(qs[offset: offset + limit + 1])
        items = rows[:limit]
        has_more = len(rows) > len(items)

        clip_pk_list = [c.id for c in items]
        scrap_count_map, user_scrapped_set = _scrap_maps_for_clips(request.user, clip_pk_list)

        data_items = [{
            "video_id": c.video_id,
            "title": c.title,
            "authorName": c.channel_title,
            "playbackUrl": f"https://www.youtube.com/watch?v={c.video_id}",
            "loveCount": (c.like_count or 0),
            "caption": (c.description or "")[:140],
            "published_at": _fmt_yymmdd(c.published_at),
            "isScrapped": (c.id in user_scrapped_set),
            "scrapCount": scrap_count_map.get(c.id, 0),
        } for c in items]

        request._resp_message = "숙소 댕글 영상"
        return Response({
            "items": data_items,
            "nextCursor": "",
            "hasMore": has_more,
        })

class RegionPlainShortsView(APIView):
    @swagger_auto_schema(
        operation_summary="지역별 댕글 영상 조회",
        operation_description="PLACE 태그 기반으로 지역 별 댕글 영상을 조회합니다.",
        tags=["Daenggle"],
        query_serializer=RegionShortsQuery,
    )
    def get(self, request):
        q = RegionShortsQuery(data=request.query_params)
        q.is_valid(raise_exception=True)
        d = q.validated_data

        clip_ids_sub = DaenggleTag.objects.filter(
            category=DaenggleTag.Category.PLACE,
            context_id=d["contextId"],
        ).values("clip_id")

        qs = DaenggleClip.objects.filter(id__in=Subquery(clip_ids_sub))

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

        place_pill = DaenggleTag.objects.filter(
            category=DaenggleTag.Category.PLACE,
            context_id=d["contextId"],
        ).values_list("context_name", flat=True).first()

        clip_pk_list = [c.id for c in items]
        scrap_count_map, user_scrapped_set = _scrap_maps_for_clips(request.user, clip_pk_list)

        data_items = [{
            "video_id": c.video_id,
            "title": c.title,
            "authorName": c.channel_title,
            "playbackUrl": f"https://www.youtube.com/watch?v={c.video_id}",
            "placePill": place_pill,
            "caption": (c.description or "")[:140],
            "published_at": _fmt_yymmdd(c.published_at),
            "isScrapped": (c.id in user_scrapped_set),
            "scrapCount": scrap_count_map.get(c.id, 0),
            "tags": c.tags or [],
        } for c in items]

        request._resp_message = "지역별 댕글 영상 조회"
        return Response({
            "items": data_items,
            "nextCursor": "",
            "hasMore": has_more,
        })


class TrendingShortsView(APIView):
    @swagger_auto_schema(
        operation_summary="트렌딩(조회수 높은) 댕글 영상",
        operation_description="TREND 태그 기반. days로 최근 N일 제한 가능.",
        tags=["Daenggle"],
        query_serializer=TrendingShortsQuery,
    )
    def get(self, request):
        s = TrendingShortsQuery(data=request.query_params)
        s.is_valid(raise_exception=True)
        d = s.validated_data


        clip_ids_sub = DaenggleTag.objects.filter(
            category=DaenggleTag.Category.TREND
        ).values("clip_id")

        qs = DaenggleClip.objects.filter(id__in=Subquery(clip_ids_sub))

        qs = qs.order_by(*_order_by(d["sort"]))
        limit, offset = d["limit"], d["offset"]
        rows = list(qs[offset: offset + limit + 1])
        items = rows[:limit]
        has_more = len(rows) > len(items)

        clip_pk_list = [c.id for c in items]
        scrap_count_map, user_scrapped_set = _scrap_maps_for_clips(request.user, clip_pk_list)

        data_items = [{
            "video_id": c.video_id,
            "title": c.title,
            "authorName": c.channel_title,
            "playbackUrl": f"https://www.youtube.com/watch?v={c.video_id}",
            "caption": (c.description or "")[:140],
            "published_at": _fmt_yymmdd(c.published_at),
            "isScrapped": (c.id in user_scrapped_set),
            "scrapCount": scrap_count_map.get(c.id, 0),
            "tags": c.tags or [],
        } for c in items]

        request._resp_message = "조회수 탑 10 댕글 영상"
        return Response({
            "items": data_items,
            "nextCursor": "",
            "hasMore": has_more,
        })



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

        clip_pk_list = [c.id for c in items]
        scrap_count_map, user_scrapped_set = _scrap_maps_for_clips(request.user, clip_pk_list)

        data_items = [{
            "video_id": c.video_id,
            "title": c.title,
            "authorName": c.channel_title,
            "styles": c.styles or [],
            "playbackUrl": f"https://www.youtube.com/watch?v={c.video_id}",
            "placePill": DaenggleTag.objects.filter(
                clip=c, category=DaenggleTag.Category.PLACE, context_id=d["contextId"]
            ).values_list("context_name", flat=True).first() or None,
            "caption": (c.description or "")[:140],
            "published_at": _fmt_yymmdd(c.published_at),
            "isScrapped": (c.id in user_scrapped_set),
            "scrapCount": scrap_count_map.get(c.id, 0),
            "duration_seconds": c.duration_seconds,
            "tags": c.tags or [],
        } for c in items]

        request._resp_message = "지역별 사용자 스타일 기반 댕글 영상"
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