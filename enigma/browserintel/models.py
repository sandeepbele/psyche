from django.db import models

from django.db import models
from django.utils import timezone
from browserintel.fp import Fingerprint

import json
class FingerprintData(models.Model):
    fingerprint = models.JSONField()
    user_identifier = models.CharField(max_length=255)
    stable_fp = models.CharField(max_length=255)
    loose_fp = models.CharField(max_length=255)
    access_time = models.DateTimeField(default=timezone.now)
    ip_address = models.CharField(max_length=255)
    device = models.CharField(max_length=255, null=True)
    browser = models.CharField(max_length=255, null=True)
    browser_private_mode = models.BooleanField(null=True)
    headless_rating = models.IntegerField(null=True)
    stealth_rating = models.IntegerField(null=True)
    timezone = models.CharField(max_length=255, null=True)
    lies = models.IntegerField(null=True)
    resistance = models.JSONField(null=True)
    is_bot = models.BooleanField(null=True)
    bot_type = models.CharField(max_length=255, null=True)

    def parse_fingerprint_data(self):
        fp_data = Fingerprint(self.fingerprint)
        self.stable_fp = fp_data.stable_digest()
        self.loose_fp = fp_data.digest()
        self.device = fp_data.device()
        self.browser = fp_data.browser()
        self.browser_private_mode = fp_data.browserPrivateMode()
        self.headless_rating = fp_data.headlessRating()
        self.stealth_rating = fp_data.stealthRating()
        self.timezone = fp_data.timezone()
        self.lies = fp_data.lies()
        self.resistance = fp_data.resistance()
        self.is_bot = fp_data.is_bot()
        self.bot_type = fp_data.bot_type()

    def save(self, *args, **kwargs):
        if not self.pk:
            self.parse_fingerprint_data()
        super().save(*args, **kwargs)

    def to_dict(self):
        # Convert the model to a dictionary, excluding the fingerprint field
        fields = self._meta.fields
        field_names = [field.name for field in fields if field.name != 'fingerprint']
        return {field_name: getattr(self, field_name) for field_name in field_names}

    
    def to_json(self):
        return json.dumps(self.to_dict())
