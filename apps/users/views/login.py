from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.users.serializers import (
    LoginRequestSerializer,
    LoginResponseSerializer,
    LogoutRequestSerializer,
    LogoutResponseSerializer,
    UserInfoSerializer,
)


class LoginView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_summary='Login',
        operation_description=(
            'Username va password orqali foydalanuvchini tekshiradi, '
            'JWT access va refresh token qaytaradi.'
        ),
        request_body=LoginRequestSerializer,
        responses={
            200: LoginResponseSerializer,
            400: openapi.Response(description='Validation error'),
        },
        tags=['Users Auth'],
    )
    def post(self, request):
        serializer = LoginRequestSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        data = {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'token_type': 'Bearer',
            'user': UserInfoSerializer(user).data,
        }
        return Response(data, status=status.HTTP_200_OK)


class GetMeView(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_summary='Joriy foydalanuvchi profili',
        operation_description='Bearer access token egasining profil va rol ma’lumotlarini qaytaradi.',
        responses={
            200: UserInfoSerializer,
            401: openapi.Response(description='Access token berilmagan yoki yaroqsiz'),
        },
        tags=['Users Auth'],
    )
    def get(self, request):
        return Response(UserInfoSerializer(request.user).data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_summary='Logout',
        operation_description=(
            'Refresh tokenni blacklistga qo‘shadi. Shundan keyin bu token orqali yangi access token olib bo‘lmaydi.'
        ),
        request_body=LogoutRequestSerializer,
        responses={
            200: LogoutResponseSerializer,
            400: openapi.Response(description='Refresh token yaroqsiz yoki allaqachon bekor qilingan'),
            401: openapi.Response(description='Access token berilmagan yoki yaroqsiz'),
        },
        tags=['Users Auth'],
    )
    def post(self, request):
        serializer = LogoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data['token'].blacklist()
        return Response(
            {'detail': 'Tizimdan muvaffaqiyatli chiqildi.'},
            status=status.HTTP_200_OK,
        )
