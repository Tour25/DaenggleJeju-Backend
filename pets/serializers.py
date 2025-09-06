from django.utils.text import slugify
from rest_framework import serializers
from .models import PetBreed, PetProfile


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

    class Meta:
        model = PetProfile
        fields = ("id", "name", "sizeCode", "breed")
