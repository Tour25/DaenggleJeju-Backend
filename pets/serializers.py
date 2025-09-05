from rest_framework import serializers
from .models import PetBreed

class PetBreedReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetBreed
        fields = ("id", "code", "name_ko", "is_active")

class PetBreedInitItemSerializer(serializers.Serializer):
    code = serializers.SlugField(max_length=64, required=False, allow_blank=True)
    nameKo = serializers.CharField(max_length=100)

class PetBreedInitRequestSerializer(serializers.Serializer):
    items = PetBreedInitItemSerializer(many=True)

class PetBreedInitResultSerializer(serializers.Serializer):
    created = serializers.IntegerField()
    updated = serializers.IntegerField()
    total = serializers.IntegerField()
