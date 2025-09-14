from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from .serializers import BatchSyncBody, YouTubeSyncRequest
from .presets import TRENDING_KEYWORDS, PLACE_PRESETS, ACCOM_PRESETS

from daenggle.presets import CURATION_TILES, REGION_NAME_BY_ID
from daenggle.service.ingest import sync_keywords
from daenggle.models import DaenggleClip, DaenggleTag

def _tile_ctx_id(key: str) -> str:
    return f"TILE_{key}"

def _tile_saved_count(key: str) -> int:
    return DaenggleTag.objects.filter(
        category=DaenggleTag.Category.KEYWORD,
        context_id=_tile_ctx_id(key),
    ).count()


class YouTubeSyncView(APIView):
    @swagger_auto_schema(
        operation_summary="서버용: YouTube 키워드 수집",
        tags=["Integration/YouTube"],
        request_body=YouTubeSyncRequest,
    )
    def post(self, request):
        ser = YouTubeSyncRequest(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        result = sync_keywords(
            d["keywords"],
            days=d["days"],
            pages=d["pages"],
            max_duration_seconds=d["maxDuration"],
            category=d["category"],
            context_id=d.get("contextId", ""),
            context_name=d.get("contextName", ""),
        )
        return Response(
            {**result, "limits": {"days": d["days"], "pages": d["pages"], "maxDuration": d["maxDuration"]}},
            status=status.HTTP_200_OK,
        )


class YouTubeBatchSyncView(APIView):
    @swagger_auto_schema(
        operation_summary="서버용: 댕글 영상 일괄 저장 - 필수 실행",
        operation_description="제주 관련 댕글 영상을 일괄 저장합니다. 댕글 영상 수집을 위해 실행해주세요. 서버용 api입니다.",
        tags=["Integration/YouTube"],
        request_body=BatchSyncBody,
    )
    def post(self, request):
        s = BatchSyncBody(data=request.data or {})
        s.is_valid(raise_exception=True)
        q = s.validated_data

        include = set(q["include"])
        days = q["days"]
        pages = q["pages"]
        max_dur = q.get("maxDuration")
        place_ids = set(q.get("placeIds") or []) or None
        acc_ids = set(q.get("accommodationIds") or []) or None

        results = {}

        # 1) 트렌딩
        if "trending" in include:
            res = sync_keywords(
                TRENDING_KEYWORDS,
                days=days,
                pages=pages,
                max_duration_seconds=max_dur,
                category=DaenggleTag.Category.TREND,
                context_id="",
                context_name="",
            )
            results["trending"] = res

        # 2) 장소별
        if "place" in include:
            place_runs = []
            for p in PLACE_PRESETS:
                if place_ids and p["context_id"] not in place_ids:
                    continue
                place_runs.append(
                    sync_keywords(
                        p["keywords"],
                        days=days,
                        pages=pages,
                        max_duration_seconds=max_dur,
                        category=DaenggleTag.Category.PLACE,
                        context_id=p["context_id"],
                        context_name=p["context_name"],
                    )
                )
            results["place"] = place_runs

        # 3) 숙소별
        if "accommodation" in include:
            acc_runs = []
            for a in ACCOM_PRESETS:
                if acc_ids and a["context_id"] not in acc_ids:
                    continue
                acc_runs.append(
                    sync_keywords(
                        a["keywords"],
                        days=days,
                        pages=pages,
                        max_duration_seconds=max_dur,
                        category=DaenggleTag.Category.ACCOMMODATION,
                        context_id=a["context_id"],
                        context_name=a["context_name"],
                    )
                )
            results["accommodation"] = acc_runs

        summary = {"totalFound": 0, "totalSaved": 0}

        def acc_total(res):
            if isinstance(res, dict):
                summary["totalFound"] += res.get("totalFound", 0)
                summary["totalSaved"] += res.get("totalSaved", 0)

        if "trending" in results:
            acc_total(results["trending"])
        for k in ("place", "accommodation"):
            for r in results.get(k, []):
                acc_total(r)

        return Response({"summary": summary, "results": results})



def _build_keywords_from_tile_filters(filters: dict):

    kws = list(filters.get("keywords_any") or [])
    for pid in filters.get("place_context_ids") or []:
        name = REGION_NAME_BY_ID.get(pid)
        if name:
            kws.extend([f"{name} 애견동반", f"{name} 반려견", f"{name} 여행", name])

    seen, out = set(), []
    for k in [k.strip() for k in kws if k and k.strip()]:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out

class TilePresetSyncView(APIView):
    DEFAULT_DAYS = 365
    DEFAULT_PAGES = 1
    DEFAULT_MAX_DURATION = 500

    MIN_TARGET_PER_TILE = 8
    MAX_TARGET_PER_TILE = 10

    @swagger_auto_schema(
        operation_summary="서버용: 타일 프리셋 영상 수집(바디 없음, 전체 타일 수집)",
        operation_description="컨셉(타일)별로 영상을 수집합니다.",
        tags=["Integration/YouTube"],
        request_body=None,
    )
    def post(self, request):
        days = self.DEFAULT_DAYS
        pages = self.DEFAULT_PAGES
        max_dur = self.DEFAULT_MAX_DURATION

        results = []
        total_found = 0
        total_saved = 0

        for t in CURATION_TILES:
            key = t["key"]
            title = t["title"]
            ctx_id = _tile_ctx_id(key)

            keywords = _build_keywords_from_tile_filters(t.get("filters") or {})

            saved_now = _tile_saved_count(key)
            runs = []

            for kw in keywords:

                if saved_now >= self.MAX_TARGET_PER_TILE:
                    break

                res = sync_keywords(
                    [kw],
                    days=days,
                    pages=pages,
                    max_duration_seconds=max_dur,
                    category=DaenggleTag.Category.KEYWORD,
                    context_id=ctx_id,
                    context_name=title,
                )

                found = int(res.get("totalFound", 0))
                saved = int(res.get("totalSaved", 0))
                total_found += found
                total_saved += saved
                runs.append({"keyword": kw, "found": found, "saved": saved})

                saved_now = _tile_saved_count(key)

            results.append({
                "key": key,
                "title": title,
                "minTarget": self.MIN_TARGET_PER_TILE,
                "maxTarget": self.MAX_TARGET_PER_TILE,
                "targetPerTile": self.MIN_TARGET_PER_TILE,  # (하위호환용 필드)
                "savedNow": saved_now,
                "keywordsUsed": keywords,
                "runs": runs,
                "limits": {"days": days, "pages": pages, "maxDuration": max_dur},
            })

        return Response({
            "summary": {
                "totalFound": total_found,
                "totalSaved": total_saved,
                "tiles": len(CURATION_TILES),
                "minTargetPerTile": self.MIN_TARGET_PER_TILE,
                "maxTargetPerTile": self.MAX_TARGET_PER_TILE,
                "targetPerTile": self.MIN_TARGET_PER_TILE,
            },
            "results": results,
        }, status=status.HTTP_200_OK)
