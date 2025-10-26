from django.db import transaction
import json

from .models import Place, PlaceImage, PetPolicy
from .extra_data import HARDCODED


def ingest_hardcoded(*, dry_run: bool = False, allow_data_urls: bool = True) -> dict:

    data = HARDCODED or {}
    stats = {
        "processed": 0,
        "updated_policies": 0,
        "replaced_images": 0,
        "removed_images": 0,
        "skipped_missing_place": 0,
        "dry_run": bool(dry_run),
        "logs": [],
    }

    def _to_list(x):
        if not x:
            return []
        if isinstance(x, str):

            try:
                v = json.loads(x)
                if isinstance(v, list):
                    return [str(s).strip() for s in v if str(s).strip()]
            except Exception:
                pass
            import re
            return [s.strip() for s in re.split(r"[,\\n]+", x) if s.strip()]
        if isinstance(x, (list, tuple)):
            return [str(s).strip() for s in x if str(s).strip()]
        return []

    def _merge_unique(a, b):

        return sorted(
            {s for s in (a or []) if isinstance(s, str)} |
            {s for s in (b or []) if isinstance(s, str)}
        )

    @transaction.atomic
    def _run():
        for content_id, payload in data.items():
            stats["processed"] += 1

            place = (
                Place.objects.filter(content_id=content_id).first()
                or Place.objects.filter(content_id=str(content_id)).first()
            )
            if not place:
                stats["skipped_missing_place"] += 1
                stats["logs"].append(f"[SKIP] Place 없음: content_id={content_id}")
                continue


            chips1_in = _to_list((payload or {}).get("chips1"))
            chips2_in = _to_list((payload or {}).get("chips2"))
            legacy = _to_list((payload or {}).get("chips"))


            if legacy and not chips1_in:
                chips1_in = legacy

            if chips1_in or chips2_in:
                policy, _ = PetPolicy.objects.get_or_create(place=place)


                info = {}
                if policy.etc_info:
                    try:
                        parsed = json.loads(policy.etc_info)
                        info = parsed if isinstance(parsed, dict) else {"_raw": str(policy.etc_info)}
                    except Exception:
                        info = {"_raw": str(policy.etc_info)}

                before1 = _to_list(info.get("chips1"))
                before2 = _to_list(info.get("chips2"))

                merged1 = _merge_unique(before1, chips1_in)
                merged2 = _merge_unique(before2, chips2_in)

                if isinstance(info.get("chips"), list):
                    migrated = _merge_unique(merged1, _to_list(info.get("chips")))
                    merged1 = migrated
                    info.pop("chips", None)

                info["chips1"] = merged1
                info["chips2"] = merged2

                if not dry_run:
                    policy.etc_info = json.dumps(info, ensure_ascii=False)
                    policy.save(update_fields=["etc_info"])

                stats["updated_policies"] += 1
                stats["logs"].append(
                    f"[OK] chips1/2 병합: {content_id} -> chips1={merged1} | chips2={merged2}"
                )


            if "images" in (payload or {}):
                raw_list = (payload or {}).get("images") or []
                seen, new_urls = set(), []
                for u in raw_list:
                    if not isinstance(u, str):
                        continue
                    u = u.strip()
                    if not u:
                        continue
                    if (not allow_data_urls) and u.startswith("data:"):
                        continue
                    if u in seen:
                        continue
                    seen.add(u)
                    new_urls.append(u)

                qs = PlaceImage.objects.filter(place=place)
                to_remove = qs.count()
                if dry_run:
                    stats["removed_images"] += to_remove
                    stats["replaced_images"] += len(new_urls)
                    stats["logs"].append(
                        f"[DRY] 이미지 교체: {content_id} 삭제 {to_remove} → 추가 {len(new_urls)}"
                    )
                else:
                    removed = qs.delete()[0]
                    stats["removed_images"] += removed
                    objs = [PlaceImage(place=place, origin=u, thumb=u) for u in new_urls]
                    if objs:
                        PlaceImage.objects.bulk_create(objs)
                    stats["replaced_images"] += len(objs)
                    new_has = bool(objs)
                    if place.has_image != new_has:
                        place.has_image = new_has
                        place.save(update_fields=["has_image"])
                    stats["logs"].append(
                        f"[OK] 이미지 교체: {content_id} 삭제 {removed} → 추가 {len(objs)}"
                    )

    _run()
    return stats
