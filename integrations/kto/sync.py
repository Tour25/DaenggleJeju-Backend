# integrations/kto/sync.py
import os
import re
from typing import Optional
from django.db import transaction

from .client import KTOClient, items_as_list
from places.models import AreaCode, CategoryCode, Place, PlaceImage, PetPolicy


def _item_first(body):
    item = (body.get("items", {}) or {}).get("item")
    if isinstance(item, list):
        return item[0] if item else None
    return item if isinstance(item, dict) else None

def _to_float(v):
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None

def _pick_homepage(common_item: Optional[dict]) -> Optional[str]:
    if not common_item:
        return None
    v = common_item.get("homepage")
    if not v:
        return None
    m = re.search(r'href=[\'"]([^\'"]+)[\'"]', v)
    return m.group(1) if m else v

_KR_TEL_RE = re.compile(r'(0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4})')

def _extract_tel_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    m = _KR_TEL_RE.search(text)
    if not m:
        return None
    return m.group(1).replace(' ', '-')

def _pick_tel(content_type_id: Optional[int], common_item: Optional[dict], intro_item: Optional[dict]) -> Optional[str]:

    if common_item and common_item.get("tel"):
        return common_item.get("tel")

    intro_keys = [
        "infocenter", "infocenterculture", "infocenterfood",
        "infocenterlodging", "infocentershopping", "infocenterleports"
    ]
    if intro_item:
        for k in intro_keys:
            if intro_item.get(k):
                return intro_item.get(k)

    if common_item and common_item.get("overview"):
        found = _extract_tel_from_text(common_item["overview"])
        if found:
            return found
    return None


def sync_area_and_sigungu(cli: KTOClient):
    body = cli.get("areaCode", pageNo=1, numOfRows=1000)
    for area in items_as_list(body):
        # 광역
        AreaCode.objects.update_or_create(
            area_code=area["code"], sigungu_code=None, defaults={"name": area["name"]}
        )
        # 시군구
        sub = cli.get("areaCode", areaCode=area["code"], pageNo=1, numOfRows=1000)
        for s in items_as_list(sub):
            AreaCode.objects.update_or_create(
                area_code=area["code"], sigungu_code=s["code"], defaults={"name": s["name"]}
            )

def sync_category(cli: KTOClient):
    for ctype in (12, 14, 15, 28, 32, 38, 39):
        body = cli.get("categoryCode", contentTypeId=ctype)
        for cat in items_as_list(body):
            CategoryCode.objects.update_or_create(
                content_type_id=ctype,
                cat1=cat.get("cat1"),
                cat2=cat.get("cat2"),
                cat3=cat.get("cat3"),
                defaults={"name": cat.get("name", "")},
            )


def upsert_place_from_list(item) -> Place:
    place, _ = Place.objects.update_or_create(
        content_id=int(item["contentid"]),
        defaults={
            "content_type_id": int(item.get("contenttypeid") or 0),
            "title": item.get("title") or "",
            "addr1": item.get("addr1"),
            "mapx": _to_float(item.get("mapx")),
            "mapy": _to_float(item.get("mapy")),
            "modified_time": item.get("modifiedtime"),
            "has_image": bool(item.get("firstimage")),
        },
    )
    return place


