from django.contrib.auth.decorators import login_not_required
from django.utils.decorators import method_decorator
from mozilla_django_oidc.views import OIDCAuthenticationCallbackView, OIDCAuthenticationRequestView


@method_decorator(login_not_required, name="dispatch")
class PublicOIDCAuthRequestView(OIDCAuthenticationRequestView):
    pass


@method_decorator(login_not_required, name="dispatch")
class PublicOIDCAuthCallbackView(OIDCAuthenticationCallbackView):
    pass
