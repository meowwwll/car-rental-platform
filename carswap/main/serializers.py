from rest_framework import serializers
from .models import Car

class CarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = [
            'id',
            'owner',   # !!! важно, чтобы был, если хочешь видеть владельца
            'brand',
            'model',
            'year',
            'city',
            'price_per_day',
            'price_per_hour',
            'description',
            'fuel_type',
            'transmission',
            'seats',
        ]
        read_only_fields = ('owner',)  # Чтобы при создании машины автоматически задавался владелец

    # Переопределяем создание машины
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['owner'] = user.userprofile
        return super().create(validated_data)
