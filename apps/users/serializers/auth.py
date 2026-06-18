from django.contrib.auth import authenticate
from rest_framework import serializers


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        request = self.context.get('request')
        user = authenticate(
            request=request,
            username=attrs.get('username'),
            password=attrs.get('password'),
        )

        if user is None:
            raise serializers.ValidationError({
                'detail': 'Username yoki password xato.'
            })

        if not user.is_active:
            raise serializers.ValidationError({
                'detail': 'Bu foydalanuvchi faol emas.'
            })

        attrs['user'] = user
        return attrs


class UserInfoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    name = serializers.CharField()
    role = serializers.CharField()


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    token_type = serializers.CharField()
    user = UserInfoSerializer()
