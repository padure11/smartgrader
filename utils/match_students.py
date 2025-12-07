"""
Match existing submissions to enrolled students.
Run this to retroactively link submissions that were uploaded before the matching feature.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'smartgrader_app'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartgrader_app.settings')
django.setup()

from accounts.models import Submission, TestEnrollment

def match_submission_to_student(submission, test):
    """
    Try to match a submission to an enrolled student based on name.
    """
    # Handle None values from database
    first_name = (submission.first_name or '').strip()
    last_name = (submission.last_name or '').strip()

    if not first_name and not last_name:
        return None

    # Get all enrolled students for this test
    enrollments = TestEnrollment.objects.filter(test=test).select_related('student')

    for enrollment in enrollments:
        user = enrollment.student
        # Try exact match (case-insensitive) - handle None values
        user_first = (user.first_name or '').strip().lower()
        user_last = (user.last_name or '').strip().lower()
        ocr_first = first_name.lower()
        ocr_last = last_name.lower()

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


def match_all_submissions():
    """Match all unlinked submissions to enrolled students"""
    print("="*70)
    print("MATCHING SUBMISSIONS TO STUDENTS")
    print("="*70)

    # Get all submissions without a student_user link
    unlinked = Submission.objects.filter(student_user__isnull=True).select_related('test')

    print(f"\nFound {unlinked.count()} unlinked submissions\n")

    matched_count = 0
    unmatched_count = 0

    for submission in unlinked:
        test = submission.test
        matched_student = match_submission_to_student(submission, test)

        if matched_student:
            submission.student_user = matched_student
            submission.save(update_fields=['student_user'])
            matched_count += 1
            print(f"✓ Matched: {submission.first_name} {submission.last_name} → {matched_student.email}")
        else:
            unmatched_count += 1
            print(f"✗ No match: {submission.first_name} {submission.last_name} (Test: {test.title})")

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total unlinked submissions: {unlinked.count()}")
    print(f"Successfully matched: {matched_count}")
    print(f"Still unmatched: {unmatched_count}")

    if unmatched_count > 0:
        print("\nUnmatched submissions may be:")
        print("  - Students not enrolled in the test")
        print("  - Names don't match enrolled student names")
        print("  - OCR read names incorrectly")
        print("\nYou can manually update names in the UI and they will auto-match.")

    print("="*70)


if __name__ == '__main__':
    try:
        match_all_submissions()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
