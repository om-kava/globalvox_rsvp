from django.db import models

class Invitee(models.Model):
    """
    Represents an event invitee contact record.
    """
    external_id = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="ID from imported CSV if provided")
    name = models.CharField(max_length=255, help_text="Full name of invitee")
    phone = models.CharField(max_length=32, db_index=True, help_text="Phone number (E.164 or standardized format)")
    email = models.EmailField(max_length=254, db_index=True, help_text="Invitee email address")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone', 'email'], name='idx_invitee_phone_email'),
        ]

    def __str__(self):
        return f"{self.name} ({self.phone})"

    @property
    def phone_masked(self) -> str:
        """
        Returns a privacy-masked representation of the phone number.
        Example: +919876543210 -> +91 98765 ****0
        """
        raw = self.phone.strip()
        if len(raw) < 7:
            return raw
        return f"{raw[:7]} ****{raw[-2:]}"
