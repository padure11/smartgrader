from .models import Profile

def user_profile(request):
    """Add user profile to template context"""
    if request.user.is_authenticated:
        try:
            profile = Profile.objects.get(user=request.user)
            return {'user_profile': profile}
        except Profile.DoesNotExist:
            # Create default student profile if it doesn't exist
            profile = Profile.objects.create(user=request.user, role='student')
            return {'user_profile': profile}
    return {'user_profile': None}
