from django.urls import path
from apps.users.views import GetMeView, LoginView, LogoutView

app_name = 'users'

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/getme/', GetMeView.as_view(), name='getme'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
]
