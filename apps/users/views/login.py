from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.users.serializers import LoginRequestSerializer, LoginResponseSerializer


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
            'user': {
                'id': user.id,
                'username': user.username,
                'name': user.name,
                'role': user.role,
            },
        }
        return Response(data, status=status.HTTP_200_OK)
