import json
import os
import logging

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .forms import *
from .models import *

#My additional imports
#import vonage
from django.conf import settings
from django.core.exceptions import ValidationError
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime
import requests
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus.flowables import Image
from twilio.rest import Client

logger = logging.getLogger(__name__)

def staff_home(request):
    staff = get_object_or_404(Staff, admin=request.user)
    total_students = Student.objects.filter(course=staff.course).count()
    total_leave = LeaveReportStaff.objects.filter(staff=staff).count()
    subjects = Subject.objects.filter(staff=staff)
    total_subject = subjects.count()
    attendance_list = Attendance.objects.filter(subject__in=subjects)
    total_attendance = attendance_list.count()
    attendance_list = []
    subject_list = []
    for subject in subjects:
        attendance_count = Attendance.objects.filter(subject=subject).count()
        subject_list.append(subject.name)
        attendance_list.append(attendance_count)
    context = {
        'page_title': 'Staff Panel - ' + str(staff.admin.last_name) + ' (' + str(staff.course) + ')',
        'total_students': total_students,
        'total_attendance': total_attendance,
        'total_leave': total_leave,
        'total_subject': total_subject,
        'subject_list': subject_list,
        'attendance_list': attendance_list
    }
    return render(request, 'staff_template/home_content.html', context)


def staff_take_attendance(request):
    staff = get_object_or_404(Staff, admin=request.user)
    subjects = Subject.objects.filter(staff_id=staff)
    sessions = Session.objects.all()
    context = {
        'subjects': subjects,
        'sessions': sessions,
        'page_title': 'Take Attendance'
    }

    return render(request, 'staff_template/staff_take_attendance.html', context)


@csrf_exempt
def get_students(request):
    subject_id = request.POST.get('subject')
    session_id = request.POST.get('session')
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        session = get_object_or_404(Session, id=session_id)
        students = Student.objects.filter(
            course_id=subject.course.id, session=session)
        student_data = []
        for student in students:
            data = {
                    "id": student.id,
                    "name": student.admin.last_name + " " + student.admin.first_name
                    }
            student_data.append(data)
        return JsonResponse(json.dumps(student_data), content_type='application/json', safe=False)
    except Exception as e:
        return e



@csrf_exempt
def save_attendance(request):
    student_data = request.POST.get('student_ids')
    date = request.POST.get('date')
    subject_id = request.POST.get('subject')
    session_id = request.POST.get('session')
    students = json.loads(student_data)
    try:
        session = get_object_or_404(Session, id=session_id)
        subject = get_object_or_404(Subject, id=subject_id)

        # Check if an attendance object already exists for the given date and session
        attendance, created = Attendance.objects.get_or_create(session=session, subject=subject, date=date)

        for student_dict in students:
            student = get_object_or_404(Student, id=student_dict.get('id'))

            # Check if an attendance report already exists for the student and the attendance object
            attendance_report, report_created = AttendanceReport.objects.get_or_create(student=student, attendance=attendance)

            # Update the status only if the attendance report was newly created
            if report_created:
                attendance_report.status = student_dict.get('status')
                attendance_report.save()

    except Exception as e:
        return None

    return HttpResponse("OK")


def staff_update_attendance(request):
    staff = get_object_or_404(Staff, admin=request.user)
    subjects = Subject.objects.filter(staff_id=staff)
    sessions = Session.objects.all()
    context = {
        'subjects': subjects,
        'sessions': sessions,
        'page_title': 'Update Attendance'
    }

    return render(request, 'staff_template/staff_update_attendance.html', context)


@csrf_exempt
def get_student_attendance(request):
    attendance_date_id = request.POST.get('attendance_date_id')
    try:
        date = get_object_or_404(Attendance, id=attendance_date_id)
        attendance_data = AttendanceReport.objects.filter(attendance=date)
        student_data = []
        for attendance in attendance_data:
            data = {"id": attendance.student.admin.id,
                    "name": attendance.student.admin.last_name + " " + attendance.student.admin.first_name,
                    "status": attendance.status}
            student_data.append(data)
        return JsonResponse(json.dumps(student_data), content_type='application/json', safe=False)
    except Exception as e:
        return e


