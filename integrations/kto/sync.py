# integrations/kto/sync.py
import os
import re
from typing import Optional, Tuple, Set, Dict, List
from django.db import transaction

from .client import KTOClient, items_as_list
from places.models import AreaCode, CategoryCode, Place, PlaceImage, PetPolicy


def _item_first(body: Dict) -> Optional[Dict]:
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
    m = re.search(r'href=[\'"]([^\'"]+)[\'"]', v)  # <a href="...">
    return m.group(1) if m else v

_KR_TEL_RE = re.compile(r'(0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4})')

def _extract_tel_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    m = _KR_TEL_RE.search(text)
    if not m:
        return None
    return m.group(1).replace(" ", "-")

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

def _parse_bool_like(v: Optional[str]) -> Optional[bool]:
    if not v:
        return None
    s = str(v).strip().lower()
    yes = {"y","yes","true","1","가능","사용","가능함","o","ok","가능합니다","사용가능","가능해요"}
    no  = {"n","no","false","0","불가","사용불가","사용 안함","x","불가능","불가함","불가능함"}
    if s in yes: return True
    if s in no:  return False
    return None

def _pick_first(d: Dict, keys: List[str]) -> Tuple[Optional[str], Set[str]]:
    used: Set[str] = set()
    for k in keys:
        if k in d and d[k] not in (None, "", []):
            used.add(k)
            return str(d[k]), used
    return None, used

def _canon_from_intro(content_type_id: Optional[int], intro_item: Dict) -> Tuple[Dict, Set[str]]:

    used: Set[str] = set()
    pickmap: Dict[str, List[str]] = {
        "usetime":      ["usetime", "opentimefood", "opentime", "usetimeleports"],
        "restdate":     ["restdate", "restdatefood", "restdateshopping", "restdateleports"],
        "opendate":     ["opendate"],
        "useseason":    ["useseason"],
        "accomcount":   ["accomcount", "roomcount"],
        "expagerange":  ["expagerange"],
        "expguide":     ["expguide"],
        "chkcreditcard":["chkcreditcard","chkcreditcardfood","chkcreditcardshopping",
                         "chkcreditcardculture","chkcreditcardleports","chkcreditcardlodging"],

        "infocenter":   ["infocenter","infocenterfood","infocentershopping",
                         "infocenterculture","infocenterleports","infocenterlodging"],
    }

    parking_keys = [k for k in intro_item.keys() if "parking" in k.lower()]
    if parking_keys:
        pickmap["parking"] = parking_keys

    out: Dict[str, Optional[str]] = {}
    for canon, keys in pickmap.items():
        val, u = _pick_first(intro_item, keys)
        if u:
            used |= set(keys)
        if val:
            out[canon] = val


    out["accepts_card"] = _parse_bool_like(out.get("chkcreditcard"))
    return out, used

def _slim_intro(intro_item: Dict, used_keys: Set[str]) -> Dict:

    if not isinstance(intro_item, dict):
        return {}
    slim = {}
    for k, v in intro_item.items():
        if k in used_keys:
            continue
        if v in (None, "", []):
            continue
        slim[k] = v
    return slim

def _clean_common_for_meta(common_item: Dict) -> Dict:

    if not isinstance(common_item, dict):
        return {}
    drop = {
        "title","contentid","contenttypeid",
        "addr1","mapx","mapy","map_x","map_y",
        "tel","homepage","overview",
        "firstimage","firstimage2","zipcode","modifiedtime",
    }
    return {k: v for k, v in common_item.items() if k not in drop and v not in (None, "", [])}

