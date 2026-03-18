from django.shortcuts import render, get_object_or_404
import json
import razorpay
from django.conf import settings
from django.http import JsonResponse
from django.core.mail import send_mail
from .models import *
from django.http import HttpResponse
from django.utils import timezone
import logging
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
import re
from django.contrib.staticfiles import finders
import os
from num2words import num2words
from requests.exceptions import RequestException
from django.db import transaction
from django.core.cache import cache
from datetime import timezone as dt_timezone, timedelta
import base64
from django.template.loader import render_to_string
from weasyprint import HTML, CSS



logger = logging.getLogger(__name__)
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


RS = '\u20B9'                    
IST = dt_timezone(timedelta(hours=5, minutes=30))
 
 
def rs(amount):
    return f"Rs.{amount:,}"

def parse_course_fee(course):
    """
    Returns (base_amount, gst, total) as plain ints.

    Handles both the old CharField format ("₹ 10,000") and
    the new DecimalField (10000.00) transparently.
    """
    raw = str(course.course_fee).replace('₹', '').replace('Rs.', '').replace(',', '').strip()
    try:
        base = int(float(raw))
    except (ValueError, TypeError):
        base = 0
    gst   = int(base * 0.18)
    total = base + gst
    return base, gst, total


def home(request):
    featured_courses = cache.get('featured_courses')
    if not featured_courses:
        featured_courses = list(
            Course.objects.select_related('category') 
                          .filter(is_featured=True)[:3]
        )
        cache.set('featured_courses', featured_courses, 300)

    projects = StudentProject.objects.all()[:3]
    stories  = StudentStory.objects.all()
    return render(request, 'home.html', {
        'featured_courses': featured_courses,
        'projects': projects,
        'stories': stories,
    })


def course_autocomplete(request):
    if 'term' in request.GET:
        term = request.GET.get('term')
        courses = Course.objects.filter(coursename__icontains=term)[:10]
        course_names = list(courses.values_list('coursename', flat=True))
        return JsonResponse(course_names, safe=False)
    return JsonResponse([], safe=False)


def courses(request):
    search_query = request.GET.get('q', '').strip()
    category     = request.GET.get('category', 'All')
    categories   = CourseCategory.objects.all()

    if not search_query and category == 'All':
        all_courses = cache.get('all_courses')
        if not all_courses:
            all_courses = list(
                Course.objects.select_related('category').all()
            )
            cache.set('all_courses', all_courses, 120)
        courses_qs = all_courses
    else:
        courses_qs = Course.objects.select_related('category')
        if category != 'All':
            courses_qs = courses_qs.filter(category=category)
        if search_query:
            courses_qs = courses_qs.filter(
                Q(coursename__icontains=search_query) |
                Q(category__name__icontains=search_query) |
                Q(short_description__icontains=search_query)
            ).distinct()

    context = {
        'courses': courses_qs,
        'active_category': category,
        'search_query': search_query,
        'categories': categories,
    }
    return render(request, 'courses/course_list.html', context)


def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    return render(request, 'courses/course_detail.html', {'course': course})


def create_enrollment(request):
    if request.method == 'POST':
        try:
            data   = json.loads(request.body)
            course = Course.objects.get(id=data['course_id'])
            base_amount, gst, total_amount = parse_course_fee(course)
            order_amount   = total_amount * 100
            order_currency = 'INR'

            try:
                razorpay_order = client.order.create(dict(
                    amount=order_amount,
                    currency=order_currency,
                    receipt=f"rcpt_course_{course.id}"
                ))
            except RequestException as net_err:
                logger.error(f"Razorpay Network Error: {net_err}")
                raise Exception("Payment gateway is currently unreachable. Please try again.")

            return JsonResponse({
                'status': 'success',
                'order_id': razorpay_order['id'],
                'amount': order_amount,
                'key': settings.RAZORPAY_KEY_ID,
                'base_amount': base_amount,
                'gst': gst,
                'total': total_amount
            })

        except Exception as e:
            logger.error(f"Error in create_enrollment: {e}")
            error_msg = str(e) if "Payment gateway" in str(e) else "An unexpected error occurred."
            return JsonResponse({'status': 'error', 'message': error_msg}, status=400)

    return JsonResponse({'status': 'invalid method'}, status=405)


