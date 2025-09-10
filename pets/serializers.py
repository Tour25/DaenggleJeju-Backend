from django.utils.text import slugify
from rest_framework import serializers
from .models import PetBreed, PetProfile
from datetime import date


class PetBreedReadSerializer(serializers.ModelSerializer):
    nameKo = serializers.CharField(source="name_ko")
    class Meta:
        model = PetBreed
        fields = ("id", "code", "nameKo")

class PetBreedInitItemSerializer(serializers.Serializer):
    code = serializers.SlugField(max_length=64, required=False, allow_blank=True)
    nameKo = serializers.CharField(max_length=100)

    def validate(self, attrs):

        if not attrs.get("code"):
            attrs["code"] = slugify(attrs["nameKo"], allow_unicode=True)
        return attrs

class PetBreedInitRequestSerializer(serializers.Serializer):
    items = PetBreedInitItemSerializer(many=True)

class PetBreedInitResultSerializer(serializers.Serializer):
    created = serializers.IntegerField()
    updated = serializers.IntegerField()
    total = serializers.IntegerField()

class PetProfileWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50)

    sizeCode = serializers.ChoiceField(choices=PetProfile.Size.choices)
    breedId = serializers.IntegerField(required=False, allow_null=True)
    birthDate = serializers.DateField(required=False, allow_null=True,
                                      help_text="생년월일(YYYY-MM-DD)")

    def validate_breedId(self, value):
        if value is None:
            return value
        if not PetBreed.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("유효하지 않은 breedId 입니다.")
        return value

class _PetBreedNestedSerializer(serializers.ModelSerializer):
    nameKo = serializers.CharField(source="name_ko")

    class Meta:
        model = PetBreed
        fields = ("id", "code", "nameKo")

class PetProfileReadSerializer(serializers.ModelSerializer):
    sizeCode = serializers.CharField(source="size_code")
    breed = _PetBreedNestedSerializer(read_only=True)
    birthDate = serializers.DateField(required=False, allow_null=True,
                                      help_text="생년월일(YYYY-MM-DD)")
    ageYears = serializers.SerializerMethodField()

    class Meta:
        model = PetProfile
        fields = ("id", "name", "sizeCode", "breed")

    def get_ageYears(self, obj):
        return obj.age_years


class PetProfilePatchSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50, required=False)
    sizeCode = serializers.ChoiceField(choices=PetProfile.Size.choices, required=False)
    breedId = serializers.IntegerField(required=False, allow_null=True)
    birthDate = serializers.DateField(required=False, allow_null=True,
                                      help_text="생년월일(YYYY-MM-DD)")

    def validate_breedId(self, value):
        if value is None:
            return value
        if not PetBreed.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("유효하지 않은 breedId 입니다.")
        return value

    def validate_birthDate(self, value):
        if value and value > date.today():
            raise serializers.ValidationError("생일은 미래일 수 없습니다.")
        return value


class _PetBreedNestedSerializer(serializers.ModelSerializer):
    nameKo = serializers.CharField(source="name_ko")

    class Meta:
        model = PetBreed
        fields = ("id", "code", "nameKo")

class PetProfileReadSerializer(serializers.ModelSerializer):
    breedNameKo = serializers.CharField(source="breed.name_ko", allow_null=True)
    sizeLabelKo = serializers.SerializerMethodField(help_text="사이즈 한글 라벨(예: '대형견(16~30kg)')")
    ageYears    = serializers.SerializerMethodField(help_text="만 나이(년) — 생일 없으면 null")

    class Meta:
        model = PetProfile
        fields = ("id", "name", "breedNameKo", "sizeLabelKo", "ageYears")

    def get_sizeLabelKo(self, obj):

        try:
            return obj.get_size_code_display()
        except Exception:
            return None

    def get_ageYears(self, obj):
        b = getattr(obj, "birth_date", None)
        if not b:
            return None
        today = date.today()
        return max(0, today.year - b.year - ((today.month, today.day) < (b.month, b.day)))