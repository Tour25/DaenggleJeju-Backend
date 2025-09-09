from functools import reduce
from operator import or_
from typing import Optional, Tuple, List, Dict
from math import radians, sin, cos, asin, sqrt
import re
from django.db.models import Q


from django.db.models import Q
from .constants import (
    CONTENT_TYPE_LABELS,
    SIZE_KEYWORDS,
    AREA_KEYWORDS,
    AMENITY_KEYWORDS,
    COND_KEYWORDS,
)

NO_IMAGE_TEXT = "사진 없음"

SIZE_TOKEN_TO_LABEL = {"small": "소형", "med": "중형", "large": "대형", "xlarge": "초대형", "all": "모든크기"}
AREA_TOKEN_TO_LABEL = {"indoor": "실내", "outdoor": "야외", "allarea": "모든 구역"}
COND_TOKEN_TO_LABEL = {
    "leash": "목줄 착용",
    "carrier": "이동 가방 사용",
    "leash_free": "목줄 자유",
    "diaper": "강아지 기저귀 착용",
}
AMENITY_TOKEN_TO_LABEL = {
    "bbq": "바베큐",
    "wifi": "무선인터넷",
    "takeout": "테이크아웃",
    "yard": "마당",
    "pets_zone": "애견 전용 공간",
    "jacuzzi": "자쿠지",
}

def parse_bbox(bbox_str: str) -> Tuple[float, float, float, float]:
    parts = [p.strip() for p in bbox_str.split(",")]
    if len(parts) != 4:
        raise ValueError("invalid bbox")
    min_lng, min_lat, max_lng, max_lat = map(float, parts)
    return min_lng, min_lat, max_lng, max_lat

def or_icontains(fields: List[str], terms: List[str]) -> Q:
    terms = [t for t in terms if t]
    if not fields or not terms:
        return Q()
    qs = [Q(**{f"{f}__icontains": t}) for f in fields for t in terms]
    return reduce(or_, qs)

def text_or_unknown(v: Optional[str]) -> str:
    return v.strip() if (v and str(v).strip()) else "정보없음"

def parking_text(v: Optional[bool]) -> str:
    if v is True:
        return "주차 가능"
    if v is False:
        return "주차 불가"
    return "정보없음"

def extract_conditions(policy) -> List[str]:
    conds: List[str] = []
    txt = f"{getattr(policy, 'etc_info', '')} {getattr(policy, 'acmpy_type_cd', '')}"
    if "목줄" in txt:
        conds.append("목줄착용")
    return conds

def conditions_text(policy) -> str:
    conds = extract_conditions(policy)
    return " · ".join(conds) if conds else "정보없음"

def split_lines(text: str) -> List[str]:
    if not text:
        return []
    raw = text.replace("\r\n", "\n").replace("\r", "\n")
    out: List[str] = []
    for chunk in raw.split("\n"):
        for piece in chunk.split(","):
            t = piece.strip("• ").strip()
            if t:
                out.append(t)
    return out

def prune_empty(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            pv = prune_empty(v)
            if pv in (None, "", []) or (isinstance(pv, dict) and not pv):
                continue
            out[k] = pv
        return out
    if isinstance(obj, list):
        out = [prune_empty(v) for v in obj]
        return [v for v in out if v not in (None, "", []) and not (isinstance(v, dict) and not v)]
    return obj

def haversine_km(lat1: float, lng1: float, lat2: Optional[float], lng2: Optional[float]) -> Optional[float]:
    if None in (lat1, lng1, lat2, lng2):
        return None
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
    c = 2 * asin(sqrt(a))
    return round(R * c, 1)

def address_brief(addr: Optional[str]) -> str:
    if not addr:
        return "정보없음"
    parts = addr.split()

    if len(parts) >= 3 and parts[1].endswith("시"):
        return f"{parts[1]} {parts[2]}"
    return " ".join(parts[:2]) if len(parts) >= 2 else parts[0]

def thumb_or_text(place) -> str:
    im = place.images.first()
    url = (im.thumb or im.origin) if im else None
    return url or NO_IMAGE_TEXT

def collect_text(place) -> str:
    policy = getattr(place, "pet_policy", None)
    return " ".join([
        place.overview or "",
        getattr(policy, "etc_info", "") or "",
        getattr(policy, "acmpy_type_cd", "") or "",
        (place.title or ""),
    ])

def find_labels(text: str, mapping: Dict[str, List[str]]) -> List[str]:
    if not text:
        return []
    tl = text.lower()
    out: List[str] = []
    for label, kws in mapping.items():
        if any(kw.lower() in tl for kw in kws):
            out.append(label)
    return list(dict.fromkeys(out))

def place_type_label(place) -> Optional[str]:

    if place.content_type_id != 32:
        return None
    txt = (place.title or "") + " " + (place.overview or "")
    for w in ["호텔", "리조트", "콘도", "펜션", "게스트하우스", "풀빌라", "모텔", "호스텔"]:
        if w in txt:
            return w
    return "숙소"

def tokens_to_terms(tokens: List[str], token_map: Dict[str, str], dict_map: Dict[str, List[str]]) -> List[str]:
    out: List[str] = []
    for t in tokens or []:
        label = token_map.get(t)
        if label:
            out += dict_map.get(label, [])
    return out

def build_filter_q(query) -> Q:

    q = Q()

    sizes = set(query.get("sizes") or [])
    if sizes and "all" not in sizes:

        size_code_map = {"small": "01", "med": "02", "large": "03", "xlarge": "04"}
        codes = [size_code_map[s] for s in sizes if s in size_code_map]
        if codes:
            sq = Q()
            for c in codes:
                sq |= Q(pet_policy__acmpy_type_cd__icontains=c)
            q &= sq
        terms = tokens_to_terms(list(sizes), SIZE_TOKEN_TO_LABEL, SIZE_KEYWORDS)
        if terms:
            q &= or_icontains(["pet_policy__etc_info", "overview"], terms)

    # areas
    areas = set(query.get("areas") or [])
    area_terms = tokens_to_terms(list(areas), AREA_TOKEN_TO_LABEL, AREA_KEYWORDS)
    if area_terms:
        q &= or_icontains(["pet_policy__etc_info", "overview"], area_terms)

    # conditions
    conds = set(query.get("conditions") or [])
    cond_terms = tokens_to_terms(list(conds), COND_TOKEN_TO_LABEL, COND_KEYWORDS)
    if cond_terms:
        q &= or_icontains(["pet_policy__etc_info", "overview"], cond_terms)

    # amenities
    amens = set(query.get("amenities") or [])
    if "parking" in amens:
        q &= Q(has_parking=True)
    amen_terms = tokens_to_terms(list(amens), AMENITY_TOKEN_TO_LABEL, AMENITY_KEYWORDS)
    if amen_terms:
        q &= or_icontains(["overview", "pet_policy__etc_info"], amen_terms)

    return q

def split_terms(qstr: str) -> List[str]:

    if not qstr:
        return []
    tokens = re.split(r"[\s,]+", str(qstr).strip())
    return [t for t in tokens if len(t) >= 2]

def and_icontains(fields: List[str], terms: List[str]) -> Q:
    if not fields or not terms:
        return Q()

    q_total = None
    for t in terms:
        subq = Q()
        for f in fields:
            subq |= Q(**{f"{f}__icontains": t})
        q_total = subq if q_total is None else (q_total & subq)

    return q_total or Q()