def verify_payment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'}, status=400)

        try:
            # ── Step 1: Signature verification ────────────────────────────────
            try:
                client.utility.verify_payment_signature({
                    'razorpay_order_id':  data['razorpay_order_id'],
                    'razorpay_payment_id': data['razorpay_payment_id'],
                    'razorpay_signature':  data['razorpay_signature']
                })
            except razorpay.errors.SignatureVerificationError:
                return JsonResponse(
                    {'status': 'error', 'message': 'Payment verification failed. Signature mismatch.'},
                    status=400
                )

            # ── Step 2: Fetch payment details from Razorpay ───────────────────
            payment_method = 'Online'
            bank_rrn = 'N/A'
            try:
                razorpay_payment = client.payment.fetch(data['razorpay_payment_id'])
                raw_method = razorpay_payment.get('method', 'Online')
                payment_method = raw_method.upper()
                acquirer_data  = razorpay_payment.get('acquirer_data', {})
                if raw_method == 'upi':
                    bank_rrn = acquirer_data.get('rrn') or acquirer_data.get('upi_transaction_id', 'N/A')
                elif raw_method == 'netbanking':
                    bank_rrn = acquirer_data.get('bank_transaction_id', 'N/A')
                elif raw_method == 'card':
                    bank_rrn = acquirer_data.get('auth_code', 'N/A')
                else:
                    bank_rrn = (
                        acquirer_data.get('rrn') or
                        acquirer_data.get('bank_transaction_id') or
                        acquirer_data.get('upi_transaction_id', 'N/A')
                    )
            except Exception as pay_err:
                logger.warning(f"Could not fetch payment details: {pay_err}")

            # ── Step 3: Validate inputs ───────────────────────────────────────
            user_data = data.get('user_details')
            if not user_data:
                return JsonResponse({'status': 'error', 'message': 'User details missing.'}, status=400)

            course_id = str(user_data.get('course_id', '')).strip()
            if not course_id:
                return JsonResponse(
                    {'status': 'error', 'message': 'Course ID is missing. Please select a course.'},
                    status=400
                )

            # ── Step 4: Save enrollment ───────────────────────────────────────
            try:
                course = Course.objects.get(id=course_id)
                enrollment = Enrollment.objects.create(
                    course=course,
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    email=user_data['email'],
                    phone=user_data['phone'],
                    gender=user_data['gender'],
                    dob=user_data['dob'],
                    address=user_data['address'],
                    city=user_data['city'],
                    state=user_data['state'],
                    pincode=user_data['pincode'],
                    mode=user_data['mode'],
                    message=user_data.get('message', ''),
                    razorpay_order_id=data['razorpay_order_id'],
                    razorpay_payment_id=data['razorpay_payment_id'],
                    payment_method=payment_method,
                    bank_rrn=bank_rrn,
                    payment_date=timezone.now(),
                    payment_status='Paid',
                )
            except Course.DoesNotExist:
                return JsonResponse(
                    {'status': 'error', 'message': f'Course ID "{course_id}" not found.'},
                    status=400
                )
            except Exception as e:
                logger.error(f"DB creation failed: {e}")
                return JsonResponse({'status': 'error', 'message': 'Failed to save enrollment.'}, status=500)

            # ── Step 5: Amounts via shared helper ─────────────────────────────
            base_amount, gst, total_amount = parse_course_fee(course)

            # ── Step 6: Email ─────────────────────────────────────────────────
            try:
                send_mail(
                    f"Enrollment Confirmation - {course.coursename}",
                    f"Dear {enrollment.first_name} {enrollment.last_name},\n\n"
                    f"Thank you for enrolling in \"{course.coursename}\".\n"
                    f"Payment ₹{total_amount} received.\n\n "
                    f"Ref: {data['razorpay_payment_id']}\n\n"
                    f"Our Team will contact you shortly with further details.\n\n"
                    f"Best Regards,\nVetri Technology Solutions",

                    settings.EMAIL_HOST_USER,
                    [enrollment.email],
                    fail_silently=True
                )
            except Exception as e:
                logger.error(f"Email failed: {e}")

            return JsonResponse({
                'status': 'success',
                'transaction_id': data['razorpay_payment_id'],
                'date': timezone.now().strftime('%d/%m/%Y'),
                'amount': f"{total_amount:,.0f}",
                'email': enrollment.email,
                'method': payment_method,
                'order_id': data['razorpay_order_id']
            })

        except Exception as e:
            logger.error(f"Unexpected error in verify_payment: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'invalid method'}, status=405)


def amount_in_words(amount):
    try:
        rupees = int(amount)
        paise  = round((amount - rupees) * 100)
        words  = num2words(rupees, lang='en_IN').title()
        if paise:
            words += f" and {num2words(paise, lang='en_IN').title()} Paise"
        return f"(Rupees {words} Only)"
    except Exception:
        return ""


def download_invoice(request, order_id):
    try:
        enrollment = Enrollment.objects.select_related('course').get(
            razorpay_order_id=order_id
        )

        IST = timezone.get_fixed_timezone(330)
        pay_dt = enrollment.payment_date or timezone.now()
        pay_dt_ist = pay_dt.astimezone(IST)
        
        base_amount, _, total_amount = parse_course_fee(enrollment.course)
        gst_amount = base_amount * 0.18
        

        logo_path = finders.find('images/VTSlogo.jpg')
        if logo_path:
            logo_url = 'file:///' + logo_path.replace('\\', '/')
        else:
            logo_url = None

        context = {
            'enrollment': enrollment,
            'inv_date': pay_dt_ist.strftime('%d-%m-%Y'),
            'pay_date_str': pay_dt_ist.strftime('%d-%m-%Y %I:%M:%S %p'),
            'base_amount': f"{base_amount:,.2f}",
            'gst_amount': f"{gst_amount:,.2f}",
            'total_amount': f"{total_amount:,.2f}",
            'amount_words': amount_in_words(total_amount),
            'logo_url': logo_url,
        }

        html_string = render_to_string('invoice_pdf.html', context)
        
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        pdf = html.write_pdf()

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Invoice_{enrollment.id}.pdf"'
        return response

    except Enrollment.DoesNotExist:
        return HttpResponse("Invoice not found.", status=404)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)
    


