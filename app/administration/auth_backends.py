from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from app.administration.models import AllowedEmailDomain


class MicrosoftOIDCBackend(OIDCAuthenticationBackend):
    def verify_claims(self, claims):
        if not super().verify_claims(claims):
            return False

        email = claims.get("email") or claims.get("preferred_username", "")
        if not email:
            return False

        domain = email.split("@")[-1].lower()
        return AllowedEmailDomain.objects.filter(
            domain=domain, is_active=True
        ).exists()

    def create_user(self, claims):
        user = super().create_user(claims)
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.save()
        return user

    def update_user(self, user, claims):
        user.first_name = claims.get("given_name", user.first_name)
        user.last_name = claims.get("family_name", user.last_name)
        user.save()
        return user
