from django.db import models


class SoftDeleteMixin(models.Model):
    """Adds soft-delete to a model. deleted_at=None means active."""

    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
