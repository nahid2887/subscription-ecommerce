from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class TermsAndConditions(models.Model):
    """
    Terms and Conditions document for the subscription and e-commerce platform.
    Allows versioning, active status management, and audit tracking.
    """
    title = models.CharField(
        max_length=255,
        default='Terms and Conditions',
        help_text="Title of the terms and conditions document."
    )
    content = models.TextField(
        help_text="Full text or formatted Markdown/HTML content of the terms and conditions."
    )
    version = models.CharField(
        max_length=50,
        default='1.0',
        help_text="Document version identifier, e.g. '1.0', '2026.1'."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether this version is the currently published/active terms and conditions."
    )
    effective_date = models.DateTimeField(
        default=timezone.now,
        help_text="Date and time when this version takes legal effect."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_terms',
        help_text="Super admin who initially created this terms entry."
    )
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='updated_terms',
        help_text="Super admin who last edited this terms entry."
    )

    class Meta:
        verbose_name = "Terms and Conditions"
        verbose_name_plural = "Terms and Conditions"
        ordering = ['-is_active', '-created_at']

    def __str__(self):
        status_tag = " [Active]" if self.is_active else ""
        return f"{self.title} (v{self.version}){status_tag}"

    def save(self, *args, **kwargs):
        # If this instance is active, ensure all other versions are marked inactive
        if self.is_active:
            if self.pk:
                TermsAndConditions.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
            else:
                TermsAndConditions.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active(cls):
        """
        Retrieves the current active terms, or falls back to latest existing, or None.
        """
        active = cls.objects.filter(is_active=True).order_by('-updated_at').first()
        if not active:
            active = cls.objects.order_by('-created_at').first()
            if active:
                active.is_active = True
                active.save(update_fields=['is_active'])
        return active
