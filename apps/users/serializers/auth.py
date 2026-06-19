from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User


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


class UserInfoSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'name', 'role', 'role_display', 'is_active')
        read_only_fields = fields


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    token_type = serializers.CharField()
    user = UserInfoSerializer()


class LogoutRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        write_only=True,
        help_text='Login endpointdan olingan refresh token.',
    )

    def validate(self, attrs):
        try:
            attrs['token'] = RefreshToken(attrs['refresh'])
        except TokenError as exc:
            raise serializers.ValidationError({'refresh': 'Refresh token yaroqsiz yoki eskirgan.'}) from exc
        return attrs


class LogoutResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
