from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import Test
import json
import os
import sys
import random

# Add pdf_generator to path
sys.path.append(os.path.join(settings.BASE_DIR.parent, 'pdf_generator'))
from pdf_generator import generate_test_pdf_from_db

User = get_user_model()

def landing(request):
    return render(request, 'accounts/landing.html')


def login_page(request):
    if request.user.is_authenticated:
        return redirect('test-list')
    return render(request, 'accounts/login.html')

def register_page(request):
    if request.user.is_authenticated:
        return redirect('test-list')
    return render(request, 'accounts/register.html')


@csrf_exempt
def register_user(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=400)

    data = json.loads(request.body)

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return JsonResponse({"error": "Email and password required"}, status=400)

    if User.objects.filter(email=email).exists():
        return JsonResponse({"error": "Email already registered"}, status=400)

    user = User.objects.create_user(email=email, password=password)
    login(request, user)  # Auto login after registration

    return JsonResponse({"message": "User created successfully", "email": user.email}, status=201)


@csrf_exempt
def login_user(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=400)

    data = json.loads(request.body)

    email = data.get("email")
    password = data.get("password")

    user = authenticate(request, email=email, password=password)

    if user is None:
        return JsonResponse({"error": "Invalid credentials"}, status=400)

    login(request, user)

    return JsonResponse({"message": "Login successful", "email": user.email})


@login_required
def test_generator_page(request):
    """Render the test generator page"""
    return render(request, 'accounts/test_generator.html')


@csrf_exempt
@login_required
def create_test(request):
    """API endpoint to create a new test"""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=400)

    try:
        data = json.loads(request.body)

        # Validate required fields
        title = data.get("title")
        questions = data.get("questions", [])
        num_options = data.get("num_options", 5)

        if not title:
            return JsonResponse({"error": "Test title is required"}, status=400)

        if not questions or len(questions) == 0:
            return JsonResponse({"error": "At least one question is required"}, status=400)

        # Check if randomization is enabled
        enable_randomization = data.get("enable_randomization", False)
        num_variants = data.get("num_variants", 1)
        questions_per_variant = data.get("questions_per_variant", len(questions))

        created_tests = []

        if enable_randomization and num_variants > 1:
            # Validate randomization parameters
            if questions_per_variant > len(questions):
                return JsonResponse({
                    "error": f"Cannot create variants with {questions_per_variant} questions when you only have {len(questions)} questions"
                }, status=400)

            # Create multiple randomized test variants
            for i in range(num_variants):
                # Randomly select questions
                variant_questions = random.sample(questions, questions_per_variant)

                # Create test variant
                variant_title = f"{title} - Variant {i + 1}"
                test = Test.objects.create(
                    title=variant_title,
                    description=data.get("description", ""),
                    questions=variant_questions,
                    num_questions=len(variant_questions),
                    num_options=num_options,
                    created_by=request.user
                )
                created_tests.append(test)

            response_data = {
                "message": f"Successfully created {num_variants} test variants!",
                "test_ids": [test.id for test in created_tests],
                "num_variants": num_variants,
                "questions_per_variant": questions_per_variant
            }

        else:
            # Create single test (no randomization)
            test = Test.objects.create(
                title=title,
                description=data.get("description", ""),
                questions=questions,
                num_questions=len(questions),
                num_options=num_options,
                created_by=request.user
            )
            created_tests.append(test)

            response_data = {
                "message": "Test created successfully!",
                "test_id": test.id,
                "title": test.title,
                "num_questions": test.num_questions
            }

        # If generate_pdf flag is set, generate PDFs for all created tests
        if data.get("generate_pdf", False):
            try:
                # Create media directory if it doesn't exist
                media_root = os.path.join(settings.BASE_DIR, 'media', 'tests')
                os.makedirs(media_root, exist_ok=True)

                pdf_urls = []
                for test in created_tests:
                    pdf_filename = f"test_{test.id}.pdf"
                    pdf_path = os.path.join(media_root, pdf_filename)
                    generate_test_pdf_from_db(test, pdf_path)
                    pdf_urls.append(f"/media/tests/{pdf_filename}")

                if len(created_tests) > 1:
                    response_data["message"] = f"{num_variants} test variants created and PDFs generated successfully!"
                    response_data["pdf_urls"] = pdf_urls
                else:
                    response_data["message"] = "Test created and PDF generated successfully!"
                    response_data["pdf_url"] = pdf_urls[0]

            except Exception as e:
                response_data["message"] = "Tests created but PDF generation failed."
                response_data["pdf_error"] = str(e)

        return JsonResponse(response_data, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def test_list_page(request):
    """Render the test list page - show only user's tests"""
    tests = Test.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'accounts/test_list.html', {'tests': tests})


@login_required
def test_detail_page(request, test_id):
    """Render the test detail page"""
    try:
        test = Test.objects.get(id=test_id, created_by=request.user)
        return render(request, 'accounts/test_detail.html', {'test': test})
    except Test.DoesNotExist:
        return render(request, 'accounts/test_not_found.html', status=404)


@csrf_exempt
@login_required
def generate_pdf_api(request, test_id):
    """Generate PDF for an existing test"""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=400)

    try:
        test = Test.objects.get(id=test_id, created_by=request.user)

        # Create media directory if it doesn't exist
        media_root = os.path.join(settings.BASE_DIR, 'media', 'tests')
        os.makedirs(media_root, exist_ok=True)

        # Generate PDF
        pdf_filename = f"test_{test.id}.pdf"
        pdf_path = os.path.join(media_root, pdf_filename)
        generate_test_pdf_from_db(test, pdf_path)

        return JsonResponse({
            "message": "PDF generated successfully!",
            "pdf_url": f"/media/tests/{pdf_filename}"
        }, status=200)

    except Test.DoesNotExist:
        return JsonResponse({"error": "Test not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@login_required
def delete_test_api(request, test_id):
    """Delete a test"""
    if request.method != "DELETE" and request.method != "POST":
        return JsonResponse({"error": "Only DELETE or POST allowed"}, status=400)

    try:
        test = Test.objects.get(id=test_id, created_by=request.user)
        test_title = test.title

        # Delete associated PDF if it exists
        pdf_path = os.path.join(settings.BASE_DIR, 'media', 'tests', f"test_{test.id}.pdf")
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

        test.delete()

        return JsonResponse({
            "message": f"Test '{test_title}' deleted successfully!"
        }, status=200)

    except Test.DoesNotExist:
        return JsonResponse({"error": "Test not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def logout_view(request):
    """Logout the user"""
    logout(request)
    return redirect('landing')