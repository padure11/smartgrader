# SmartGrader - Question Import Guide

This directory contains sample files demonstrating how to import questions into SmartGrader.

## Supported Formats

### CSV Format

CSV files should follow this structure:

```csv
Question,Option A,Option B,Option C,Option D,Option E,Correct Answer
"Your question text",option1,option2,option3,option4,option5,index
```

**Important Notes:**
- First row is the header (will be skipped)
- Last column should be the index of the correct answer (0-based)
- Use quotes around text containing commas
- You can use 3-5 options per question

**Example:**
```csv
Question,Option A,Option B,Option C,Option D,Option E,Correct Answer
"What is the capital of France?",London,Paris,Berlin,Madrid,Rome,1
"What is 2 + 2?",3,4,5,6,7,1
```

### JSON Format

JSON files can use either of these formats:

**Format 1: Array of questions**
```json
[
  {
    "question": "What is the capital of France?",
    "options": ["London", "Paris", "Berlin", "Madrid", "Rome"],
    "correct_answer": 1
  }
]
```

**Format 2: Object with questions array**
```json
{
  "questions": [
    {
      "question": "What is the capital of France?",
      "options": ["London", "Paris", "Berlin", "Madrid", "Rome"],
      "correct_answer": 1
    }
  ]
}
```

**Format 3: Extended object format (with metadata)**
```json
{
  "title": "Test Matematică — 10 întrebări",
  "num_questions": 10,
  "num_answers": 4,
  "questions": [
    {
      "id": 1,
      "text": "Care este rezultatul expresiei: 3 × (4 + 2) − 5?",
      "correct_answer": "1",
      "options": ["11", "13", "17", "7"],
      "points": 5
    }
  ]
}
```

**Alternative field names (also supported):**
- `question`, `text`, or `questionText` for the question
- `options`, `answers`, or `choices` for the answer options
- `correct_answer` or `correctAnswer` for the correct answer index (supports both string "1" and number 1)

## Randomization Feature

After importing questions, you can use the randomization feature to create multiple test variants:

### How it Works

1. **Upload your question pool** - Import a CSV or JSON file with all your questions (e.g., 60 questions)

2. **Enable randomization** - Check the "Generate Multiple Test Variants" checkbox

3. **Configure settings:**
   - **Number of Variants**: How many different test versions to create (e.g., 6)
   - **Questions per Variant**: How many questions each test should have (e.g., 10)

4. **Generate** - Click "Save Test" to create all variants

### Example Use Case

You want to create 6 different versions of a 10-question test from a pool of 60 questions:

1. Upload `sample_questions.csv` (60 questions)
2. Enable randomization
3. Set "Number of Variants" to 6
4. Set "Questions per Variant" to 10
5. Save

Result: 6 tests will be created, each with 10 randomly selected questions from your pool.

### Benefits

- **Prevents cheating** - Each student gets a different set of questions
- **Fair testing** - All variants draw from the same question pool
- **Easy management** - Generate multiple variants with one click
- **PDF Generation** - Optionally generate PDFs for all variants at once

## AI Generated Subject (Coming Soon)

The "AI Generated Subject" button is a placeholder for future functionality that will allow you to:
- Generate questions automatically based on a topic
- Create diverse question pools without manual entry
- Customize difficulty levels and question types

This feature is currently under development.

## Sample Files

- `sample_questions.csv` - Example CSV file with 10 sample questions (English)
- `sample_questions.json` - Example JSON file with the same 10 questions (simple format)
- `sample_romanian_math.json` - Example Romanian mathematics test (extended format with metadata)

Feel free to use these as templates for your own question imports! All formats are fully supported.
