import cv2
import numpy as np
import sys
import os
import re
import traceback

# Add grade_processor to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'grade_processor'))
import utils

# Try to import pytesseract for OCR
try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False
    print("Warning: pytesseract not installed. OCR name extraction will be disabled.")


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


def extract_student_info(img, debug_path=None):
    """
    Extract student name and surname from the top portion of the image using OCR

    Args:
        img: Grayscale image of the answer sheet
        debug_path: Optional path to save debug images

    Returns:
        dict with 'first_name', 'last_name', and 'debug_text' keys
    """
    if not HAS_TESSERACT:
        return {'first_name': None, 'last_name': None, 'debug_text': 'Tesseract not installed'}

    try:
        # Extract top portion of image (first 25% contains name/surname fields)
        height, width = img.shape
        name_region = img[0:int(height * 0.25), :]

        print(f"\n=== OCR Name Extraction ===")
        print(f"Image region size: {name_region.shape}")

        # Save original region for debugging
        if debug_path:
            cv2.imwrite(f"{debug_path}_1_original_region.png", name_region)

        # Try multiple preprocessing approaches for better OCR
        preprocessed_images = []

        # Approach 1: Simple threshold
        _, thresh1 = cv2.threshold(name_region, 127, 255, cv2.THRESH_BINARY)
        preprocessed_images.append(('simple_binary', thresh1))

        # Approach 2: Inverted threshold (for dark text on light background)
        _, thresh2 = cv2.threshold(name_region, 127, 255, cv2.THRESH_BINARY_INV)
        preprocessed_images.append(('inverted_binary', thresh2))

        # Approach 3: Adaptive threshold
        adaptive = cv2.adaptiveThreshold(
            name_region, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )
        preprocessed_images.append(('adaptive', adaptive))

        # Approach 4: Enhanced preprocessing
        enhanced = cv2.equalizeHist(name_region)
        enhanced = cv2.bilateralFilter(enhanced, 5, 50, 50)
        _, enhanced = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        preprocessed_images.append(('enhanced', enhanced))

        # Try OCR on each preprocessed version
        best_result = {'first_name': None, 'last_name': None}
        all_texts = []

        for method_name, processed_img in preprocessed_images:
            if debug_path:
                cv2.imwrite(f"{debug_path}_2_{method_name}.png", processed_img)

            # Try multiple PSM modes
            for psm in [6, 11, 13]:
                try:
                    config = f'--oem 3 --psm {psm}'
                    text = pytesseract.image_to_string(processed_img, config=config)
                    all_texts.append(f"\n--- {method_name} (PSM {psm}) ---\n{text}")

                    # Parse the extracted text
                    result = parse_name_from_text(text)

                    # Keep the best result (one with both names if possible)
                    if result['first_name'] and result['last_name']:
                        print(f"✓ Found both names using {method_name} PSM {psm}")
                        best_result = result
                        break
                    elif result['first_name'] or result['last_name']:
                        if not best_result['first_name'] and result['first_name']:
                            best_result['first_name'] = result['first_name']
                        if not best_result['last_name'] and result['last_name']:
                            best_result['last_name'] = result['last_name']
                except Exception as e:
                    print(f"Error with {method_name} PSM {psm}: {e}")
                    continue

            # If we found both names, no need to try more methods
            if best_result['first_name'] and best_result['last_name']:
                break

        debug_text = "\n".join(all_texts)
        print(f"\nFinal result - First: {best_result['first_name']}, Last: {best_result['last_name']}")

        return {
            'first_name': best_result['first_name'],
            'last_name': best_result['last_name'],
            'debug_text': debug_text
        }

    except Exception as e:
        error_msg = f"Error extracting student info: {e}"
        print(error_msg)
        traceback.print_exc()
        return {'first_name': None, 'last_name': None, 'debug_text': error_msg}


