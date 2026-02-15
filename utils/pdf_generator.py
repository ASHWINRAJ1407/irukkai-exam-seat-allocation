"""PDF generation for seat allocation documents."""
from datetime import datetime, date
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import xml.sax.saxutils as saxutils


def create_overall_allocation_pdf(allocations_by_hall, exam_name, exam_date):
    """Overall seating allocation - single compact table: Hall | Department | Subject Code | No. Students | Roll Range."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=8
    )
    sub_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=12
    )

    story = []
    story.append(Paragraph("EXAM SEATING ALLOCATION", title_style))
    story.append(Paragraph(f"<b>Exam:</b> {exam_name} | <b>Date:</b> {exam_date}", sub_style))
    story.append(Spacer(1, 0.2*inch))

    # Table: Hall Number | Building Name | Floor Name | Department | No. Students | Roll Number Range
    data = [['Hall Number', 'Building Name', 'Floor Name', 'Department', 'No. Students', 'Roll Number Range']]
    for hall_info in allocations_by_hall:
        hall_num = hall_info['hall_number']
        building = hall_info.get('building_name', '') or ''
        floor = hall_info.get('floor', '') or ''
        for da in hall_info.get('allocations', []):
            rolls = da.get('roll_range', '')
            if not rolls and da.get('roll_numbers'):
                rn = da['roll_numbers']
                rolls = f"{min(rn)} - {max(rn)}" if len(rn) > 1 else str(rn[0])
            data.append([
                hall_num,
                building,
                floor,
                da.get('department_code', da.get('dept_name', '')),
                str(da.get('count', len(da.get('roll_numbers', [])))),
                rolls
            ])

    col_widths = [0.8*inch, 1.2*inch, 0.9*inch, 1*inch, 0.9*inch, 1.8*inch]
    t = Table(data, colWidths=col_widths)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]

    # Merge repeated hall number, building, and floor cells for consecutive rows of same hall
    # Row 0 is header; start scanning from row 1.
    if len(data) > 2:
        current_hall = data[1][0]
        start_row = 1
        for r in range(2, len(data)):
            hall_val = data[r][0]
            if hall_val != current_hall:
                end_row = r - 1
                if end_row > start_row:
                    style_cmds.append(('SPAN', (0, start_row), (0, end_row)))
                    style_cmds.append(('VALIGN', (0, start_row), (0, end_row), 'MIDDLE'))
                    style_cmds.append(('SPAN', (1, start_row), (1, end_row)))
                    style_cmds.append(('VALIGN', (1, start_row), (1, end_row), 'MIDDLE'))
                    style_cmds.append(('SPAN', (2, start_row), (2, end_row)))
                    style_cmds.append(('VALIGN', (2, start_row), (2, end_row), 'MIDDLE'))
                current_hall = hall_val
                start_row = r
        # Final block
        end_row = len(data) - 1
        if end_row > start_row:
            style_cmds.append(('SPAN', (0, start_row), (0, end_row)))
            style_cmds.append(('VALIGN', (0, start_row), (0, end_row), 'MIDDLE'))
            style_cmds.append(('SPAN', (1, start_row), (1, end_row)))
            style_cmds.append(('VALIGN', (1, start_row), (1, end_row), 'MIDDLE'))
            style_cmds.append(('SPAN', (2, start_row), (2, end_row)))
            style_cmds.append(('VALIGN', (2, start_row), (2, end_row), 'MIDDLE'))

    t.setStyle(TableStyle(style_cmds))
    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer


def create_classroom_allocation_pdf(hall_info, exam_name, exam_date):
    """Single classroom seating allocation.

    - For traditional 45-capacity halls, we keep the compact Bench/Pos1/Pos2/Pos3 layout.
    - For other capacities, we generate a Seat No → Roll Number list (seat numbers derived
      from bench/position and trimmed to the configured hall capacity).
    - Below the seating chart:
      - Include a "Post-Allocation Data Aggregation" section showing subject code counts.
      - Format: "Room [No] - [Code_A]: [Count], [Code_B]: [Count]"
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.4*inch, bottomMargin=0.4*inch)
    styles = getSampleStyleSheet()

    story = []
    story.append(Paragraph(
        f"<b>HALL {hall_info['hall_number']}</b> | {hall_info.get('building_name', '')} | Floor: {hall_info.get('floor', '')}",
        styles['Heading2']
    ))
    story.append(Paragraph(f"Exam: {exam_name} | Date: {exam_date}", styles['Normal']))
    story.append(Spacer(1, 0.15*inch))

    seats = hall_info.get('seats', [])
    if not seats:
        story.append(Paragraph("No allocation data.", styles['Normal']))
        doc.build(story)
        buffer.seek(0)
        return buffer
    capacity = hall_info.get("capacity") or 45

    if capacity == 45:
        # Preserve existing Bench/Position table for 45-seat halls.
        data = [['Bench', 'Pos 1', 'Pos 2', 'Pos 3']]
        seat_map = {}
        for bench, pos, roll in seats:
            if bench not in seat_map:
                seat_map[bench] = {1: '', 2: '', 3: ''}
            seat_map[bench][pos] = str(roll)

        for b in sorted(seat_map.keys()):
            row = seat_map[b]
            data.append([str(b), row.get(1, ''), row.get(2, ''), row.get(3, '')])

        t = Table(data, colWidths=[0.6*inch, 1.4*inch, 1.4*inch, 1.4*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2980b9')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(t)
    else:
        # Visual seat grid for non-45 halls.
        # Seat number is shown inside the \"seat\" cell, with the roll number below.
        # Seats are arranged in rows of 6; the 7th seat appears under the 1st seat.
        seats_sorted = sorted(seats, key=lambda x: (x[0], x[1]))
        per_bench = 3
        per_row = 6

        # Build list of (seat_no, roll) trimmed to capacity
        seat_entries = []
        for bench, pos, roll in seats_sorted:
            seat_no = (bench - 1) * per_bench + pos
            if seat_no > capacity:
                continue
            seat_entries.append((seat_no, str(roll)))

        # Create rows of up to 6 seats each
        grid_rows = []
        current_row = []
        for seat_no, roll in seat_entries:
            # Display text: seat number on first line, roll below
            cell_text = f"<b>{seat_no}</b><br/><font size='8'>{roll}</font>"
            current_row.append(Paragraph(cell_text, styles['Normal']))
            if len(current_row) == per_row:
                grid_rows.append(current_row)
                current_row = []
        if current_row:
            # Pad remaining cells so the grid looks uniform
            while len(current_row) < per_row:
                current_row.append('')
            grid_rows.append(current_row)

        t = Table(grid_rows, colWidths=[0.9 * inch] * per_row)
        t.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            # Seat \"image\" styling
            ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ]))
        story.append(t)
    
    # Post-Allocation Data Aggregation: Subject Code Summary for Invigilators
    # Group-by subject_code and count students for attendance verification
    story.append(Spacer(1, 0.25*inch))
    story.append(Paragraph("<b>Invigilator Attendance Summary (Group-by Subject Code)</b>", styles['Heading3']))
    
    subject_code_summary = hall_info.get('subject_code_summary', {})
    if subject_code_summary:
        # Build summary string: "Room [No] - [Code_A]: [Count], [Code_B]: [Count]"
        summary_parts = []
        for code in sorted(subject_code_summary.keys()):
            count = subject_code_summary[code]
            summary_parts.append(f"{code}: {count}")
        summary_str = ", ".join(summary_parts)
        room_no = hall_info.get('hall_number', 'N/A')
        summary_text = f"<b>Room {room_no}</b> - {summary_str}"
        story.append(Paragraph(summary_text, styles['Normal']))
    else:
        story.append(Paragraph("No subject code breakdown available.", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


def create_attendance_sheet_pdf(hall_info, exam_name, exam_date):
    """Attendance sheet with separate pages per department within the same hall."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()

    story = []
    hall_num = hall_info['hall_number']
    students = hall_info.get('students', [])
    allocations = hall_info.get('allocations', [])

    if not students and not allocations:
        story.append(Paragraph(f"<b>ATTENDANCE SHEET - HALL {hall_num}</b>", styles['Heading2']))
        story.append(Paragraph("No students.", styles['Normal']))
        doc.build(story)
        buffer.seek(0)
        return buffer

    # Build students grouped by department from allocations (dept_code + subject_code as key)
    # allocations have department_code, roll_numbers; we need roll -> name from students
    roll_to_name = {str(s.get('roll_number', '')): s.get('name', '') for s in students}
    dept_rolls = {}  # (dept_code, subject_code) -> [roll_numbers]
    for al in allocations:
        key = (al.get('department_code', ''), al.get('subject_code', ''))
        rolls = al.get('roll_numbers', [])
        if key not in dept_rolls:
            dept_rolls[key] = []
        dept_rolls[key].extend(rolls)

    # If no allocation breakdown, treat all students as one "department" page
    if not dept_rolls and students:
        story.append(Paragraph(
            f"<b>ATTENDANCE SHEET - HALL {hall_num}</b>",
            styles['Heading2']
        ))
        story.append(Paragraph(f"Exam: {exam_name} | Date: {exam_date}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        data = [['S.No', 'Roll Number', 'Name', 'Signature']]
        for i, entry in enumerate(students, 1):
            data.append([
                str(i),
                str(entry.get('roll_number', '')),
                str(entry.get('name', '')),
                ''
            ])
        t = Table(data, colWidths=[0.5*inch, 1.2*inch, 2.5*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(t)
        doc.build(story)
        buffer.seek(0)
        return buffer

    # Separate page per department (dept_code + subject for label)
    for (dept_code, subj_code), rolls in dept_rolls.items():
        if not rolls:
            continue
        story.append(Paragraph(
            f"<b>HALL {hall_num} – Department: {dept_code} | Subject: {subj_code}</b>",
            styles['Heading2']
        ))
        story.append(Paragraph(f"Exam: {exam_name} | Date: {exam_date}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        data = [['S.No', 'Roll Number', 'Name', 'Signature']]
        for i, roll in enumerate(sorted(rolls, key=lambda x: (len(str(x)), str(x))), 1):
            data.append([
                str(i),
                str(roll),
                roll_to_name.get(str(roll), ''),
                ''
            ])
        t = Table(data, colWidths=[0.5*inch, 1.2*inch, 2.5*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(t)
        story.append(PageBreak())

    if story and isinstance(story[-1], PageBreak):
        story.pop()  # remove trailing page break
    doc.build(story)
    buffer.seek(0)
    return buffer


def _fmt_date_dd_mm_yyyy(d):
    """Format date as DD.MM.YYYY for master timetable."""
    if isinstance(d, date):
        return d.strftime('%d.%m.%Y')
    return str(d)


def create_master_timetable_pdf(schedule_list, exam_name, academic_year, exam_time_str, subject_name_map=None):
    """
    schedule_list: list of (date, dept_code, subject_code) or (date, dept_code, subject_code, subject_name).
    exam_name: e.g. UG - IV YEAR - MODEL EXAMINATION.
    academic_year: e.g. 2024-2025 (ODD SEMESTER).
    exam_time_str: e.g. "13:15 - 16:15" or "01:15 PM to 04:15 PM".
    subject_name_map: { subject_code: subject_name } optional.
    Output: MASTER TIME TABLE style PDF (like sample).
    """
    subject_name_map = subject_name_map or {}
    # Build (dept, date) -> (code, name); normalize dates for sorting
    grid = {}  # (dept_code, date) -> (subject_code, subject_name)
    depts_order = []
    dates_order = []
    seen_depts = set()
    seen_dates_set = set()

    def _norm_d(d):
        if isinstance(d, date) and hasattr(d, 'year'):
            return d
        if isinstance(d, str):
            if len(d) == 10 and d[4] == '-' and d[7] == '-':
                try:
                    return date(int(d[:4]), int(d[5:7]), int(d[8:10]))
                except (ValueError, IndexError):
                    pass
            if '/' in d:
                parts = d.split('/')
                if len(parts) == 3:
                    return date(int(parts[2]), int(parts[1]), int(parts[0]))
        return d

    for item in schedule_list:
        if len(item) >= 4:
            d, dept, code, name = item[0], item[1], item[2], item[3]
        else:
            d, dept, code = item[0], item[1], item[2]
            name = subject_name_map.get(code, '')
        d = _norm_d(d)
        grid[(dept, d)] = (code, name)
        if dept not in seen_depts:
            seen_depts.add(dept)
            depts_order.append(dept)
        if d not in seen_dates_set:
            seen_dates_set.add(d)
            dates_order.append(d)
    dates_order.sort(key=lambda x: (x.isoformat() if hasattr(x, 'isoformat') else str(x)))
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.4*inch, bottomMargin=0.4*inch)
    styles = getSampleStyleSheet()

    def _escape(s):
        return saxutils.escape(str(s)) if s else ''

    title_style = ParagraphStyle('MasterTitle', parent=styles['Heading1'], fontSize=14, alignment=TA_CENTER, spaceAfter=4)
    sub_style = ParagraphStyle('MasterSub', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, spaceAfter=2)
    cell_style = ParagraphStyle(
        'MasterCell', parent=styles['Normal'],
        fontSize=6, alignment=TA_CENTER, leading=7,
        leftIndent=0, rightIndent=0, spaceBefore=1, spaceAfter=1,
    )
    header_style = ParagraphStyle(
        'MasterHeader', parent=styles['Normal'],
        fontSize=7, alignment=TA_CENTER, textColor=colors.whitesmoke,
    )
    story = []
    story.append(Paragraph("MASTER TIME TABLE", title_style))
    story.append(Paragraph(_escape(f"BATCH {academic_year}"), sub_style))
    story.append(Paragraph(_escape(exam_name), sub_style))
    story.append(Paragraph(_escape(f"EXAM TIME: AN - From {exam_time_str}"), sub_style))
    story.append(Spacer(1, 0.15*inch))

    col_widths = [0.95*inch] + [1.35*inch] * len(dates_order)
    header_row0 = [Paragraph(_escape('DEPT'), header_style)] + [Paragraph(_escape(_fmt_date_dd_mm_yyyy(d)), header_style) for d in dates_order]
    header_row1 = [Paragraph('', header_style)] + [Paragraph('AN', header_style) for _ in dates_order]
    data = [header_row0, header_row1]
    for dept in depts_order:
        row = [Paragraph(_escape(dept), cell_style)]
        for d in dates_order:
            val = grid.get((dept, d))
            if val:
                code, name = val
                part_code = _escape(code)
                part_name = _escape(name) if name else ''
                cell_text = f"{part_code}<br/>{part_name}" if part_name else part_code
                row.append(Paragraph(cell_text, cell_style))
            else:
                row.append(Paragraph('-', cell_style))
        data.append(row)

    t = Table(data, colWidths=col_widths, repeatRows=2)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 2), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer
