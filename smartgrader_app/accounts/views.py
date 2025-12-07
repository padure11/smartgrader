from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Test, Submission, TestEnrollment, Profile, EmailVerificationToken
from .decorators import teacher_required, student_required
import json
import os
import sys
import random
import zipfile
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .omr_processor import process_omr_image, grade_submission
from django.conf import settings

# Add pdf_generator to path
sys.path.append(os.path.join(settings.BASE_DIR.parent, 'pdf_generator'))
from pdf_generator import generate_test_pdf_from_db

User = get_user_model()


def send_verification_email(user, request):
    """Send email verification link to user"""
    try:
        # Create verification token
        token = EmailVerificationToken.objects.create(user=user)

        # Build verification URL
        verification_url = request.build_absolute_uri(
            f'/accounts/verify-email/{token.token}/'
        )

        # Email subject and message
        subject = 'Verify your SmartGrader account'
        message = f"""
        Hi {user.first_name},

        Thank you for registering with SmartGrader!

        Please verify your email address by clicking the link below:
        {verification_url}

        This link will expire in 24 hours.

        If you didn't create this account, please ignore this email.

        Best regards,
        SmartGrader Team
        """

        # Send email
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending verification email: {str(e)}")
        return False


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

    try:
        data = json.loads(request.body)

        email = data.get("email")
        password = data.get("password")
        # Handle None values from JSON null
        first_name = (data.get("first_name") or "").strip()
        last_name = (data.get("last_name") or "").strip()
        role = data.get("role", "student")  # Default to student if not provided

        if not email or not password:
            return JsonResponse({"error": "Email and password required"}, status=400)

        if not first_name or not last_name:
            return JsonResponse({"error": "First name and last name required"}, status=400)

        if User.objects.filter(email=email).exists():
            return JsonResponse({"error": "Email already registered"}, status=400)

        # Create user with first and last name (inactive until email verification)
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=False  # Require email verification
        )

        # Create profile with the selected role
        # Note: Signal auto-creation is disabled to allow role selection
        profile = Profile.objects.create(user=user, role=role)

        # Send verification email
        email_sent = send_verification_email(user, request)

        if not email_sent:
            # If email fails, still create account but warn user
            return JsonResponse({
                "message": "Account created but verification email failed to send. Please contact support.",
                "email": user.email,
                "requires_verification": True
            }, status=201)

        return JsonResponse({
            "message": "Account created! Please check your email to verify your account.",
            "email": user.email,
            "requires_verification": True
        }, status=201)

    except Exception as e:
        return JsonResponse({"error": f"Registration failed: {str(e)}"}, status=500)


@csrf_exempt
def login_user(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=400)

    try:
        data = json.loads(request.body)

        email = data.get("email")
        password = data.get("password")

        user = authenticate(request, email=email, password=password)

        if user is None:
            return JsonResponse({"error": "Invalid credentials"}, status=400)

        # Check if user has verified their email
        if not user.is_active:
            return JsonResponse({
                "error": "Please verify your email address before logging in. Check your inbox for the verification link."
            }, status=403)

        login(request, user)

        # Get or create user profile
        profile, created = Profile.objects.get_or_create(user=user, defaults={'role': 'student'})

        return JsonResponse({
            "message": "Login successful",
            "email": user.email,
            "role": profile.role
        })

    except Exception as e:
        return JsonResponse({"error": f"Login failed: {str(e)}"}, status=500)


def verify_email(request, token):
    """Verify user email with token"""
    try:
        # Find token
        verification_token = EmailVerificationToken.objects.get(token=token)

        # Check if token is expired
        if verification_token.is_expired():
            return render(request, 'accounts/verification_result.html', {
                'success': False,
                'message': 'This verification link has expired. Please contact support to resend a verification email.'
            })

        # Activate user
        user = verification_token.user
        user.is_active = True
        user.save()

        # Delete used token
        verification_token.delete()

        return render(request, 'accounts/verification_result.html', {
            'success': True,
            'message': 'Email verified successfully! You can now log in to your account.'
        })

    except EmailVerificationToken.DoesNotExist:
        return render(request, 'accounts/verification_result.html', {
            'success': False,
            'message': 'Invalid verification link. Please check your email or contact support.'
        })


