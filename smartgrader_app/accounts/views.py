from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import Test, Submission
import json
import os
import sys
import random
import zipfile
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .omr_processor import process_omr_image, grade_submission

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

@csrf_exempt
@login_required
def upload_submissions(request, test_id):
    """Upload and process student submissions (images or zip file)"""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=400)

    try:
        test = Test.objects.get(id=test_id, created_by=request.user)
        
        # Get correct answers from test
        correct_answers = [q['correct_answer'] for q in test.questions]
        
        uploaded_files = request.FILES.getlist('files')
        zip_file = request.FILES.get('zip_file')
        
        results = []
        errors = []
        
        # Handle zip file upload
        if zip_file:
            try:
                # Save zip temporarily
                zip_path = os.path.join(settings.BASE_DIR, 'media', 'temp', zip_file.name)
                os.makedirs(os.path.dirname(zip_path), exist_ok=True)
                
                with open(zip_path, 'wb+') as destination:
                    for chunk in zip_file.chunks():
                        destination.write(chunk)
                
                # Extract and process images
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    extract_path = os.path.join(settings.BASE_DIR, 'media', 'temp', 'extracted')
                    zip_ref.extractall(extract_path)
                    
                    # Process each image in zip
                    for filename in os.listdir(extract_path):
                        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                            image_path = os.path.join(extract_path, filename)
                            result = process_single_submission(test, image_path, filename, correct_answers)
                            results.append(result)
                
                # Cleanup
                os.remove(zip_path)
                import shutil
                shutil.rmtree(extract_path)
                
            except Exception as e:
                errors.append(f"Error processing zip file: {str(e)}")
        
        # Handle individual image uploads
        elif uploaded_files:
            for uploaded_file in uploaded_files:
                # Save file temporarily
                temp_path = os.path.join(settings.BASE_DIR, 'media', 'temp', uploaded_file.name)
                os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                
                with open(temp_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                
                # Process image
                result = process_single_submission(test, temp_path, uploaded_file.name, correct_answers)
                results.append(result)
                
                # Cleanup
                os.remove(temp_path)
        else:
            return JsonResponse({"error": "No files uploaded"}, status=400)
        
        return JsonResponse({
            "message": f"Processed {len(results)} submission(s)",
            "results": results,
            "errors": errors
        }, status=200)
        
    except Test.DoesNotExist:
        return JsonResponse({"error": "Test not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def process_single_submission(test, image_path, filename, correct_answers):
    """Process a single submission image"""
    try:
        # Run OMR processing
        omr_result = process_omr_image(image_path, test.num_questions, test.num_options)
        
        if not omr_result['success']:
            return {
                'filename': filename,
                'success': False,
                'error': omr_result['error']
            }
        
        detected_answers = omr_result['answers']
        first_name = omr_result.get('first_name')
        last_name = omr_result.get('last_name')

        # Grade the submission
        grading = grade_submission(detected_answers, correct_answers)

        # Save to database
        # First, save the image permanently
        submission_image_path = f"submissions/test_{test.id}_{filename}"
        with open(image_path, 'rb') as f:
            image_content = f.read()
        saved_path = default_storage.save(submission_image_path, ContentFile(image_content))

        submission = Submission.objects.create(
            test=test,
            first_name=first_name,
            last_name=last_name,
            image=saved_path,
            answers=detected_answers,
            score=grading['score'],
            total_questions=grading['total'],
            percentage=grading['percentage'],
            processed=True
        )

        return {
            'filename': filename,
            'success': True,
            'submission_id': submission.id,
            'student_name': submission.full_name,
            'score': grading['score'],
            'total': grading['total'],
            'percentage': grading['percentage']
        }
        
    except Exception as e:
        return {
            'filename': filename,
            'success': False,
            'error': str(e)
        }


@login_required
def get_test_submissions(request, test_id):
    """Get all submissions for a test"""
    try:
        test = Test.objects.get(id=test_id, created_by=request.user)
        submissions = test.submissions.all()
        
        submissions_data = [{
            'id': sub.id,
            'student_name': sub.full_name,
            'score': sub.score,
            'total': sub.total_questions,
            'percentage': sub.percentage,
            'submitted_at': sub.submitted_at.strftime('%Y-%m-%d %H:%M'),
            'image_url': sub.image.url if sub.image else None
        } for sub in submissions]
        
        return JsonResponse({
            'submissions': submissions_data,
            'count': len(submissions_data)
        }, status=200)
        
    except Test.DoesNotExist:
        return JsonResponse({"error": "Test not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
