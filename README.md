# 📝 SmartGrader

**Automated Multiple Choice Test Grading System with OMR & OCR**

SmartGrader is a comprehensive web application for educators to create, distribute, and automatically grade multiple-choice tests using Optical Mark Recognition (OMR) and Optical Character Recognition (OCR) technology.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.1-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

### 🎓 For Teachers
- **Test Generator** - Create multiple-choice tests with customizable questions and options
- **PDF Export** - Generate printable test sheets with OMR bubble sheets
- **Bulk Upload** - Upload and process multiple scanned answer sheets at once
- **Automatic Grading** - OMR technology reads filled bubbles and grades instantly
- **Name Recognition** - OCR extracts student names from answer sheets
- **Student Management** - Share enrollment codes with students to link results
- **Analytics & Export** - View statistics, rankings, and export results to CSV
- **Test Duplication** - Clone existing tests for reuse

### 👨‍🎓 For Students
- **Easy Enrollment** - Join tests using simple 8-character codes
- **Dashboard** - View all enrolled tests and their statuses
- **Detailed Results** - See scores, grades, and question-by-question review
- **Answer Analysis** - Compare your answers with correct answers

### 🔧 Technical Features
- **Role-Based Access** - Separate interfaces for teachers and students
- **Automatic Student Matching** - Links graded submissions to enrolled students by name
- **Dark Theme UI** - Modern, professional interface
- **Responsive Design** - Works on desktop and mobile devices
- **SQLite/PostgreSQL** - Flexible database options
- **Image Processing** - Advanced OMR and OCR capabilities

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment tool (venv)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd smartgrader
   ```

2. **Create and activate virtual environment**

   **Linux/Mac:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

   **Windows (Command Prompt):**
   ```bash
   python -m venv venv
   venv\Scripts\activate.bat
   ```

   **Windows (PowerShell):**
   ```bash
   python -m venv venv
   venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the database**
   ```bash
   cd smartgrader_app
   python manage.py migrate
   ```

   Or use the automated setup:
   ```bash
   bash utils/run_migrations.sh  # Linux/Mac
   ```

5. **Run the development server**
   ```bash
   python manage.py runserver
   ```

6. **Access the application**

   Open your browser and navigate to: `http://localhost:8000`

---

## 📖 Usage Guide

### For Teachers

1. **Register an Account**
   - Go to the registration page
   - Select "Teacher" role
   - Provide your name, email, and password

2. **Create a Test**
   - Navigate to "Create Test" in the menu
   - Enter test details (title, description)
   - Add questions and options
   - Mark the correct answers
   - Save the test

3. **Generate PDF**
   - Click "Generate PDF" on the test detail page
   - Print the PDF with answer sheets

4. **Share Enrollment Code**
   - Copy the 8-character enrollment code from the test page
   - Share it with your students

5. **Upload Graded Sheets**
   - Students fill out and submit answer sheets
   - Scan the completed answer sheets
   - Upload images (supports bulk upload)
   - System automatically grades and matches to students

6. **View Results**
   - See all submissions with scores and grades
   - View detailed analytics
   - Export results to CSV

### For Students

1. **Register an Account**
   - Go to the registration page
   - Select "Student" role
   - Provide your name, email, and password

2. **Enroll in Test**
   - Navigate to "My Tests" dashboard
   - Enter the enrollment code from your teacher
   - Click "Enroll"

3. **Take the Test**
   - Obtain printed answer sheet from teacher
   - Fill in your name
   - Mark your answers with dark pencil/pen
   - Submit to teacher

4. **View Results**
   - After teacher uploads graded sheets
   - Results appear automatically in your dashboard
   - Click "View Detailed Results" to see question-by-question analysis

---

## 🏗️ Project Structure

