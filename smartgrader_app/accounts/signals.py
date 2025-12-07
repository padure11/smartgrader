from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Profile

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    """
    DISABLED: Profile creation is handled in the registration view
    to allow role selection during registration.
    """
    # Do not auto-create profiles - let the registration view handle it
    pass
