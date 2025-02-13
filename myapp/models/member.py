from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import now


class Member(models.Model):
    firstname = models.CharField(max_length=255, null=False, blank=False)
    lastname = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(max_length=255, null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    address_number = models.CharField(max_length=20, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=255, null=True, blank=True)
    zip = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "member"

    def __str__(self):
        return (
            f"{self.firstname} {self.lastname.upper() if self.lastname else ''}".strip()
        )

    def get_fullname(self):
        first = self.firstname or ""
        last = self.lastname or ""
        return f"{first} {last}".strip()

    def get_shortname(self):
        first = self.firstname or ""
        last = (self.lastname or "")[0:1].upper()
        if last != "":
            last = "." + last
        return f"{first} {last}".strip()

    def get_country(self):
        return "CH"

    def get_full_address_line1(self):
        if not self.address and not self.address_number:
            return None
        return f"{self.address or ''} {self.address_number or ''}".strip()

    def get_full_address_line2(self):
        if not self.city and not self.zip:
            return None
        return f"{self.zip or ''} {self.city or ''}".strip()

    def set_city_and_zip(self, npa_and_city):
        if not npa_and_city:
            return
        parts = npa_and_city.split()
        for i, part in enumerate(parts):
            if part.isdigit():
                self.zip = int(part)
                self.city = " ".join(parts[:i] + parts[i + 1 :]).strip()
                return
