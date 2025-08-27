from django.db import models
from .base import TimeStampedModel
from .area_code import AreaCode

class Place(TimeStampedModel):
    content_id=models.CharField(max_length=32, unique=True, db_index=True) #관광공사 원본 콘텐츠 ID
    content_type_id=models.CharField(max_length=4, blank=True, default="", db_index=True) #관광공사 원본 콘텐츠 타입

    #지역
    area=models.ForeignKey(
        AreaCode,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="places",
        db_index=True
    )

    #기본 정보
    title=models.CharField(max_length=225, db_index=True) #장소명
    addr_primary=models.CharField(max_length=225, blank=True, default="") #기본 주소
    addr_detail=models.CharField(max_length=225, blank=True, default="") #상세 주소
    postal_code=models.CharField(max_length=20, blank=True, default="") #우편번호
    tel=models.CharField(max_length=100, blank=True, default="") #전화번호
    homepage=models.TextField(blank=True, default="") #홈페이지 URL

    #좌표/이미지
    mapx=models.DecimalField(max_digits=13, decimal_places=6,null=True, blank=True) #경도
    mapy=models.DecimalField(max_digits=13, decimal_places=6, null=True, blank=True) #위도
    thumbnail_image=models.URLField(blank=True, default="") #대표 이미지
    thumbnail_small_image=models.URLField(blank=True, default="") #대표 이미지 (작은 사이즈)

    #카테고리
    category_lv1=models.CharField(max_length=10, blank=True, default="", db_index=True) #카테고리 대분류 코드
    category_lv2=models.CharField(max_length=10, blank=True, default="", db_index=True) #카테고리 중분류 코드
    category_lv3=models.CharField(max_length=10, blank=True, default="", db_index=True) #카테고리 소분류 코드

    #소개/운영
    overview=models.TextField(blank=True, default="") #장소 설명
    openingtime=models.CharField(max_length=225, blank=True, default="") #운영시간
    closed_days=models.CharField(max_length=225, blank=True, default="") #휴무일
    parking=models.CharField(max_length=225, blank=True, default="") #주차 안내
    creditcard=models.CharField(max_length=50, blank=True, default="") #카드 사용가능 여부

    source=models.CharField(max_length=50, default="KTO", db_index=True) #데이터 출처
    is_active=models.BooleanField(default=True) #사용 여부

    class Meta:
        indexes=[
            models.Index(fields=["title"]),
            models.Index(fields=["category_lv1", "category_lv2", "category_lv3"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.content_id})"