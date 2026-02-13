"""Excel/CSV file parsing utilities."""
import pandas as pd
from io import BytesIO


def parse_excel_file(file_content, filename):
    """
    Parse Excel or CSV file and return a list of dicts.
    Handles .csv, .xlsx, .xls files.
    """
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(file_content), encoding='utf-8')
        elif filename.endswith('.xlsx'):
            df = pd.read_excel(BytesIO(file_content), engine='openpyxl')
        elif filename.endswith('.xls'):
            df = pd.read_excel(BytesIO(file_content), engine='xlrd')
        else:
            raise ValueError(f"Unsupported file format: {filename}")
        
        df = df.dropna(how='all')
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        return df.to_dict('records')
    except Exception as e:
        raise ValueError(f"Error parsing file: {str(e)}")


def parse_students_file(file_content, filename, required_columns=None):
    """Parse student import file. Expected columns: roll_number, name (or roll, name)."""
    records = parse_excel_file(file_content, filename)
    if not records:
        raise ValueError("File is empty or has no valid data")
    
    normalized = []
    for r in records:
        row = {k.strip().lower(): str(v).strip() if pd.notna(v) else '' for k, v in r.items()}
        roll = row.get('roll_number') or row.get('roll_no') or row.get('roll') or row.get('rollnumber', '')
        name = row.get('name') or row.get('student_name') or row.get('studentname', '')
        section = (row.get('section') or row.get('section_name') or row.get('sectionname', '')).strip() or None
        if roll and name:
            rec = {'roll_number': roll, 'name': name}
            if section:
                rec['section'] = section
            normalized.append(rec)
    
    if not normalized:
        raise ValueError("No valid student records found. Ensure columns include roll number and name.")
    return normalized


def parse_subjects_file(file_content, filename):
    """Parse subject import file. Expected: name, code (or subject_name, subject_code)."""
    records = parse_excel_file(file_content, filename)
    normalized = []
    for r in records:
        row = {k.strip().lower(): str(v).strip() if pd.notna(v) else '' for k, v in r.items()}
        name = row.get('name') or row.get('subject_name') or row.get('subjectname', '')
        code = row.get('code') or row.get('subject_code') or row.get('subjectcode', '')
        if name and code:
            normalized.append({'name': name, 'code': code.upper()})
    return normalized


def parse_halls_file(file_content, filename):
    """Parse exam hall import file. Expected: hall_number, capacity, building_name, floor."""
    records = parse_excel_file(file_content, filename)
    normalized = []
    for r in records:
        row = {k.strip().lower(): v for k, v in r.items()}
        hall_num = str(row.get('hall_number') or row.get('hall') or row.get('hall_no', '')).strip()
        cap = row.get('capacity', 45)
        try:
            cap = int(cap) if pd.notna(cap) else 45
        except (ValueError, TypeError):
            cap = 45
        building = str(row.get('building_name') or row.get('building') or '').strip()
        floor = str(row.get('floor') or '').strip()
        if hall_num:
            normalized.append({
                'hall_number': hall_num,
                'capacity': cap,
                'building_name': building or 'Main Building',
                'floor': floor or 'Ground'
            })
    return normalized


def parse_timetable_subjects_file(file_content, filename):
    """
    Parse exam timetable subject list (department_code, subject_code).
    Do NOT drop duplicates - each row is one subject per department.
    Expected columns: department_code, subject_code (or departmentcode, subjectcode).
    """
    records = parse_excel_file(file_content, filename)
    normalized = []
    for r in records:
        row = {k.strip().lower(): str(v).strip() if pd.notna(v) else '' for k, v in r.items()}
        dept_code = (row.get('department_code') or row.get('dept_code') or row.get('departmentcode') or '').strip().upper()
        subj_code = (row.get('subject_code') or row.get('subjectcode') or '').strip().upper()
        if dept_code and subj_code:
            normalized.append({'department_code': dept_code, 'subject_code': subj_code})
    return normalized


def parse_schedule_file(file_content, filename):
    """
    Parse exam schedule file.
    Expected columns: subject_code, department_code, exam_date, start_time, end_time
    """
    records = parse_excel_file(file_content, filename)
    normalized = []
    for r in records:
        row = {k.strip().lower(): v for k, v in r.items()}
        subj_code = str(row.get('subject_code') or row.get('subjectcode') or '').strip().upper()
        dept_code = str(row.get('department_code') or row.get('dept_code') or row.get('departmentcode') or '').strip().upper()
        date_val = row.get('exam_date') or row.get('date') or row.get('examdate')
        start_val = row.get('start_time') or row.get('starttime') or row.get('start')
        end_val = row.get('end_time') or row.get('endtime') or row.get('end')
        
        if not all([subj_code, dept_code, date_val]):
            continue
            
        try:
            if isinstance(date_val, str):
                date_obj = pd.to_datetime(date_val).date()
            else:
                date_obj = pd.Timestamp(date_val).date()
            
            def parse_time(t):
                if pd.isna(t):
                    return None
                if isinstance(t, str) and ':' in t:
                    parts = t.split(':')
                    from datetime import time
                    return time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
                ts = pd.Timestamp(t)
                return ts.time()
            
            start_time = parse_time(start_val)
            end_time = parse_time(end_val)
            if start_time and end_time:
                normalized.append({
                    'subject_code': subj_code,
                    'department_code': dept_code,
                    'exam_date': date_obj,
                    'start_time': start_time,
                    'end_time': end_time
                })
        except Exception:
            continue
    return normalized
