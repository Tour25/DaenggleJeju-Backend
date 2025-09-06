from django.urls import path
from .views import KakaoLoginStartView,KakaoCallbackView,MeView, DevLoginView, DevLogoutView

urlpatterns = [
    path("kakao/login", KakaoLoginStartView.as_view()),
    path("kakao/callback", KakaoCallbackView.as_view()),
    path("me", MeView.as_view()),
    path("dev-login", DevLoginView.as_view()),
    path("dev-logout", DevLogoutView.as_view()),
]