def about(request):
    return render(request, 'about.html')


def contact(request):
    branches = Branch.objects.all()
    env_images = EnvironmentImage.objects.all()
    faqs = FAQ.objects.all()
    valid_map_branches = branches.filter(latitude__isnull=False, longitude__isnull=False)
    branches_data = list(valid_map_branches.values('name', 'address', 'latitude', 'longitude', 'map_link'))
    courses = Course.objects.values_list('coursename', flat=True).order_by('coursename')

    context = {
        'branches': branches,
        'branches_json': json.dumps(branches_data),
        'env_images': env_images,
        'faqs': faqs,
        'courses': [{'coursename': n} for n in courses],
    }
    return render(request, 'contact.html', context)


def submit_enquiry(request):
    if request.method == 'POST':
        try:
            data          = json.loads(request.body)
            full_name     = data.get('full_name', '').strip()
            email         = data.get('email', '').strip()
            phone         = data.get('phone', '').strip()
            course_interest = data.get('course_interest', '').strip()
            message       = data.get('message', '').strip()

            if not all([full_name, email, phone, course_interest, message]):
                return JsonResponse({'status': 'error', 'message': 'All fields are required.'}, status=400)
            if not re.match(r"^[A-Za-z\s\.\-']+$", full_name):
                return JsonResponse({'status': 'error', 'message': 'Please enter a valid name (numbers are not allowed).'}, status=400)
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                return JsonResponse({'status': 'error', 'message': 'Please enter a valid email address.'}, status=400)
            if not phone.isdigit() or len(phone) < 10:
                return JsonResponse({'status': 'error', 'message': 'Please enter a valid 10-digit phone number.'}, status=400)

            Enquiry.objects.create(
                full_name=full_name, email=email, phone=phone,
                course_interest=course_interest, message=message
            )

            try:
                send_mail(
                    f"New Enquiry: {course_interest} - {full_name}",
                    f"Name: {full_name}\nEmail: {email}\nPhone: {phone}\n"
                    f"Course: {course_interest}\n\nMessage:\n{message}",
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.ADMIN_EMAIL],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Enquiry saved, email failed: {e}")

            return JsonResponse({'status': 'success', 'message': 'Enquiry submitted successfully!'})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid data format received.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


def image_gallery(request):
    return render(request, 'image.html', {'images': EnvironmentImage.objects.all()})


def student_projects(request):
    return render(request, 'studentsproject.html', {'projects': StudentProject.objects.all()})