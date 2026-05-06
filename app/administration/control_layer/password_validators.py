"""OWASP-compliant password validators.

Following OWASP Authentication Cheat Sheet recommendations:
- Minimum length (12 characters minimum)
- Check against common/breached passwords
- Check against user attributes (username, email, etc.)
- No arbitrary complexity requirements (no forced uppercase/number/symbol mixtures)
- Allow spaces and all special characters
"""

from django.contrib.auth.password_validation import (
    MinimumLengthValidator,
    get_password_validators,
)
from django.core.exceptions import ValidationError


class OWASPMinimumLengthValidator(MinimumLengthValidator):
    """OWASP-compliant minimum length validator: 12 characters minimum.

    OWASP recommends 8+ characters, but 12 is a reasonable stronger baseline
    for organizational use. Can be configured via PASSWORD_MIN_LENGTH_OWASP env var.
    """

    def __init__(self, min_length: int = 12) -> None:
        self.min_length = min_length

    def get_help_text(self) -> str:
        return f"Your password must contain at least {self.min_length} characters."

    def validate(self, password: str, user=None) -> None:
        if len(password) < self.min_length:
            raise ValidationError(
                f"This password is too short. It must contain at least {self.min_length} characters.",
                code="password_too_short",
                params={"min_length": self.min_length},
            )
