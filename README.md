# Exam Seat Allocation System

A user-friendly web-based system for managing exam seat allocation at educational institutions. Built with Flask, Bootstrap, and SQLite.

## Features

- **Authentication**: Secure login with User ID and password
- **Admin Dashboard**: Overview of departments, students, halls, subjects, and upcoming exams
- **Department Management**: Add departments with name, code, and enrolled students count
- **Student Management**: Import from Excel (.csv, .xlsx, .xls) or add manually; filter by department and academic year
- **Subject Management**: Add subjects individually or import from Excel
- **Exam Hall Management**: Configure halls with capacity (default 45), building, and floor
- **Exam Schedule**: Create schedules manually or import from Excel
- **Seat Allocation**: View allocations and generate PDFs (overall sheet, classroom sheets, attendance sheets)

## Installation

1. Create a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate   # Windows
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python run.py
   ```

4. Open http://localhost:5000 in your browser.

5. **Default login**: User ID: `ashwin`, Password: `ashwin0211`

## Excel Import Formats

### Students
Columns: `roll_number` (or roll, roll_no), `name` (or student_name)

### Subjects
Columns: `name` (or subject_name), `code` (or subject_code)

### Exam Halls
Columns: `hall_number`, `capacity`, `building_name`, `floor`

### Exam Schedule
Columns: `subject_code`, `department_code`, `exam_date`, `start_time`, `end_time`

## PDF Generation

When you generate allocation PDFs for an exam date, you receive a ZIP file containing:

1. **Overall allocation sheet** – Notice board summary with hall-wise department and roll ranges
2. **Classroom seating PDF** – Per-hall seating with bench and position (students from same department not adjacent)
3. **Attendance sheet** – Per-hall list with roll number, name, and signature column

## Tech Stack

- **Backend**: Python, Flask, SQLAlchemy, Flask-Login, Flask-WTF
- **Database**: SQLite (easily switchable to PostgreSQL/MySQL)
- **Frontend**: Bootstrap 5, Bootstrap Icons
- **PDF**: ReportLab
- **Excel**: pandas, openpyxl, xlrd

## Project Structure

```
├── app.py              # Main application
├── config.py           # Configuration
├── models.py           # Database models
├── run.py              # Entry point
├── requirements.txt
├── routes/             # Blueprints (auth, dashboard, departments, etc.)
├── templates/          # HTML templates
├── utils/              # Excel parser, PDF generator, allocation engine
└── uploads/            # Temporary file uploads
```
