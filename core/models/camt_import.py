from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .subscription import Subscription


class CamtImport(models.Model):
    file = models.FileField(upload_to="uploads/camt/")
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="camt_imports"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "camt_import"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.file.name} ({self.subscription.name})"


@receiver(pre_delete, sender=CamtImport)
def _delete_camt_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)
