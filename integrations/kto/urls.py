from django.urls import path
from .views import (
    AreaCodeView, CategoryCodeView,
    AreaBasedListView, LocationBasedListView, SearchKeywordView,
    DetailPreviewView, DailySyncView, BootstrapAreaView, EnrichIdsView,
)

urlpatterns = [
    # 코드 동기화
    path('area-codes', AreaCodeView.as_view()),
    path('category-codes', CategoryCodeView.as_view()),

    # 목록 조회
    path('area-based-list', AreaBasedListView.as_view()),
    path('location-based-list', LocationBasedListView.as_view()),
    path('search-keyword', SearchKeywordView.as_view()),

    # 상세 미리보기
    path('detail-preview', DetailPreviewView.as_view()),

    # 증분 동기화 + 부트스트랩
    path('sync/daily', DailySyncView.as_view()),
    path('bootstrap/area', BootstrapAreaView.as_view()),

    # contentId 묶음 상세 저장
    path('enrich/ids', EnrichIdsView.as_view()),
]
