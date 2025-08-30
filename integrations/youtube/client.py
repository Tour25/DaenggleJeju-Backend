# integrations/youtube/client.py
import time
from typing import Dict, List, Optional

import requests
from django.conf import settings

BASE_URL = "https://www.googleapis.com/youtube/v3"

class YouTubeClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.YOUTUBE_API_KEY
        if not self.api_key:
            raise RuntimeError("YOUTUBE_API_KEY is not set")

    def _get(self, path: str, params: Dict, tries: int = 5) -> Dict:
        backoff = 1.0
        for i in range(tries):
            r = requests.get(f"{BASE_URL}/{path}", params=params, timeout=10)
            # 429/5xx는 지수 백오프
            if r.status_code in (429, 500, 502, 503, 504):
                if i == tries - 1:
                    r.raise_for_status()
                time.sleep(backoff)
                backoff *= 2
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError("unreachable")

    def search_video_ids(
        self,
        q: str,
        *,
        published_after_iso: Optional[str] = None,
        page_token: Optional[str] = None,
        max_results: int = 50,
        order: str = "date",
        region_code: Optional[str] = None,
        relevance_lang: Optional[str] = None,
    ) -> Dict:
        params = {
            "key": self.api_key,
            "part": "id",
            "type": "video",
            "q": q,
            "maxResults": max_results,
            "order": order,
        }
        if published_after_iso:
            params["publishedAfter"] = published_after_iso
        if page_token:
            params["pageToken"] = page_token
        if region_code:
            params["regionCode"] = region_code
        if relevance_lang:
            params["relevanceLanguage"] = relevance_lang

        data = self._get("search", params)
        ids = [
            it.get("id", {}).get("videoId")
            for it in data.get("items", [])
            if it.get("id", {}).get("kind") == "youtube#video"
        ]
        return {
            "video_ids": [i for i in ids if i],
            "next_page_token": data.get("nextPageToken"),
        }

    def get_videos_details(self, video_ids: List[str]) -> List[Dict]:
        if not video_ids:
            return []
        params = {
            "key": self.api_key,
            "part": "snippet,contentDetails,statistics",
            "id": ",".join(video_ids[:50]),  # 최대 50개
            "maxResults": 50,
        }
        data = self._get("videos", params)
        return data.get("items", [])
