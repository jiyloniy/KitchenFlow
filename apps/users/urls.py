from django.urls import path
from apps.users.views import LoginView

app_name = 'users'

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='login'),
]
