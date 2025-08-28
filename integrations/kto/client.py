import os
import httpx
from typing import Any, Dict, Optional

PATHS = {
    "areaCode": "areaCode",
    "categoryCode": "categoryCode",
    "areaBasedList": "areaBasedList",
    "locationBasedList": "locationBasedList",
    "searchKeyword": "searchKeyword",
    "detailCommon": "detailCommon",
    "detailIntro": "detailIntro",
    "detailInfo": "detailInfo",
    "detailImage": "detailImage",
    "detailPetTour": "detailPetTour",
    "petTourSyncList": "petTourSyncList",
}

class KTOClient:
    def __init__(
        self,
        timeout: int = 20,
        base_url: Optional[str] = None,
        service_key: Optional[str] = None,
    ):
        """
        base_url: 서비스 베이스 URL. 기본은 반려동물 전용 'KorPetTourService'
                  예) https://apis.data.go.kr/B551011/KorPetTourService
            폴백용 공용 서비스는 'KorService' 권장
                  예) https://apis.data.go.kr/B551011/KorService
        """
        self.base_url = base_url or os.getenv(
            "KTO_BASE_URL",
            "https://apis.data.go.kr/B551011/KorPetTourService",
        )
        self.client = httpx.Client(timeout=timeout)
        self.service_key = (
            service_key
            or os.getenv("KTO_TOURAPI_KEY")
            or os.getenv("KTO_PET_API_KEY")
        )
        self.mobile_app = os.getenv("KTO_MOBILE_APP", "DaenggleJeju")
        self.mobile_os = os.getenv("KTO_MOBILE_OS", "ETC")
        if not self.service_key:
            raise RuntimeError(
                "KTO service key not found. Set KTO_TOURAPI_KEY or KTO_PET_API_KEY in env."
            )

    def get(self, op: str, **params) -> Dict[str, Any]:
        if op not in PATHS:
            raise ValueError(f"Unknown operation: {op}")
        url = f"{self.base_url}/{PATHS[op]}"
        q = {
            "serviceKey": self.service_key,
            "MobileOS": self.mobile_os,
            "MobileApp": self.mobile_app,
            "_type": "json",
            **params,
        }
        r = self.client.get(url, params=q)
        r.raise_for_status()
        data = r.json()


        code = None
        if isinstance(data, dict):
            resp = data.get("response")
            if isinstance(resp, dict):
                header = resp.get("header") or {}
                code = header.get("resultCode")
                if code == "0000":
                    return resp.get("body", {})
            # fallback: top-level
            code = code or data.get("resultCode")

        raise RuntimeError(f"KTO error: {code} {data}")

def items_as_list(body: Dict[str, Any]):
    """KTO body에서 items.item을 리스트로 정규화"""
    items = (body.get("items", {}) or {}).get("item", [])
    if items is None:
        return []
    return items if isinstance(items, list) else [items]