@login_required
def profile_page(request):
    """Display user profile information"""
    user = request.user
    profile = Profile.objects.get(user=user)

    # Get user statistics
    if profile.role == 'teacher':
        # Teacher stats
        total_tests = Test.objects.filter(created_by=user).count()
        total_submissions = Submission.objects.filter(test__created_by=user).count()
        total_students = TestEnrollment.objects.filter(test__created_by=user).values('student').distinct().count()
    else:
        # Student stats
        total_tests = TestEnrollment.objects.filter(student=user).count()
        total_submissions = Submission.objects.filter(student_user=user).count()
        avg_score = 0
        if total_submissions > 0:
            submissions = Submission.objects.filter(student_user=user, processed=True)
            if submissions.exists():
                avg_score = sum(s.percentage for s in submissions) / submissions.count()

    context = {
        'user': user,
        'profile': profile,
    }

    if profile.role == 'teacher':
        context['total_tests'] = total_tests
        context['total_submissions'] = total_submissions
        context['total_students'] = total_students
    else:
        context['total_tests'] = total_tests
        context['total_submissions'] = total_submissions
        context['avg_score'] = round(avg_score, 1) if total_submissions > 0 else 0

    return render(request, 'accounts/profile.html', context)


@login_required
@teacher_required
def test_generator_page(request):
    """Render the test generator page"""
    return render(request, 'accounts/test_generator.html')


@csrf_exempt
@login_required
@teacher_required
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


