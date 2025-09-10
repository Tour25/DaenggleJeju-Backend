REGION_NAME_BY_ID = {
    "PLACE_jeju_si": "제주시",
    "PLACE_aeweol": "애월/한림/한경",
    "PLACE_jocheon": "조천/구좌/우도",
    "PLACE_seogwipo_si": "서귀포시",
    "PLACE_andeok": "안덕/대정",
    "PLACE_seongsan": "성산/표선/남원",
}

CURATION_TILES = [
    {
        "key": "west_coast_beach",
        "title": "강아지가 좋아하는 제주 서쪽 여행 코스",
        "hashtag": "#동반입수바다",
        "filters": {
            "place_context_ids": ["PLACE_aeweol"],
            "style_any": ["OUTDOOR", "RELAX"],
            "keywords_any": ["협재 강아지 바다 여행", "곽지 강아지 여행", "금능 강아지 여행", "강아지 해변", "강아지 바다", "강아지 입수"],
        },
    },
    {
        "key": "water_activity",
        "title": "강아지와 함께 떠나는 카약&워터 액티비티",
        "hashtag": "#반려견액티비티",
        "filters": {
            "style_any": ["ACTIVITY"],
            "keywords_any": ["제주 강아지 카약", "제주 강아지 카누", "제주 강아지 패들보드", "제주 강아지와 액티비티 여행"],
        },
    },
    {
        "key": "dog_park",
        "title": "맘껏 뛰어놀자! 대형견, 소형견 전용 놀이터",
        "hashtag": "#반려견운동장",
        "filters": {
                "style_any": ["OUTDOOR"],
                "keywords_any": ["제주 강아지 운동장", "제주 도그파크", "제주 강아지 놀이터"],
        },
    },
    {
        "key": "aeweol_coastal_road",
        "title": "창밖으로 스치는 해변, 애월 해안 로드 드림",
        "hashtag": "#애월해안도로",
        "filters": {
            "place_context_ids": ["PLACE_aeweol"],
            "keywords_any": ["애월 강아지 여행", "해안도로 강아지 여행", "애월 가아지 드라이브"],
        },
    },
    {
        "key": "oreum_hike",
        "title": "제주 오름 산책, 너와 함께라서 더 특별해",
        "hashtag": "#제주중산간코스",
        "filters": {
            "style_any": ["OUTDOOR", "RELAX"],
            "keywords_any": ["강아지 제주 오름", "강아지 제주 트레킹", "제주 강아지 등산", "제주 강아지 산책"],
        },
    },
    {
        "key": "hyeopjae_sunset",
        "title": "협재의 노을 아래, 강아지와 함께 걷는 바다",
        "hashtag": "#반려견해변산책",
        "filters": {
            "place_context_ids": ["PLACE_aeweol"],
            "style_any": ["RELAX", "OUTDOOR"],
            "keywords_any": ["협재 강아지 여행", "협재 일몰 강아지 여행", "제주 협재 노을 반려견 여행", "제주 협재 해변 강아지", "제주 협재 강아지 해변 산책"],
        },
    },
]

__all__ = ["CURATION_TILES", "REGION_NAME_BY_ID"]
