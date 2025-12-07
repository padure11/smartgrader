from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import secrets
import string
import uuid


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, default='student')
    image = models.ImageField(upload_to='profiles/', blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.email}"


class Test(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    questions = models.JSONField()  # Stores test questions and answers as JSON
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tests')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    num_questions = models.IntegerField()
    num_options = models.IntegerField(default=5)
    enrollment_code = models.CharField(max_length=8, unique=True, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Generate unique enrollment code if not exists
        if not self.enrollment_code:
            self.enrollment_code = self.generate_enrollment_code()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_enrollment_code():
        """Generate a unique 8-character enrollment code"""
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(secrets.choice(chars) for _ in range(8))
            if not Test.objects.filter(enrollment_code=code).exists():
                return code

    def __str__(self):
        return f"{self.title} - {self.created_by.email}"


class TestEnrollment(models.Model):
    """Track which students are enrolled in which tests"""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'test')
        ordering = ['-enrolled_at']

    def __str__(self):
        return f"{self.student.email} enrolled in {self.test.title}"


class Submission(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='submissions')
    student_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='submissions', blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    image = models.ImageField(upload_to='submissions/')
    answers = models.JSONField()  # Stores detected answers as array [0, 1, 2, ...] where index is question number
    score = models.IntegerField()  # Number of correct answers
    total_questions = models.IntegerField()
    percentage = models.FloatField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-submitted_at']

    @property
    def full_name(self):
        """Return full name of student"""
        if self.student_user:
            return f"{self.student_user.first_name} {self.student_user.last_name}".strip() or self.student_user.email
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return "Unknown"

    @property
    def grade(self):
        """Calculate letter grade based on percentage"""
        if self.percentage >= 90:
            return 'A'
        elif self.percentage >= 80:
            return 'B'
        elif self.percentage >= 70:
            return 'C'
        elif self.percentage >= 60:
            return 'D'
        else:
            return 'F'

    def __str__(self):
        return f"{self.full_name} - {self.test.title} - {self.score}/{self.total_questions}"


class EmailVerificationToken(models.Model):
    """Token for email verification during registration"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='verification_tokens')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        # Set expiration to 24 hours from creation
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_expired(self):
        """Check if token has expired"""
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Verification token for {self.user.email}"