@csrf_exempt
@login_required
@teacher_required
def ai_generate_questions(request):
    """Generate test questions using AI (Claude API)"""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=400)

    try:
        import anthropic
    except ImportError:
        return JsonResponse({
            "error": "AI generation requires the 'anthropic' package. Install it with: pip install anthropic"
        }, status=500)

    try:
        data = json.loads(request.body)

        topic = data.get("topic", "").strip()
        num_questions = data.get("num_questions", 10)
        num_options = data.get("num_options", 5)
        difficulty = data.get("difficulty", "medium")

        if not topic:
            return JsonResponse({"error": "Topic is required"}, status=400)

        if num_questions < 1 or num_questions > 50:
            return JsonResponse({"error": "Number of questions must be between 1 and 50"}, status=400)

        # Get API key from environment variable
        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            return JsonResponse({
                "error": "ANTHROPIC_API_KEY environment variable not set. Please configure your API key."
            }, status=500)

        # Initialize Anthropic client
        client = anthropic.Anthropic(api_key=api_key)

        # Create prompt for Claude
        option_letters = ['A', 'B', 'C', 'D', 'E'][:num_options]
        prompt = f"""Generate {num_questions} multiple-choice questions about: {topic}

Difficulty level: {difficulty}
Number of options per question: {num_options} ({', '.join(option_letters)})

Format each question as a JSON object with this exact structure:
{{
    "question": "The question text",
    "options": ["Option A text", "Option B text", "Option C text"{', "Option D text"' if num_options >= 4 else ''}{', "Option E text"' if num_options >= 5 else ''}],
    "correct_answer": 0
}}

Where correct_answer is the index (0-{num_options-1}) of the correct option.

Return a JSON array of {num_questions} questions. Make the questions educational, clear, and appropriately challenging for {difficulty} level.
Ensure each question tests understanding of {topic}."""

        # Call Claude API
        # Using claude-3-5-haiku-20241022 (fast and cost-effective for question generation)
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=4000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse response
        response_text = message.content[0].text

        # Try to extract JSON from response
        # Claude might wrap it in markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        questions = json.loads(response_text)

        # Validate and clean the questions
        if not isinstance(questions, list):
            return JsonResponse({"error": "Invalid response format from AI"}, status=500)

        validated_questions = []
        for q in questions:
            if not isinstance(q, dict):
                continue
            if "question" not in q or "options" not in q or "correct_answer" not in q:
                continue
            if not isinstance(q["options"], list) or len(q["options"]) != num_options:
                continue
            if not isinstance(q["correct_answer"], int) or q["correct_answer"] < 0 or q["correct_answer"] >= num_options:
                continue

            validated_questions.append(q)

        if len(validated_questions) == 0:
            return JsonResponse({"error": "No valid questions generated"}, status=500)

        return JsonResponse({
            "success": True,
            "questions": validated_questions,
            "count": len(validated_questions)
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON in request"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"AI generation failed: {str(e)}"}, status=500)


@login_required
@teacher_required
def test_list_page(request):
    """Render the test list page - show only user's tests with stats"""
    tests = Test.objects.filter(created_by=request.user).order_by('-created_at')

    # Add statistics for each test
    tests_with_stats = []
    for test in tests:
        submissions = test.submissions.filter(processed=True)
        stats = {
            'test': test,
            'submission_count': submissions.count(),
            'average_percentage': 0,
            'latest_submission': None
        }

        if submissions.exists():
            percentages = [sub.percentage for sub in submissions]
            stats['average_percentage'] = round(sum(percentages) / len(percentages), 1)
            stats['latest_submission'] = submissions.order_by('-submitted_at').first()

        tests_with_stats.append(stats)

    return render(request, 'accounts/test_list.html', {'tests_with_stats': tests_with_stats})


@login_required
@teacher_required
def test_detail_page(request, test_id):
    """Render the test detail page"""
    try:
        test = Test.objects.get(id=test_id, created_by=request.user)
        return render(request, 'accounts/test_detail.html', {'test': test})
    except Test.DoesNotExist:
        return render(request, 'accounts/test_not_found.html', status=404)


@csrf_exempt
@login_required
@teacher_required
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
@teacher_required
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


@csrf_exempt
@login_required
@teacher_required
def duplicate_test_api(request, test_id):
    """Duplicate an existing test"""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=400)

    try:
        original_test = Test.objects.get(id=test_id, created_by=request.user)

        # Create a new test with the same data
        new_test = Test.objects.create(
            title=f"{original_test.title} (Copy)",
            description=original_test.description,
            questions=original_test.questions,  # JSONField is copied by value
            num_questions=original_test.num_questions,
            num_options=original_test.num_options,
            created_by=request.user
        )

        return JsonResponse({
            "message": f"Test duplicated successfully!",
            "test_id": new_test.id,
            "test_title": new_test.title
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
@teacher_required
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


def match_submission_to_student(submission, test, first_name, last_name):
    """
    Try to match a submission to an enrolled student based on name.
    Returns the matched user or None.
    """
    # Ensure first_name and last_name are strings, not None
    first_name = first_name or ''
    last_name = last_name or ''

    if not first_name and not last_name:
        return None

    # Get all enrolled students for this test
    enrollments = TestEnrollment.objects.filter(test=test).select_related('student')

    for enrollment in enrollments:
        user = enrollment.student
        # Try exact match (case-insensitive) - handle None values
        user_first = (user.first_name or '').strip().lower()
        user_last = (user.last_name or '').strip().lower()
        ocr_first = first_name.strip().lower()
        ocr_last = last_name.strip().lower()

        # Match: first and last name
        if user_first and user_last and ocr_first and ocr_last:
            if user_first == ocr_first and user_last == ocr_last:
                return user
            # Try swapped (in case OCR detected them backwards)
            if user_first == ocr_last and user_last == ocr_first:
                return user
        # Match: only last name (more unique)
        elif user_last and ocr_last and user_last == ocr_last:
            return user

    return None


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
        student_info = omr_result.get('student_info', {})

        # Grade the submission
        grading = grade_submission(detected_answers, correct_answers)

        # Save to database
        # First, save the image permanently
        submission_image_path = f"submissions/test_{test.id}_{filename}"
        with open(image_path, 'rb') as f:
            image_content = f.read()
        saved_path = default_storage.save(submission_image_path, ContentFile(image_content))

        # Extract student info from OCR (handle None values)
        first_name = (student_info.get('first_name') or '').strip()
        last_name = (student_info.get('last_name') or '').strip()

        # Try to match with enrolled student
        student_user = match_submission_to_student(None, test, first_name, last_name)

        submission = Submission.objects.create(
            test=test,
            student_user=student_user,  # Link to enrolled student if matched
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
@teacher_required
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


@login_required
@teacher_required
def submission_detail_page(request, test_id, submission_id):
    """View detailed submission with answer breakdown"""
    try:
        test = Test.objects.get(id=test_id, created_by=request.user)
        submission = Submission.objects.get(id=submission_id, test=test)
        
        # Build detailed answer breakdown
        correct_answers = [q['correct_answer'] for q in test.questions]
        answer_details = []
        
        for i, question in enumerate(test.questions):
            student_answer = submission.answers[i] if i < len(submission.answers) else None
            correct_answer = question['correct_answer']
            is_correct = student_answer == correct_answer
            
            answer_details.append({
                'question_num': i + 1,
                'question_text': question['question'],
                'options': question['options'],
                'student_answer': student_answer,
                'correct_answer': correct_answer,
                'is_correct': is_correct
            })
        
        context = {
            'test': test,
            'submission': submission,
            'answer_details': answer_details
        }
        
        return render(request, 'accounts/submission_detail.html', context)
        
    except (Test.DoesNotExist, Submission.DoesNotExist):
        return render(request, 'accounts/test_not_found.html', status=404)


@csrf_exempt
@login_required
@teacher_required
def update_submission_name(request, test_id, submission_id):
    """Update the student name on a submission"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    try:
        test = Test.objects.get(id=test_id, created_by=request.user)
        submission = Submission.objects.get(id=submission_id, test=test)

        data = json.loads(request.body)
        # Handle None values from JSON null
        first_name = (data.get('first_name') or '').strip()
        last_name = (data.get('last_name') or '').strip()

        if not first_name or not last_name:
            return JsonResponse({'error': 'Both first name and last name are required'}, status=400)

        # Update the submission
        submission.first_name = first_name
        submission.last_name = last_name

        # Try to match with enrolled student based on the updated name
        matched_student = match_submission_to_student(submission, test, first_name, last_name)
        if matched_student:
            submission.student_user = matched_student

        submission.save()

        return JsonResponse({
            'success': True,
            'full_name': submission.full_name,
            'first_name': first_name,
            'last_name': last_name,
            'matched_student': matched_student.email if matched_student else None
        })

    except (Test.DoesNotExist, Submission.DoesNotExist):
        return JsonResponse({'error': 'Test or submission not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@teacher_required
def update_test_name(request, test_id):
    """Update the test name/title"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    try:
        test = Test.objects.get(id=test_id, created_by=request.user)

        data = json.loads(request.body)
        title = data.get('title', '').strip()

        if not title:
            return JsonResponse({'error': 'Test title is required'}, status=400)

        # Update the test
        test.title = title
        test.save()

        return JsonResponse({
            'success': True,
            'title': title
        })

    except Test.DoesNotExist:
        return JsonResponse({'error': 'Test not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@teacher_required
def test_analytics_api(request, test_id):
    """Get analytics for a test"""
    try:
        test = Test.objects.get(id=test_id, created_by=request.user)
        submissions = test.submissions.filter(processed=True)
        
        if submissions.count() == 0:
            return JsonResponse({
                'count': 0,
                'message': 'No submissions yet'
            })
        
        # Calculate statistics
        scores = [sub.score for sub in submissions]
        percentages = [sub.percentage for sub in submissions]
        
        analytics = {
            'total_submissions': submissions.count(),
            'average_score': round(sum(scores) / len(scores), 2),
            'average_percentage': round(sum(percentages) / len(percentages), 2),
            'highest_score': max(scores),
            'lowest_score': min(scores),
            'pass_rate': round(len([p for p in percentages if p >= 60]) / len(percentages) * 100, 2),
            'score_distribution': {
                'excellent': len([p for p in percentages if p >= 80]),
                'good': len([p for p in percentages if 60 <= p < 80]),
                'needs_improvement': len([p for p in percentages if p < 60])
            }
        }
        
        # Question difficulty analysis
        question_stats = []
        for i in range(test.num_questions):
            correct_count = sum(1 for sub in submissions if i < len(sub.answers) and sub.answers[i] == test.questions[i]['correct_answer'])
            difficulty = round(correct_count / submissions.count() * 100, 2)
            
            question_stats.append({
                'question_num': i + 1,
                'correct_count': correct_count,
                'difficulty_percentage': difficulty,
                'question_text': test.questions[i]['question'][:50] + '...' if len(test.questions[i]['question']) > 50 else test.questions[i]['question']
            })
        
        # Sort by difficulty (hardest first)
        question_stats.sort(key=lambda x: x['difficulty_percentage'])
        
        analytics['question_difficulty'] = question_stats[:5]  # Top 5 hardest questions
        
        return JsonResponse(analytics)
        
    except Test.DoesNotExist:
        return JsonResponse({"error": "Test not found"}, status=404)


import csv
from django.http import HttpResponse

@login_required
@teacher_required
def export_results_csv(request, test_id):
    """Export test results to CSV"""
    try:
        test = Test.objects.get(id=test_id, created_by=request.user)
        submissions = test.submissions.filter(processed=True).order_by('-percentage')
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="test_{test_id}_results.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        header = ['Rank', 'First Name', 'Last Name', 'Score', 'Total', 'Percentage', 'Grade', 'Submitted At']
        
        # Add question columns
        for i in range(test.num_questions):
            header.append(f'Q{i+1}')
        
        writer.writerow(header)
        
        # Write data
        for rank, submission in enumerate(submissions, start=1):
            grade = 'A' if submission.percentage >= 90 else \
                   'B' if submission.percentage >= 80 else \
                   'C' if submission.percentage >= 70 else \
                   'D' if submission.percentage >= 60 else 'F'
            
            row = [
                rank,
                submission.first_name or '',
                submission.last_name or '',
                submission.score,
                submission.total_questions,
                f'{submission.percentage}%',
                grade,
                submission.submitted_at.strftime('%Y-%m-%d %H:%M')
            ]
            
            # Add answers (show option letter)
            option_letters = ['A', 'B', 'C', 'D', 'E']
            for i in range(test.num_questions):
                if i < len(submission.answers) and submission.answers[i] is not None:
                    answer_idx = submission.answers[i]
                    if answer_idx < len(option_letters):
                        row.append(option_letters[answer_idx])
                    else:
                        row.append(str(answer_idx))
                else:
                    row.append('-')
            
            writer.writerow(row)
        
        # Write summary statistics
        writer.writerow([])
        writer.writerow(['SUMMARY STATISTICS'])
        writer.writerow(['Total Submissions', submissions.count()])
        
        if submissions.count() > 0:
            avg_score = sum(s.score for s in submissions) / submissions.count()
            avg_pct = sum(s.percentage for s in submissions) / submissions.count()
            writer.writerow(['Average Score', f'{avg_score:.2f}/{test.num_questions}'])
            writer.writerow(['Average Percentage', f'{avg_pct:.2f}%'])
            writer.writerow(['Highest Score', max(s.score for s in submissions)])
            writer.writerow(['Lowest Score', min(s.score for s in submissions)])
            pass_count = len([s for s in submissions if s.percentage >= 60])
            writer.writerow(['Pass Rate (≥60%)', f'{pass_count}/{submissions.count()} ({pass_count/submissions.count()*100:.1f}%)'])
        
        return response
        
    except Test.DoesNotExist:
        return HttpResponse("Test not found", status=404)


# ============================================
# STUDENT PORTAL VIEWS
# ============================================

@login_required
@student_required
def student_dashboard(request):
    """Student dashboard showing enrolled tests and results"""
    # Get enrolled tests with their submissions
    enrollments = TestEnrollment.objects.filter(student=request.user).select_related('test')
    
    tests_data = []
    for enrollment in enrollments:
        test = enrollment.test
        # Get student's submission for this test
        submission = Submission.objects.filter(
            test=test,
            student_user=request.user
        ).first()
        
        tests_data.append({
            'test': test,
            'enrollment': enrollment,
            'submission': submission,
            'has_result': submission is not None and submission.processed
        })
    
    context = {
        'tests_data': tests_data,
        'student': request.user
    }
    
    return render(request, 'accounts/student_dashboard.html', context)


@csrf_exempt
@login_required
@student_required
def enroll_in_test(request):
    """Enroll a student in a test using enrollment code"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=400)
    
    try:
        data = json.loads(request.body)
        enrollment_code = data.get('enrollment_code', '').strip().upper()
        
        if not enrollment_code:
            return JsonResponse({'error': 'Enrollment code is required'}, status=400)
        
        # Find test by enrollment code
        try:
            test = Test.objects.get(enrollment_code=enrollment_code)
        except Test.DoesNotExist:
            return JsonResponse({'error': 'Invalid enrollment code'}, status=404)
        
        # Check if already enrolled
        if TestEnrollment.objects.filter(student=request.user, test=test).exists():
            return JsonResponse({'error': 'You are already enrolled in this test'}, status=400)
        
        # Create enrollment
        enrollment = TestEnrollment.objects.create(student=request.user, test=test)
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully enrolled in "{test.title}"',
            'test_id': test.id,
            'test_title': test.title
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@student_required
def student_test_result(request, test_id):
    """View detailed results for a specific test"""
    try:
        test = Test.objects.get(id=test_id)
        
        # Check if student is enrolled
        if not TestEnrollment.objects.filter(student=request.user, test=test).exists():
            return render(request, 'accounts/error.html', {
                'error': 'You are not enrolled in this test'
            }, status=403)
        
        # Get student's submission
        submission = Submission.objects.filter(
            test=test,
            student_user=request.user
        ).first()
        
        if not submission:
            return render(request, 'accounts/error.html', {
                'error': 'No results available yet. Your answer sheet may not have been uploaded.'
            }, status=404)
        
        if not submission.processed:
            return render(request, 'accounts/error.html', {
                'error': 'Your submission is still being processed. Please check back later.'
            }, status=404)
        
        # Prepare answer details
        answer_details = []
        for i, question in enumerate(test.questions):
            student_answer = submission.answers[i] if i < len(submission.answers) else None
            correct_answer = question['correct_answer']
            is_correct = student_answer == correct_answer

            answer_details.append({
                'question_num': i + 1,
                'question_text': question['question'],
                'options': question['options'],
                'student_answer': student_answer,
                'correct_answer': correct_answer,
                'is_correct': is_correct
            })

        # Calculate performance analysis
        all_submissions = Submission.objects.filter(test=test, processed=True)
        analysis = None

        if all_submissions.count() > 0:
            # Class statistics
            class_percentages = [s.percentage for s in all_submissions]
            class_average = sum(class_percentages) / len(class_percentages)

            # Student ranking
            submissions_sorted = sorted(all_submissions, key=lambda s: s.percentage, reverse=True)
            student_rank = next((i + 1 for i, s in enumerate(submissions_sorted) if s.id == submission.id), None)

            # Performance vs class average
            performance_diff = submission.percentage - class_average

            # Identify strengths and weaknesses
            correct_count = sum(1 for detail in answer_details if detail['is_correct'])
            incorrect_count = len(answer_details) - correct_count

            # Performance level
            if submission.percentage >= 90:
                performance_level = "Excellent"
                performance_message = "Outstanding performance! Keep up the great work."
            elif submission.percentage >= 80:
                performance_level = "Very Good"
                performance_message = "Great job! You're performing well above average."
            elif submission.percentage >= 70:
                performance_level = "Good"
                performance_message = "Good work! A bit more practice and you'll excel."
            elif submission.percentage >= 60:
                performance_level = "Satisfactory"
                performance_message = "You're on the right track. Focus on areas that need improvement."
            else:
                performance_level = "Needs Improvement"
                performance_message = "Don't be discouraged! Review the material and try again."

            analysis = {
                'class_average': round(class_average, 1),
                'student_rank': student_rank,
                'total_students': all_submissions.count(),
                'performance_diff': round(performance_diff, 1),
                'performance_level': performance_level,
                'performance_message': performance_message,
                'correct_count': correct_count,
                'incorrect_count': incorrect_count,
                'above_average': performance_diff > 0
            }

        context = {
            'test': test,
            'submission': submission,
            'answer_details': answer_details,
            'analysis': analysis
        }

        return render(request, 'accounts/student_result.html', context)
        
    except Test.DoesNotExist:
        return render(request, 'accounts/error.html', {
            'error': 'Test not found'
        }, status=404)
