from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from apps.users.models import User


def ceo_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('panel-login')

        if request.user.role != User.Role.CEO:
            messages.error(request, 'Bu bo‘limga faqat CEO kira oladi.')
            return redirect('panel-login')

        return view_func(request, *args, **kwargs)

    return wrapper
