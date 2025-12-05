from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings


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

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.created_by.email}"


class Submission(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='submissions')
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
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
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return "Unknown"

    def __str__(self):
        return f"{self.full_name} - {self.test.title} - {self.score}/{self.total_questions}"
