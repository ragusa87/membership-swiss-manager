from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from ..settings import FILE_UPLOAD_MAX_MEMORY_SIZE
from .subscription import Subscription


class CamtImport(models.Model):
    file = models.FileField(
        upload_to="uploads/camt/",
        validators=[FileExtensionValidator(allowed_extensions=["xml"])],
    )
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="camt_imports"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "camt_import"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.file.name} ({self.subscription.name})"

    def clean(self):
        super().clean()
        if self.file and self.file.size > FILE_UPLOAD_MAX_MEMORY_SIZE:
            raise ValidationError({"file": _("File too large")})


@receiver(pre_delete, sender=CamtImport)
def _delete_camt_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)
