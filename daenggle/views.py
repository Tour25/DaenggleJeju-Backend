from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from django.utils import timezone
import re
from django.db.models import Q, Case, When, Value, IntegerField
from rest_framework import status

from places.models import Place
from .place_daenggle_presets import PLACE_DAENGGLE_VIDEOS

from django.db.models import Count
from django.contrib.contenttypes.models import ContentType
from scraps.models import Scrap

from django.db.models import Q, Subquery
from rest_framework.permissions import IsAuthenticated
from .models import DaenggleClip, DaenggleTag, PlaceDaenggle

from members.models import MemberPreference
from .serializers import RegionShortsQuery, ConceptQuery, TrendingShortsQuery, AccommodationShortsQuery, ShortsSearchQuery, PlaceDaenggleResponseSerializer
from daenggle.presets import CURATION_TILES as CONCEPT_PRESETS, REGION_NAME_BY_ID

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

def _z2(v) -> str:
    if v in (None, "", 0):
        return "00"
    s = str(v)
    return s.zfill(2) if s.isdigit() and len(s) <= 2 else s


_SUFFIX_RX = re.compile(r"(.+?)(시|군|구|읍|면|동|리|로|길|해변|해수욕장|공원|오름|항)$")

def _addr_terms(place) -> list[str]:
    base = f"{(place.addr1 or '').strip()} {(place.title or '').strip()}".strip()
    s = re.sub(r"[(),]", " ", base)
    s = re.sub(r"\s+", " ", s)
    toks = set()
    for p in s.split(" "):
        p = p.strip()
        if len(p) < 2:
            continue
        toks.add(p)
        m = _SUFFIX_RX.match(p)
        if m:
            toks.add(m.group(1))
    return list(toks)


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


class ConceptShortsView(APIView):
    @swagger_auto_schema(
        operation_summary="컨셉별 댕글 영상 조회",
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
            sub_concept = (
                DaenggleTag.objects
                .filter(category=DaenggleTag.Category.KEYWORD,
                        context_id=f"TILE_{concept['key']}")
                .values("clip_id")
            )
            qs = (DaenggleClip.objects
                  .filter(id__in=Subquery(sub_concept))
                  .order_by("-published_at", "-view_count", "-id"))
            clips = list(qs[:limit])

            filters = concept.get("filters") or {}
            place_pill = None
            ctxs = filters.get("place_context_ids") or []
            if len(ctxs) == 1:
                place_pill = REGION_NAME_BY_ID.get(ctxs[0])

            clip_pk_list = [c.id for c in clips]
            scrap_count_map, user_scrapped_set = _scrap_maps_for_clips(request.user, clip_pk_list)

            items = [{
                "videoId": c.video_id,
                "title": c.title,
                "channelTitle": c.channel_title,
                "publishedAt": _fmt_yymmdd(c.published_at),
                "playbackUrl": f"https://www.youtube.com/watch?v={c.video_id}",
                "isScrapped": (c.id in user_scrapped_set),
                "scrapCount": scrap_count_map.get(c.id, 0),
                "tags": c.tags or [],
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


def _split_terms(q: str):
    return [t for t in re.split(r"[\s,]+", (q or "").strip()) if t]

class ShortsSearchView(APIView):
    @swagger_auto_schema(
        operation_summary="댕글 영상 검색",
        operation_description="제목/설명/태그를 대상으로 검색합니다.",
        tags=["Daenggle"],
        query_serializer=ShortsSearchQuery,
    )
    def get(self, request):
        s = ShortsSearchQuery(data=request.query_params)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        terms = _split_terms(d["q"])
        if not terms:
            return Response({"items": [], "hasMore": False, "nextCursor": ""})

        qs = DaenggleClip.objects.all()



        kw_filter = Q()
        for t in terms:
            kw_filter |= Q(title__icontains=t) | Q(description__icontains=t) | Q(tags__contains=[t])
        qs = qs.filter(kw_filter)

        score = Value(0, output_field=IntegerField())
        for t in terms:
            score = score + Case(
                When(title__iexact=t, then=Value(120)),
                When(title__istartswith=t, then=Value(90)),
                When(title__icontains=t, then=Value(70)),
                When(tags__contains=[t], then=Value(60)),
                When(description__icontains=t, then=Value(20)),
                default=Value(0), output_field=IntegerField(),
            )
        qs = qs.annotate(score=score)


        sort = d["sort"]
        if sort == "views":
            qs = qs.order_by("-view_count", "-published_at", "-id")
        elif sort == "recent":
            qs = qs.order_by("-published_at", "-id")
        else:
            qs = qs.order_by("-score", "-view_count", "-published_at", "-id")


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
            "published_at": _fmt_yymmdd(c.published_at),
            "playbackUrl": f"https://www.youtube.com/watch?v={c.video_id}",
            "tags": c.tags or [],
            "loveCount": (c.like_count or 0),
            "isScrapped": (c.id in user_scrapped_set),
            "scrapCount": scrap_count_map.get(c.id, 0),
        } for c in items]

        request._resp_message = "댕글 영상 검색"
        return Response({"items": data_items, "hasMore": has_more, "nextCursor": ""})

class PlaceDaenggleRecommendView(APIView):
    @swagger_auto_schema(
        operation_summary="장소 연관 댕글 영상 조회",
        operation_description="해당 장소에 연관된 유튜브 영상 리스트를 반환합니다.",
        tags=["Daenggle"],
        responses={200: PlaceDaenggleResponseSerializer},
    )
    def get(self, request, contentId: int):
        try:
            place = Place.objects.get(content_id=contentId)
        except Place.DoesNotExist:
            return Response(
                {"detail": "장소를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        videos = PlaceDaenggle.objects.filter(place=place).values_list("video_id", flat=True)
        items = [
            {
                "video_id": vid,
                "playbackUrl": f"https://www.youtube.com/watch?v={vid}",
            }
            for vid in videos
        ]

        response_data = {
            "total": len(items),
            "items": items,
        }

        request._resp_message = "장소 연관 댕글 영상 조회"

        return Response(response_data, status=status.HTTP_200_OK)

class SeedPlaceDaenggleView(APIView):

    @swagger_auto_schema(
        operation_summary="서버용: 장소 연관 영상 데이터 저장",
        operation_description="장소 연관 영상 데이터를 저장합니다.",
        tags=["Daenggle"]
    )
    def post(self, request):
        created, skipped = 0, 0
        for content_id, video_ids in PLACE_DAENGGLE_VIDEOS.items():
            try:
                place = Place.objects.get(content_id=content_id)
            except Place.DoesNotExist:
                skipped += 1
                continue

            for vid in video_ids:
                _, is_created = PlaceDaenggle.objects.get_or_create(
                    place=place, video_id=vid
                )
                if is_created:
                    created += 1
        return Response({
            "status": "ok",
            "created": created,
            "skipped": skipped
        })