from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.views import LogoutView
from django.utils.decorators import method_decorator


@method_decorator(login_not_required, name="dispatch")
class PublicLogoutView(LogoutView):
    next_page = "/"
