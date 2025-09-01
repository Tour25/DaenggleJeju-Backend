from django.urls import path
from .views import KakaoLoginStartView

urlpatterns = [
    path("kakao/login", KakaoLoginStartView.as_view()),
]