```
smartgrader/
├── smartgrader_app/           # Main Django project
│   ├── accounts/              # Main app (models, views, templates)
│   │   ├── migrations/        # Database migrations
│   │   ├── templates/         # HTML templates
│   │   ├── static/           # CSS, JavaScript, images
│   │   ├── models.py         # Database models
│   │   ├── views.py          # View logic
│   │   ├── urls.py           # URL routing
│   │   └── omr_processor.py  # OMR/OCR logic
│   ├── smartgrader_app/      # Project settings
│   │   ├── settings.py       # Django settings
│   │   └── urls.py           # Root URL config
│   ├── manage.py             # Django management script
│   └── db.sqlite3           # Database (auto-generated)
│
├── pdf_generator/            # PDF generation module
│   └── pdf_generator.py     # Test sheet PDF creator
│
├── utils/                    # Utility scripts
│   ├── README.md            # Utils documentation
│   ├── match_students.py    # Student matching tool
│   ├── fix_user_role.py    # Role management
│   └── ...                  # Migration & diagnostic tools
│
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

---

## 🗄️ Database Models

### CustomUser
- Email-based authentication
- First name and last name
- Extends Django's AbstractUser

### Profile
- Links to CustomUser
- Role (teacher/student)
- Profile image (optional)

### Test
- Title, description
- Questions (JSON field)
- Number of questions/options
- Enrollment code (8-character unique)
- Created by (teacher)

### TestEnrollment
- Links student to test
- Enrollment timestamp
- Unique constraint on (student, test)

### Submission
- Links to test
- Student user (auto-matched)
- First name, last name (from OCR)
- Answers (JSON array)
- Score, percentage, grade
- Processed flag
- Submitted timestamp

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the `smartgrader_app` directory:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True

# Database (SQLite - default, no config needed)
# Or PostgreSQL:
# DB_NAME=your_db_name
# DB_USER=your_db_user
# DB_PASSWORD=your_password
# DB_HOST=localhost
# DB_PORT=5432
```

### Generate Secret Key

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### Database Options

**SQLite (Default - Recommended for Development)**
- No configuration needed
- Database file: `smartgrader_app/db.sqlite3`
- Automatically created on first migration

**PostgreSQL (Production)**
1. Install PostgreSQL
2. Create database and user
3. Update `.env` with database credentials
4. Update `settings.py` DATABASES configuration

---

## 🛠️ Utility Scripts

The `utils/` folder contains helpful management scripts. See [`utils/README.md`](utils/README.md) for detailed documentation.

**Common Commands:**

```bash
# Fix user roles
python utils/fix_user_role.py

# Match unlinked submissions to students
python utils/match_students.py

# Diagnose migration issues
python utils/diagnose.py

# Check user roles
python utils/check_user_role.py
```

---

## 🎨 Features in Detail

### Optical Mark Recognition (OMR)
- Detects filled bubbles on answer sheets
- Supports multiple choice formats (A-E)
- Handles various scanning qualities
- Robust against slight rotations and distortions

### Optical Character Recognition (OCR)
- Extracts student names from handwritten text
- Uses Tesseract OCR engine
- Preprocessing for better accuracy

### Automatic Student Matching
- Matches graded submissions to enrolled students by name
- Case-insensitive comparison
- Handles name variations (swapped first/last name)
- Manual override available through UI

### Grading System
- A: 90-100%
- B: 80-89%
- C: 70-79%
- D: 60-69%
- F: Below 60%

---

## 🔐 Security Features

- CSRF protection on all forms
- Role-based access control
- Secure password hashing
- SQL injection prevention (Django ORM)
- XSS protection (template escaping)
- Session management

---

## 🧪 Testing

Run Django tests:
```bash
cd smartgrader_app
python manage.py test accounts
```

---

## 📊 Analytics & Reporting

Teachers can access:
- **Submission statistics** - Total submissions, average score, pass rate
- **Rankings** - Students ranked by performance
- **CSV Export** - Download all results with detailed breakdown
- **Question analysis** - See which questions were most difficult

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 🐛 Troubleshooting

### Migration Issues
```bash
python utils/diagnose.py           # See what's wrong
python utils/fix_migrations_windows.py  # Fix (Windows)
```

### Students Can't See Results
```bash
python utils/match_students.py     # Match submissions to students
```

### Role Assignment Issues
```bash
python utils/fix_user_role.py      # Change user roles
```

### Common Issues

**"No such table: django_session"**
```bash
python manage.py migrate --run-syncdb
```

**"Duplicate column" errors**
```bash
python utils/fix_migrations_windows.py
```

**User registered with wrong role**
```bash
python utils/fix_user_role.py
```

See [`utils/README.md`](utils/README.md) for more troubleshooting tools.

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 👥 Authors

Developed with ❤️ for educators and students.

---

## 🙏 Acknowledgments

- Django framework
- Tesseract OCR
- OpenCV for image processing
- All contributors and testers

---

## 📧 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check the [utils documentation](utils/README.md)
- Review troubleshooting section above

---

## 🗺️ Roadmap

Future enhancements:
- [ ] Mobile app for students
- [ ] Advanced analytics dashboard
- [ ] Multiple question types (true/false, matching)
- [ ] Test scheduling and time limits
- [ ] Grade curves and weighted scoring
- [ ] Email notifications for results
- [ ] Multi-language support
- [ ] Improved OCR accuracy with ML models

---

**Made with 💻 and ☕**