def enrich_detail(
    cli: KTOClient,
    content_id: int,
    content_type_id: Optional[int] = None,
    cli_common: Optional[KTOClient] = None,  # KorService 폴백
):
    """
    Intro/Info는 contentTypeId 필수 → 반드시 확보해서 호출
    우선순위: 인자 > DB Place.content_type_id > (PetTour)detailCommon > (KorService)detailCommon
    """
    place = None
    if content_type_id is None:
        try:
            place = Place.objects.get(content_id=content_id)
            if place.content_type_id:
                content_type_id = place.content_type_id
        except Place.DoesNotExist:
            place = None

    # 1) PetTour detailCommon
    common = cli.get(
        "detailCommon",
        contentId=content_id,
        defaultYN="Y", addrinfoYN="Y", mapinfoYN="Y", overviewYN="Y",
    )
    common_item = _item_first(common)

    # contentTypeId 확보
    if content_type_id is None and isinstance(common_item, dict):
        try:
            content_type_id = int(common_item.get("contenttypeid") or 0) or None
        except (TypeError, ValueError):
            content_type_id = None

    # 1-보강) overview/homepage/tel 모두 비면 KorService로 폴백
    need_fallback = (not common_item) or (
        not (common_item.get("overview") or common_item.get("homepage") or common_item.get("tel"))
    )
    if need_fallback and cli_common is not None:
        try:
            common2 = cli_common.get(
                "detailCommon",
                contentId=content_id,
                defaultYN="Y", addrinfoYN="Y", mapinfoYN="Y", overviewYN="Y",
            )
            ci2 = _item_first(common2)
            if ci2:
                if not common_item:
                    common_item = ci2
                else:
                    for k in ("overview", "homepage", "tel", "addr1", "mapx", "mapy", "contenttypeid"):
                        if not common_item.get(k) and ci2.get(k):
                            common_item[k] = ci2[k]
                if content_type_id is None and ci2.get("contenttypeid"):
                    try:
                        content_type_id = int(ci2["contenttypeid"])
                    except Exception:
                        pass
        except Exception:
            pass  # 폴백 실패는 무시

    # 2) intro/info (ctid 있을 때만)
    if content_type_id:
        intro = cli.get("detailIntro", contentId=content_id, contentTypeId=content_type_id)
        info  = cli.get("detailInfo",  contentId=content_id, contentTypeId=content_type_id)
        intro_item = _item_first(intro)
        info_item  = _item_first(info)
    else:
        intro_item = info_item = None

    # 3) image/pet
    images = cli.get("detailImage", contentId=content_id, numOfRows=50, pageNo=1)
    pet    = cli.get("detailPetTour", contentId=content_id)

    # 4) 추출/정제
    overview  = (common_item or {}).get("overview")
    homepage  = _pick_homepage(common_item)
    tel_value = _pick_tel(content_type_id, common_item, intro_item)

    # 5) 저장
    with transaction.atomic():
        if place is None:
            place, _ = Place.objects.get_or_create(
                content_id=content_id,
                defaults={"content_type_id": content_type_id or 0, "title": str(content_id)},
            )

        if content_type_id and place.content_type_id != content_type_id:
            place.content_type_id = content_type_id

        # 빈 문자열로 저장된 경우도 덮어쓰도록 처리
        if overview:
            place.overview = overview
        if homepage and not (place.homepage or "").strip():
            place.homepage = homepage
        if tel_value and not (place.tel or "").strip():
            place.tel = tel_value

        if isinstance(common_item, dict):
            if common_item.get("addr1"): place.addr1 = common_item["addr1"]
            mx, my = _to_float(common_item.get("mapx")), _to_float(common_item.get("mapy"))
            if mx is not None: place.mapx = mx
            if my is not None: place.mapy = my
            place.meta_common = common_item  # 원문 보존 (homepage의 <a> 포함)

        if intro_item: place.meta_intro = intro_item
        if info_item:  place.meta_info  = info_item
        place.save()

        for im in items_as_list(images):
            origin = im.get("originimgurl") or im.get("firstimage")
            thumb  = im.get("smallimageurl") or im.get("firstimage2")
            if origin:
                PlaceImage.objects.get_or_create(place=place, origin=origin, defaults={"thumb": thumb})

        pet_items = items_as_list(pet)
        if pet_items:
            p0 = pet_items[0]
            PetPolicy.objects.update_or_create(
                place=place,
                defaults={
                    "acmpy_type_cd": p0.get("acmpyTypeCd"),
                    "etc_info": p0.get("etcAcmpyInfo"),
                },
            )


def run_incremental(cli: KTOClient, modified_yyyymmdd: str, showflag: int = 1, num_rows: int = 100) -> int:
    # KorService 폴백 클라이언트
    cli_common = KTOClient(base_url=os.getenv("KTO_BASE_URL_COMMON", "https://apis.data.go.kr/B551011/KorService1"))

    page, processed = 1, 0
    while True:
        body = cli.get(
            "petTourSyncList",
            modifiedtime=modified_yyyymmdd,
            showflag=showflag,
            pageNo=page,
            numOfRows=num_rows,
            listYN="Y",
            arrange="C",
        )
        items = items_as_list(body)
        if not items:
            break

        for it in items:
            place = upsert_place_from_list(it)
            ctid = int(it.get("contenttypeid") or place.content_type_id or 0) or None
            enrich_detail(cli, int(it["contentid"]), ctid, cli_common=cli_common)
            processed += 1

        if len(items) < num_rows:
            break
        page += 1

    return processed


def run_bootstrap_area(
    cli: KTOClient,
    area_code: str,
    sigungu_code: Optional[str] = "",
    num_rows: int = 100,
    max_pages: int = 999,
) -> int:
    cli_common = KTOClient(base_url=os.getenv("KTO_BASE_URL_COMMON", "https://apis.data.go.kr/B551011/KorService1"))

    page, done = 1, 0
    while page <= max_pages:
        body = cli.get(
            "areaBasedList",
            listYN="Y",
            arrange="C",
            areaCode=area_code,
            sigunguCode=sigungu_code or "",
            numOfRows=num_rows,
            pageNo=page,
        )
        items = items_as_list(body)
        if not items:
            break

        for it in items:
            place = upsert_place_from_list(it)
            ctid = int(it.get("contenttypeid") or place.content_type_id or 0) or None
            enrich_detail(cli, int(it["contentid"]), ctid, cli_common=cli_common)
            done += 1

        if len(items) < num_rows:
            break
        page += 1

    return done
