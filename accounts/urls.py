from django.urls import path
from .views import KakaoLoginStartView,KakaoCallbackView,MeView

urlpatterns = [
    path("kakao/login", KakaoLoginStartView.as_view()),
    path("kakao/callback", KakaoCallbackView.as_view()),
    path("me", MeView.as_view()),
]
