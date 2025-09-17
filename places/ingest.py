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

            chips = (payload or {}).get("chips") or []
            if chips:
                policy, _ = PetPolicy.objects.get_or_create(place=place)
                info = {}
                if policy.etc_info:
                    try:
                        parsed = json.loads(policy.etc_info)
                        info = parsed if isinstance(parsed, dict) else {"_raw": str(policy.etc_info)}
                    except Exception:
                        info = {"_raw": str(policy.etc_info)}
                before = [c for c in (info.get("chips") or []) if isinstance(c, str)]
                merged = sorted(set(before + [c for c in chips if isinstance(c, str)]))
                info["chips"] = merged
                if not dry_run:
                    policy.etc_info = json.dumps(info, ensure_ascii=False)
                    policy.save(update_fields=["etc_info"])
                stats["updated_policies"] += 1
                stats["logs"].append(f"[OK] chips 병합: {content_id} -> {merged}")

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
                    stats["logs"].append(f"[DRY] 이미지 교체: {content_id} 삭제 {to_remove} → 추가 {len(new_urls)}")
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
                    stats["logs"].append(f"[OK] 이미지 교체: {content_id} 삭제 {removed} → 추가 {len(objs)}")

    _run()
    return stats