def parse_name_from_text(text):
    """Parse first and last name from OCR text"""
    lines = text.strip().split('\n')
    first_name = None
    last_name = None

    print(f"\nParsing text ({len(lines)} lines):")

    # First pass: look for explicit patterns with colons
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        print(f"  Line {i}: '{line}'")

        # Look for "Name:" label (with colon) - NOT surname
        if re.search(r'\bname\s*:', line, re.IGNORECASE) and not re.search(r'surname|last', line, re.IGNORECASE):
            print(f"    → Found 'Name:' label (with colon)")
            # Try to extract from same line (e.g., "Name: Gaspar" or "Name:Gaspar")
            match = re.search(r'\bname\s*:\s*([A-Za-z]{2,})', line, re.IGNORECASE)
            if match:
                first_name = match.group(1).strip()
                print(f"    → ✓ Extracted first name from same line: '{first_name}'")
            # Otherwise check next line
            elif i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                print(f"    → Checking next line for first name: '{next_line}'")
                # Extract alphabetic words
                words = re.findall(r'[A-Za-z]{2,}', next_line)
                if words:
                    first_name = words[0]
                    print(f"    → ✓ Extracted first name from next line: '{first_name}'")

        # Look for "Surname:" label (with colon)
        if re.search(r'\bsurname\s*:|\blast\s*name\s*:', line, re.IGNORECASE):
            print(f"    → Found 'Surname:' or 'Last name:' label (with colon)")
            # Try to extract from same line
            match = re.search(r'\b(?:surname|last\s*name)\s*:\s*([A-Za-z]{2,})', line, re.IGNORECASE)
            if match:
                last_name = match.group(1).strip()
                print(f"    → ✓ Extracted last name from same line: '{last_name}'")
            # Otherwise check next line
            elif i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                print(f"    → Checking next line for last name: '{next_line}'")
                # Extract alphabetic words
                words = re.findall(r'[A-Za-z]{2,}', next_line)
                if words:
                    last_name = words[0]
                    print(f"    → ✓ Extracted last name from next line: '{last_name}'")

    # Second pass: if we still don't have first_name, look for standalone "Name" without colon
    if not first_name:
        print("\n  Second pass: looking for standalone 'Name' without colon...")
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Look for just "Name" word (case insensitive, without surname)
            if re.search(r'^name$', line, re.IGNORECASE) and not re.search(r'surname', line, re.IGNORECASE):
                if i + 1 < len(lines):
                    print(f"    → Found standalone 'Name' at line {i}")
                    next_line = lines[i + 1].strip()
                    print(f"    → Checking next line: '{next_line}'")
                    words = re.findall(r'[A-Za-z]{2,}', next_line)
                    if words:
                        first_name = words[0]
                        print(f"    → ✓ Extracted first name: '{first_name}'")
                        break

    # Third pass: if still no first_name, try more aggressive matching
    if not first_name:
        print("\n  Third pass: aggressive search for any 'name' pattern...")
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Any line containing "name" but not "surname" or "last"
            if re.search(r'name', line, re.IGNORECASE) and not re.search(r'surname|last', line, re.IGNORECASE):
                print(f"    → Found line with 'name': '{line}'")
                # Try to extract any alphabetic word after "name"
                match = re.search(r'name\s*:?\s*([A-Za-z]{2,})', line, re.IGNORECASE)
                if match and match.group(1).lower() != 'name':
                    first_name = match.group(1).strip()
                    print(f"    → ✓ Extracted first name: '{first_name}'")
                    break
                # Check next line
                elif i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    words = re.findall(r'[A-Za-z]{2,}', next_line)
                    if words and words[0].lower() not in ['name', 'surname', 'last']:
                        first_name = words[0]
                        print(f"    → ✓ Extracted first name from next line: '{first_name}'")
                        break

    print(f"\n  ✓ Final parse result: first_name='{first_name}', last_name='{last_name}'")
    return {'first_name': first_name, 'last_name': last_name}


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

        # Threshold the image
        _, img_threshold = cv2.threshold(answer_sheet, 150, 255, cv2.THRESH_BINARY_INV)

        # Detect answers
        answers = detect_answers(img_threshold, num_questions, num_options)

        # Extract student name information using OCR
        student_info = extract_student_info(img_gray)

        return {
            'success': True,
            'answers': answers,
            'student_info': student_info,
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