def _extract_parking(intro_item: Optional[Dict], info_body: Optional[Dict], overview_text: Optional[str]) -> Tuple[Optional[bool], Optional[str]]:

    texts: List[str] = []

    if isinstance(intro_item, dict):
        for k, v in intro_item.items():
            if v and "parking" in k.lower():
                texts.append(str(v))

    if isinstance(info_body, dict):
        for row in items_as_list(info_body):
            name = (row.get("infoname") or row.get("name") or "").strip()
            val  = (row.get("infotext") or row.get("value") or "").strip()
            if not (name or val):
                continue
            if ("주차" in name) or ("parking" in name.lower()) or ("주차" in val) or ("parking" in val.lower()):
                texts.append(f"{name} {val}".strip())

    if overview_text and ("주차" in overview_text or "parking" in overview_text.lower()):
        texts.append("overview: " + overview_text)


    def _norm(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip()[:280]
    texts = [t for t in map(_norm, texts) if t]
    note = "; ".join(dict.fromkeys(texts)) or None

    joined = " ".join(texts)
    low = joined.lower()


    if any(x in joined for x in ("주차 불가", "주차없음", "주차 없음", "불가")) or \
       any(x in low for x in ("no parking", "not available", "unavailable")):
        return (False, note)

    if any(x in joined for x in ("주차 가능", "주차장", "가능", "무료")) or \
       any(x in low for x in ("parking available", "available", "free parking", "parking lot")):
        return (True, note)

    if ("유료" in joined) or ("paid" in low):
        return (True, note or "유료")

    return (None, note)


def sync_area_and_sigungu(cli: KTOClient):
    body = cli.get("areaCode", pageNo=1, numOfRows=1000)
    for area in items_as_list(body):
        AreaCode.objects.update_or_create(
            area_code=area["code"], sigungu_code=None, defaults={"name": area["name"]}
        )
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
    place = None
    if content_type_id is None:
        try:
            place = Place.objects.get(content_id=content_id)
            if place.content_type_id:
                content_type_id = place.content_type_id
        except Place.DoesNotExist:
            place = None


    common = cli.get(
        "detailCommon",
        contentId=content_id,
        defaultYN="Y", addrinfoYN="Y", mapinfoYN="Y", overviewYN="Y",
    )
    common_item = _item_first(common)


    if content_type_id is None and isinstance(common_item, dict):
        try:
            content_type_id = int(common_item.get("contenttypeid") or 0) or None
        except (TypeError, ValueError):
            content_type_id = None


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
            pass


    if content_type_id:
        intro_body = cli.get("detailIntro", contentId=content_id, contentTypeId=content_type_id)
        info_body  = cli.get("detailInfo",  contentId=content_id, contentTypeId=content_type_id)
        intro_item = _item_first(intro_body)
        info_item  = _item_first(info_body)
    else:
        intro_body = info_body = None
        intro_item = info_item = None


    images = cli.get("detailImage", contentId=content_id, numOfRows=50, pageNo=1)
    pet    = cli.get("detailPetTour", contentId=content_id)


    overview  = (common_item or {}).get("overview")
    homepage  = _pick_homepage(common_item)
    tel_value = _pick_tel(content_type_id, common_item, intro_item)
    has_parking, parking_note = _extract_parking(intro_item, info_body, overview)

    canon, used_keys = ({}, set())
    if isinstance(intro_item, dict):
        canon, used_keys = _canon_from_intro(content_type_id, intro_item)

    # 5) 저장
    with transaction.atomic():
        if place is None:
            place, _ = Place.objects.get_or_create(
                content_id=content_id,
                defaults={"content_type_id": content_type_id or 0, "title": str(content_id)},
            )

        if content_type_id and place.content_type_id != content_type_id:
            place.content_type_id = content_type_id

        # 개요/홈페이지/전화
        if overview:
            place.overview = overview
        if homepage and not (place.homepage or "").strip():
            place.homepage = homepage
        if tel_value and not (place.tel or "").strip():
            place.tel = tel_value

        # 주차
        if has_parking is not None:
            place.has_parking = has_parking
        if parking_note and (not place.parking_note or len(place.parking_note) < len(parking_note)):
            place.parking_note = parking_note[:300]

        # intro 정규화 컬럼 저장
        for f in ("usetime","restdate","opendate","useseason","accomcount","expagerange","expguide","chkcreditcard"):
            val = canon.get(f)
            if val:
                setattr(place, f, val)
        if "accepts_card" in canon and canon["accepts_card"] is not None:
            place.accepts_card = canon["accepts_card"]

        # 주소/좌표 및 meta_common 슬림 저장
        if isinstance(common_item, dict):
            if common_item.get("addr1"): place.addr1 = common_item["addr1"]
            mx, my = _to_float(common_item.get("mapx")), _to_float(common_item.get("mapy"))
            if mx is not None: place.mapx = mx
            if my is not None: place.mapy = my
            place.meta_common = _clean_common_for_meta(common_item)

        # meta_intro는 정규화로 옮기지 않은 키만
        if isinstance(intro_item, dict):
            place.meta_intro = _slim_intro(intro_item, used_keys)

        # 반복 정보는 기존처럼 첫 아이템(원하면 info_body 전체로 바꿔도 됨)
        if info_item:
            place.meta_info = info_item

        place.save()

        # 이미지
        for im in items_as_list(images):
            origin = im.get("originimgurl") or im.get("firstimage")
            thumb  = im.get("smallimageurl") or im.get("firstimage2")
            if origin:
                PlaceImage.objects.get_or_create(place=place, origin=origin, defaults={"thumb": thumb})

        # 반려동물 정책
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

# ---------- (4) 증분/부트스트랩 ----------

def run_incremental(cli: KTOClient, modified_yyyymmdd: str, showflag: int = 1, num_rows: int = 100) -> int:

    cli_common = KTOClient(base_url=os.getenv("KTO_BASE_URL"))

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
    cli_common = KTOClient(base_url=os.getenv("KTO_BASE_URL"))

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