@csrf_exempt
def update_attendance(request):
    student_data = request.POST.get('student_ids')
    date = request.POST.get('date')
    students = json.loads(student_data)
    try:
        attendance = get_object_or_404(Attendance, id=date)

        for student_dict in students:
            student = get_object_or_404(
                Student, admin_id=student_dict.get('id'))
            attendance_report = get_object_or_404(AttendanceReport, student=student, attendance=attendance)
            attendance_report.status = student_dict.get('status')
            attendance_report.save()
    except Exception as e:
        return None

    return HttpResponse("OK")


def staff_apply_leave(request):
    form = LeaveReportStaffForm(request.POST or None)
    staff = get_object_or_404(Staff, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportStaff.objects.filter(staff=staff),
        'page_title': 'Apply for Leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.staff = staff
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('staff_apply_leave'))
            except Exception:
                messages.error(request, "Could not apply!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "staff_template/staff_apply_leave.html", context)


def staff_feedback(request):
    form = FeedbackStaffForm(request.POST or None)
    staff = get_object_or_404(Staff, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackStaff.objects.filter(staff=staff),
        'page_title': 'Add Feedback'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.staff = staff
                obj.save()
                messages.success(request, "Feedback submitted for review")
                return redirect(reverse('staff_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "staff_template/staff_feedback.html", context)


def staff_view_profile(request):
    staff = get_object_or_404(Staff, admin=request.user)
    form = StaffEditForm(request.POST or None, request.FILES or None,instance=staff)
    context = {'form': form, 'page_title': 'View/Update Profile'}
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = staff.admin
                if password != None:
                    admin.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    admin.profile_pic = passport_url
                admin.first_name = first_name
                admin.last_name = last_name
                admin.address = address
                admin.gender = gender
                admin.save()
                staff.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('staff_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
                return render(request, "staff_template/staff_view_profile.html", context)
        except Exception as e:
            messages.error(
                request, "Error Occured While Updating Profile " + str(e))
            return render(request, "staff_template/staff_view_profile.html", context)

    return render(request, "staff_template/staff_view_profile.html", context)


@csrf_exempt
def staff_fcmtoken(request):
    token = request.POST.get('token')
    try:
        staff_user = get_object_or_404(CustomUser, id=request.user.id)
        staff_user.fcm_token = token
        staff_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def staff_view_notification(request):
    staff = get_object_or_404(Staff, admin=request.user)
    notifications = NotificationStaff.objects.filter(staff=staff)
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "staff_template/staff_view_notification.html", context)


def staff_add_result(request):
    staff = get_object_or_404(Staff, admin=request.user)
    subjects = Subject.objects.filter(staff=staff)
    sessions = Session.objects.all()
    context = {
        'page_title': 'Result Upload',
        'subjects': subjects,
        'sessions': sessions
    }
    if request.method == 'POST':
        try:
            student_id = request.POST.get('student_list')
            subject_id = request.POST.get('subject')
            test = request.POST.get('test')
            exam = request.POST.get('exam')
            student = get_object_or_404(Student, id=student_id)
            subject = get_object_or_404(Subject, id=subject_id)
            try:
                data = StudentResult.objects.get(
                    student=student, subject=subject)
                data.exam = exam
                data.test = test
                data.save()
                messages.success(request, "Scores Updated")
            except:
                result = StudentResult(student=student, subject=subject, test=test, exam=exam)
                result.save()
                messages.success(request, "Scores Saved")
        except Exception as e:
            messages.warning(request, "Error Occured While Processing Form")
    return render(request, "staff_template/staff_add_result.html", context)


def calculate_grade(total_score):
    """Calculate grade based on total score"""
    if total_score >= 80:
        return 'A'
    elif total_score >= 70:
        return 'B'
    elif total_score >= 60:
        return 'C'
    elif total_score >= 50:
        return 'D'
    else:
        return 'F'

# Additional
@csrf_exempt
def send_student_result(request):
    if request.method != 'POST':
        return JsonResponse({
            'status': False,
            'message': 'Method not allowed'
        })
    
    student_id = request.POST.get('student_id')
    if not student_id:
        return JsonResponse({
            'status': False,
            'message': 'Student ID is required'
        })

    try:
        # Get student and their latest result
        student = Student.objects.get(id=student_id)
        result = StudentResult.objects.filter(student=student).latest('created_at')
        
        # Calculate total and grade
        total_score = float(result.test) + float(result.exam)
        grade = calculate_grade(total_score)
        
        # Send SMS
        success = send_result_sms(
            student=student,
            subject=result.subject,
            test_score=result.test,
            exam_score=result.exam,
            total_score=total_score,
            grade=grade
        )
        
        if success:
            return JsonResponse({
                'status': True,
                'message': 'Result sent successfully'
            })
        else:
            return JsonResponse({
                'status': False,
                'message': 'Failed to send SMS'
            })

    except Student.DoesNotExist:
        return JsonResponse({
            'status': False,
            'message': 'Student not found'
        })
    except StudentResult.DoesNotExist:
        return JsonResponse({
            'status': False,
            'message': 'No results found for this student'
        })
    except Exception as e:
        return JsonResponse({
            'status': False,
            'message': str(e)
        })

@csrf_exempt
def fetch_student_result(request):
    try:
        subject_id = request.POST.get('subject')
        student_id = request.POST.get('student')
        student = get_object_or_404(Student, id=student_id)
        subject = get_object_or_404(Subject, id=subject_id)
        result = StudentResult.objects.get(student=student, subject=subject)
        result_data = {
            'exam': result.exam,
            'test': result.test
        }
        return HttpResponse(json.dumps(result_data))
    except Exception as e:
        return HttpResponse('False')

@csrf_exempt
def send_result_sms(request, student_id):
    staff = get_object_or_404(Staff, admin=request.user)
    if not staff.class_teacher:
        return JsonResponse({'status': False, 'message': 'Unauthorized'})

    student = get_object_or_404(Student, id=student_id)
    results = StudentResult.objects.filter(student=student)

    # Accept both JSON and form POST
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body.decode())
        except Exception:
            data = {}
    else:
        data = request.POST

    phone_number = data.get('phone_number', '').strip()
    # If no phone provided, use student's phone
    if not phone_number:
        phone_number = (student.phone_number or '').strip()

    # If still no phone, return error
    if not phone_number:
        return JsonResponse({'status': False, 'message': "No parent's phone number provided."})

    # If student has no phone and a new one is provided, save it
    if not student.phone_number and phone_number:
        student.phone_number = phone_number
        student.save()

    try:
        # Format message
        message = f"Result for {student.admin.get_full_name()}\n"
        for result in results:
            total_score = result.test + result.exam
            grade = calculate_grade(total_score)
            message += f"{result.subject.name}: Test({result.test}) + Exam({result.exam}) = {total_score} ({grade})\n"

        # Initialize Twilio client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        # Send SMS
        message = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )

        logger.info(f"SMS Response: {message.sid}")  # Log the response

        return JsonResponse({
            'status': True,
            'message': 'Result sent successfully'
        })

    except Exception as e:
        logger.error(f"Error sending SMS: {str(e)}")  # Log any exceptions
        return JsonResponse({
            'status': False,
            'message': str(e)
        })

#Another newest view that has been added
def class_teacher_dashboard(request):
    staff = get_object_or_404(Staff, admin=request.user)
    if not staff.class_teacher:
        messages.error(request, "You are not authorized to access this page")
        return redirect('staff_home')

    course = staff.course
    students = Student.objects.filter(course=course)
    total_students = students.count()
    total_subjects = Subject.objects.filter(course=course).count()
    
    context = {
        'page_title': f'Class Teacher Dashboard - {staff.admin.last_name}',
        'total_students': total_students,
        'total_subjects': total_subjects,
        'students': students,
        'course': course
    }
    return render(request, 'staff_template/class_teacher_dashboard.html', context)

def view_class_students(request):
    staff = get_object_or_404(Staff, admin=request.user)
    if not staff.class_teacher:
        messages.error(request, "You are not authorized to access this page")
        return redirect('staff_home')

    students = Student.objects.filter(course=staff.course)
    context = {
        'students': students,
        'page_title': 'Class Students'
    }
    return render(request, 'staff_template/view_class_students.html', context)

@csrf_exempt
def send_class_results_sms(request):
    staff = get_object_or_404(Staff, admin=request.user)
    if not staff.class_teacher:
        return JsonResponse({
            'status': False,
            'message': 'Unauthorized access'
        })

    if request.method == 'POST':
        try:
            students = Student.objects.filter(course=staff.course)
            success_count = 0
            failure_count = 0

            for student in students:
                results = StudentResult.objects.filter(student=student)
                if results.exists():
                    message = f"Dear Parent/Guardian,\nResults for {student.admin.get_full_name()}:\n"
                    for result in results:
                        total_score = result.test + result.exam
                        grade = calculate_grade(total_score)
                        message += f"\n{result.subject.name}:\nTest: {result.test}\nExam: {result.exam}\nTotal: {total_score}\nGrade: {grade}\n"
                    
                    client = vonage.Client(
                        api_key=settings.VONAGE_API_KEY,
                        api_secret=settings.VONAGE_API_SECRET
                    )
                    sms = vonage.Sms(client)
                    
                    phone_number = student.phone_number
                    if not phone_number.startswith('+'):
                        phone_number = '+234' + phone_number.lstrip('0')
                    
                    response = sms.send_message({
                        'from': settings.VONAGE_BRAND_NAME,
                        'to': phone_number,
                        'text': message
                    })
                    
                    if response['messages'][0]['status'] == '0':
                        SMSLog.objects.create(
                            student=student,
                            staff=staff,
                            message=message,
                            status=True
                        )
                        success_count += 1
                    else:
                        failure_count += 1
            return JsonResponse({
                'status': True,
                'message': f'Successfully sent {success_count} messages. Failed: {failure_count}'
            })
        except Exception as e:
            return JsonResponse({
                'status': False,
                'message': str(e)
            })

def view_individual_results(request):
    staff = get_object_or_404(Staff, admin=request.user)
    if not staff.class_teacher:
        messages.error(request, "You are not authorized to access this page")
        return redirect('staff_home')

    students = Student.objects.filter(course=staff.course)
    context = {
        'students': students,
        'page_title': 'View Individual Results'
    }
    return render(request, 'staff_template/view_individual_results.html', context)

def view_student_result(request, student_id):
    staff = get_object_or_404(Staff, admin=request.user)
    if not staff.class_teacher:
        messages.error(request, "You are not authorized to access this page")
        return redirect('staff_home')

    student = get_object_or_404(Student, id=student_id)
    results = StudentResult.objects.filter(student=student)
    
    context = {
        'student': student,
        'results': results,
        'page_title': f'Results for {student.admin.get_full_name()}'
    }
    return render(request, 'staff_template/view_student_result.html', context)

def preview_student_result(request, student_id):
    staff = get_object_or_404(Staff, admin=request.user)
    if not staff.class_teacher:
        return HttpResponse('Unauthorized', status=403)

    student = get_object_or_404(Student, id=student_id)
    results = StudentResult.objects.filter(student=student)
    
    context = {
        'student': student,
        'results': results,
        'staff': staff,
        'current_year': datetime.now().year
    }
    return render(request, 'staff_template/preview_result.html', context)

def download_student_result(request, student_id):
    staff = get_object_or_404(Staff, admin=request.user)
    if not staff.class_teacher:
        return HttpResponse('Unauthorized', status=403)

    student = get_object_or_404(Student, id=student_id)
    results = StudentResult.objects.filter(student=student)
    teacher_comment = request.GET.get('comment', '')
    
    # Create PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{student.admin.get_full_name()}_result.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # School Logo and Name
    logo_path = os.path.join(settings.STATIC_ROOT, 'img', 'logo.jpeg')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=1*inch, height=1*inch)
        elements.append(logo)
        elements.append(Spacer(1, 10))
    
    school_style = ParagraphStyle(
        'SchoolStyle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1
    )
    elements.append(Paragraph("Juba Adventist Secondary School", school_style))
    elements.append(Spacer(1, 20))
    
    # Student Info
    student_info = [
        ["Student Name:", student.admin.get_full_name()],
        ["Class:", student.course.name],
        ["Academic Year:", datetime.now().year],
        ["Class Teacher:", staff.admin.get_full_name()]
    ]
    
    # Create table for student info
    info_table = Table(student_info, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Results Table
    result_data = [['Subject', 'Test', 'Exam', 'Total', 'Grade']]
    for result in results:
        total_score = result.test + result.exam
        grade = calculate_grade(total_score)
        result_data.append([
            result.subject.name,
            str(result.test),
            str(result.exam),
            str(total_score),
            grade
        ])
    
    result_table = Table(result_data, colWidths=[2*inch, 1*inch, 1*inch, 1*inch, 1*inch])
    result_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(result_table)
    
    # Class Teacher's Comment
    elements.append(Spacer(1, 20))
    comment_style = ParagraphStyle(
        'CommentStyle',
        parent=styles['Normal'],
        fontSize=12,
        leading=14
    )
    elements.append(Paragraph("Class Teacher's Comment:", styles['Heading2']))
    elements.append(Paragraph(teacher_comment or "No comment provided.", comment_style))
    
    # Build PDF
    doc.build(elements)
    return response


