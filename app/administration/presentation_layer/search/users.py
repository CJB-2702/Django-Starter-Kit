from django.contrib.auth import get_user_model

User = get_user_model()


def list_users_ordered():
    return User.objects.order_by("username").only("id", "username", "email", "is_active", "is_staff")
