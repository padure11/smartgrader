from .models import Profile

def user_profile(request):
    """Add user profile to template context"""
    if request.user.is_authenticated:
        # Use get_or_create to safely handle missing profiles
        # This only creates if it doesn't exist, won't override existing role
        profile, created = Profile.objects.get_or_create(
            user=request.user,
            defaults={'role': 'student'}
        )
        return {'user_profile': profile}
    return {'user_profile': None}
