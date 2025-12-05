import cv2
import numpy as np
import sys
import os
import re

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

# Add grade_processor to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'grade_processor'))
import utils


def order_points(pts):
    """Order points clockwise: top-left, top-right, bottom-right, bottom-left"""
    rect = np.zeros((4, 2), dtype="float32")

    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # Top-left (smallest sum)
    rect[2] = pts[np.argmax(s)]  # Bottom-right (largest sum)

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # Top-right (smallest difference)
    rect[3] = pts[np.argmax(diff)]  # Bottom-left (largest difference)

    return rect


def find_answer_sheet(contours, img_original):
    """Find the largest rectangular contour (answer sheet)"""
    largest_area = 0
    largest_contour = None

    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

        if len(approx) == 4:
            area = cv2.contourArea(contour)
            if area > largest_area:
                largest_area = area
                largest_contour = approx

    if largest_contour is not None:
        pts = largest_contour.reshape(4, 2)
        rect = order_points(pts)

        output_width = 550
        output_height = 700

        dst = np.array([
            [0, 0],
            [output_width - 1, 0],
            [output_width - 1, output_height - 1],
            [0, output_height - 1]
        ], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img_original, M, (output_width, output_height))

        return warped
    else:
        return None


def extract_student_info(img):
    """
    Extract student name and surname from the top portion of the image using OCR

    Args:
        img: Grayscale image of the answer sheet

    Returns:
        dict with 'first_name' and 'last_name' keys
    """
    if not HAS_TESSERACT:
        return {'first_name': None, 'last_name': None}

    try:
        # Extract top portion of image (first 15% contains name/surname fields)
        height, width = img.shape
        name_region = img[0:int(height * 0.15), :]

        # Preprocess for better OCR
        # Apply adaptive thresholding
        name_region = cv2.adaptiveThreshold(
            name_region, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # Denoise
        name_region = cv2.fastNlMeansDenoising(name_region, None, 10, 7, 21)

        # Extract text using OCR
        text = pytesseract.image_to_string(name_region, config='--psm 6')

        # Parse name and surname from text
        lines = text.strip().split('\n')
        first_name = None
        last_name = None

        for i, line in enumerate(lines):
            line = line.strip()

            # Look for "Name" field
            if 'name' in line.lower() and 'surname' not in line.lower():
                # Try to extract name from same line
                name_match = re.search(r'name[:\s_]*([A-Za-z]+)', line, re.IGNORECASE)
                if name_match:
                    first_name = name_match.group(1).strip()
                # If not on same line, check next line
                elif i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Remove underscores and get first word
                    next_line = re.sub(r'_+', '', next_line)
                    words = next_line.split()
                    if words:
                        first_name = words[0]

            # Look for "Surname" field
            if 'surname' in line.lower() or 'last name' in line.lower():
                # Try to extract surname from same line
                surname_match = re.search(r'surname[:\s_]*([A-Za-z]+)', line, re.IGNORECASE)
                if surname_match:
                    last_name = surname_match.group(1).strip()
                # If not on same line, check next line
                elif i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Remove underscores and get first word
                    next_line = re.sub(r'_+', '', next_line)
                    words = next_line.split()
                    if words:
                        last_name = words[0]

        return {
            'first_name': first_name,
            'last_name': last_name
        }

    except Exception as e:
        print(f"Error extracting student info: {e}")
        return {'first_name': None, 'last_name': None}


def detect_answers(img, num_questions=20, num_options=5):
    """
    Detect marked answers on OMR sheet
    Returns array of selected answer indices for each question
    """
    # Ensure image dimensions are divisible
    height, width = img.shape

    # Calculate target dimensions that are evenly divisible
    target_height = (height // num_questions) * num_questions
    target_width = (width // num_options) * num_options

    # Resize if necessary
    if height != target_height or width != target_width:
        img = cv2.resize(img, (target_width, target_height))

    # Split into rows (questions)
    rows = np.vsplit(img, num_questions)
    detected_answers = []

    for row in rows:
        # Split row into columns (options)
        cols = np.hsplit(row, num_options)
        max_white_pixels = 0
        selected_option = -1

        for idx, col in enumerate(cols):
            white_pixels = cv2.countNonZero(col)
            if white_pixels > max_white_pixels:
                max_white_pixels = white_pixels
                selected_option = idx

        detected_answers.append(selected_option if selected_option != -1 else None)

    return detected_answers


def process_omr_image(image_path, num_questions=20, num_options=5):
    """
    Process an OMR image and return detected answers

    Args:
        image_path: Path to the OMR image
        num_questions: Number of questions on the test
        num_options: Number of options per question (default 5 for A-E)

    Returns:
        dict with 'success', 'answers', and 'error' keys
    """
    try:
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            return {'success': False, 'error': 'Could not read image file'}

        # Resize
        imgWidth = 550
        imgHeight = 700
        img = cv2.resize(img, (imgWidth, imgHeight))

        # Convert to grayscale
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply blur
        img_blur = cv2.GaussianBlur(img_gray, (5, 5), 1)

        # Edge detection
        img_canny = cv2.Canny(img_blur, 10, 50)

        # Find contours
        contours, _ = cv2.findContours(img_canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

        # Find and warp answer sheet
        answer_sheet = find_answer_sheet(contours, img_gray)

        if answer_sheet is None:
            return {'success': False, 'error': 'Could not find answer sheet rectangle in image'}

        # Extract student name and surname from original grayscale image
        student_info = extract_student_info(img_gray)

        # Threshold the image
        _, img_threshold = cv2.threshold(answer_sheet, 150, 255, cv2.THRESH_BINARY_INV)

        # Detect answers
        answers = detect_answers(img_threshold, num_questions, num_options)

        return {
            'success': True,
            'answers': answers,
            'first_name': student_info['first_name'],
            'last_name': student_info['last_name'],
            'error': None
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Error processing image: {str(e)}',
            'answers': None
        }


def grade_submission(detected_answers, correct_answers):
    """
    Grade a submission by comparing detected answers with correct answers

    Args:
        detected_answers: List of detected answer indices
        correct_answers: List of correct answer indices from test

    Returns:
        dict with score, total, percentage, and details
    """
    score = 0
    total = len(correct_answers)
    details = []

    for i, (detected, correct) in enumerate(zip(detected_answers, correct_answers)):
        is_correct = detected == correct
        if is_correct:
            score += 1

        details.append({
            'question': i + 1,
            'detected': detected,
            'correct': correct,
            'is_correct': is_correct
        })

    percentage = (score / total * 100) if total > 0 else 0

    return {
        'score': score,
        'total': total,
        'percentage': round(percentage, 2),
        'details': details
    }
