from django.shortcuts import redirect
from django.http import JsonResponse
from functools import wraps
from .models import Profile


def teacher_required(view_func):
    """
    Decorator to ensure only teachers can access a view.
    Returns 403 JSON error for AJAX requests, redirects to student dashboard for regular requests.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if user is authenticated (should already be handled by @login_required)
        if not request.user.is_authenticated:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Authentication required'}, status=401)
            return redirect('login')

        # Get or create profile
        try:
            profile = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            # Create default student profile if doesn't exist
            profile = Profile.objects.create(user=request.user, role='student')

        # Check if user is a teacher
        if profile.role != 'teacher':
            # For AJAX requests, return JSON error
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                return JsonResponse({
                    'error': 'Access denied. This feature is only available to teachers.'
                }, status=403)
            # For regular requests, redirect to student dashboard
            return redirect('student-dashboard')

        # User is a teacher, proceed with the view
        return view_func(request, *args, **kwargs)

    return wrapper


def student_required(view_func):
    """
    Decorator to ensure only students can access a view.
    Redirects teachers to their test list.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Authentication required'}, status=401)
            return redirect('login')

        # Get or create profile
        try:
            profile = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            # Create default student profile if doesn't exist
            profile = Profile.objects.create(user=request.user, role='student')

        # Check if user is a student
        if profile.role == 'teacher':
            # Redirect teachers to their test list
            return redirect('test-list')

        # User is a student, proceed with the view
        return view_func(request, *args, **kwargs)

    return wrapper
