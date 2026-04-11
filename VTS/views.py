from django.shortcuts import render, get_object_or_404
import json
from django.conf import settings
from django.http import JsonResponse
from django.core.mail import send_mail
from .models import *
import logging
from django.db.models import Q
import re
from django.db import transaction
from django.core.cache import cache
from django.template.loader import render_to_string
import threading
from django.views.decorators.csrf import csrf_exempt


logger = logging.getLogger(__name__)


def home(request):
    featured_courses = cache.get('featured_courses')
    if not featured_courses:
        featured_courses = list(
            Course.objects.select_related('category') 
                          .filter(is_featured=True)[:3]
        )
        cache.set('featured_courses', featured_courses, 300)

    projects = StudentProject.objects.all()[:3]
    company_stats = CompanyStat.objects.all()
    sections = StorySection.objects.prefetch_related('stories').all()
    active_banner = HomeBanner.objects.filter(is_active=True).first()
    about_section = HomeAboutSection.objects.filter(is_active=True).first()
    benefit_section = HomeBenefitSection.objects.prefetch_related('cards').filter(is_active=True).first()
    process_section = HomeProcessSection.objects.prefetch_related('steps').filter(is_active=True).first()
    learning_cta = LearningJourneyCTA.objects.filter(is_active=True).first()

    grouped_stories = {}

    for section in sections:
        stories = section.stories.all() 
        if stories.exists(): 
            grouped_stories[section.name] = stories

    return render(request, 'home.html', {
        'featured_courses': featured_courses,
        'projects': projects,
        'grouped_stories': grouped_stories,
        'company_stats': company_stats,
        'banner': active_banner,
        'about_section': about_section,
        'benefit_section': benefit_section,
        'process_section': process_section,
        'learning_cta': learning_cta,
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

def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug)
    return render(request, 'courses/course_detail.html', {'course': course})

@transaction.atomic
def create_enrollment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            course = get_object_or_404(Course, id=data['course_id'])
            enrollment = Enrollment.objects.create(
                course=course,
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=data['email'],
                phone=data['phone'],
                gender=data['gender'],
                dob=data['dob'],
                address=data['address'],
                city=data['city'],
                state=data['state'],
                pincode=data['pincode'],
                mode=data['mode'],
                message=data.get('message', ''),
                payment_status='Pending' 
            )

            # 2. Prepare Emails
            student_subject = f"Application Received - {course.coursename}"
            try:
                student_msg = render_to_string('emails/student_application_ack.txt', {
                    'name': enrollment.first_name,
                    'course': course.coursename
                })
            except Exception:
                # Fallback if text template is missing
                student_msg = f"Dear {enrollment.first_name},\n\nYour application for {course.coursename} was received. Our team will contact you shortly.\n\nRegards,\nVetri Technology Solutions."

            admin_subject = f"New Enrollment Application: {enrollment.first_name} {enrollment.last_name}"
            admin_msg = (
                f"New candidate application received!\n\n"
                f"--- STUDENT DETAILS ---\n"
                f"Name: {enrollment.first_name} {enrollment.last_name}\n"
                f"Gender: {enrollment.gender}\n"
                f"Date of Birth: {enrollment.dob}\n"
                f"Phone: {enrollment.phone}\n"
                f"Email: {enrollment.email}\n\n"
                f"--- LOCATION ---\n"
                f"Address: {enrollment.address}\n"
                f"City: {enrollment.city}\n"
                f"State: {enrollment.state}\n"
                f"Pincode: {enrollment.pincode}\n\n"
                f"--- ENROLLMENT INFO ---\n"
                f"Course: {course.coursename}\n"
                f"Mode: {enrollment.mode}\n"
                f"Message: {enrollment.message}\n"
            )
            # 3. Send Emails Synchronously to catch errors
            try:
                send_mail(student_subject, student_msg, settings.EMAIL_HOST_USER, [enrollment.email], fail_silently=False)
                send_mail(admin_subject, admin_msg, settings.EMAIL_HOST_USER, [settings.ADMIN_EMAIL], fail_silently=True)
            except Exception as email_err:
                logger.error(f"Email delivery failed: {email_err}")
                raise Exception("Failed to send confirmation email. Please check your email address or try again later.")

            return JsonResponse({'status': 'success', 'message': 'Application submitted successfully'})

        except Exception as e:
            logger.error(f"Enrollment Error: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


def about(request):
    company_stats = CompanyStat.objects.all()
    about_content = AboutPageSection.objects.filter(is_active=True).first()
    mission_vision = AboutMissionVision.objects.filter(is_active=True).first()
    ecosystem_section = EcosystemSection.objects.prefetch_related('branches').filter(is_active=True).first()
    approach_section = AboutApproachSection.objects.prefetch_related('cards').filter(is_active=True).first()
    skills_section = CareerSkillsSection.objects.prefetch_related('cards').filter(is_active=True).first()
    journey_section = JourneySection.objects.prefetch_related('steps').filter(is_active=True).first()
    enrollment_section = EnrollmentSection.objects.prefetch_related('audiences').filter(is_active=True).first()
    cta_banner = CTABanner.objects.filter(is_active=True).first()
    
    context = {
        'company_stats': company_stats,
        'about_content': about_content,
        'mission_vision': mission_vision,
        'ecosystem_section': ecosystem_section,
        'approach_section': approach_section,
        'skills_section': skills_section,
        'journey_section': journey_section,
        'enrollment_section': enrollment_section,
        'cta_banner': cta_banner,
    }
    return render(request, 'about.html',context)

def contact(request):
    branches = Branch.objects.all()
    env_images = EnvironmentImage.objects.all()
    faqs = FAQ.objects.all()
    valid_map_branches = branches.filter(latitude__isnull=False, longitude__isnull=False)
    branches_data = list(valid_map_branches.values('name', 'address', 'latitude', 'longitude', 'map_link'))
    courses = Course.objects.values_list('coursename', flat=True).order_by('coursename')
    contact_cards = ContactInfoCard.objects.filter(is_active=True)
    categories = ImageCategory.objects.prefetch_related('images').all()
    grouped_env_images = {}
    
    for category in categories:
        images = category.images.all()
        if images.exists():
            grouped_env_images[category.name] = images

    phone_records = Contactnumber.objects.all()

    if phone_records.exists():
        phones = [record.contact_numbers for record in phone_records]
    else:
        phones = "8438164827"

    context = {
        'branches': branches,
        'branches_json': json.dumps(branches_data),
        'env_images': env_images,
        'faqs': faqs,
        'courses': [{'coursename': n} for n in courses],
        'grouped_env_images': grouped_env_images,
        'contact_numbers': phones,
        'contact_cards': contact_cards,
    }
    return render(request, 'contact.html', context)

def send_async_email(subject, message, from_email, recipient_list):
    try:
        send_mail(subject, message, from_email, recipient_list, fail_silently=True)
    except Exception as e:
        logger.error(f"Threaded email failed: {e}")

def submit_enquiry(request):
    if request.method == 'POST':
        try:
            data            = json.loads(request.body)
            full_name       = data.get('full_name', '').strip()
            email           = data.get('email', '').strip()
            phone           = data.get('phone', '').strip()
            course_interest = data.get('course_interest', '').strip()
            message         = data.get('message', '').strip()

            if not all([full_name, email, phone, course_interest, message]):
                return JsonResponse({'status': 'error', 'message': 'All fields are required.'}, status=400)
            if not re.match(r"^[A-Za-z\s\.\-']+$", full_name):
                return JsonResponse({'status': 'error', 'message': 'Please enter a valid name (letters only).'}, status=400)
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                return JsonResponse({'status': 'error', 'message': 'Please enter a valid email address.'}, status=400)
            if not phone.isdigit() or len(phone) < 10:
                return JsonResponse({'status': 'error', 'message': 'Please enter a valid 10-digit phone number.'}, status=400)

            with transaction.atomic():
                Enquiry.objects.create(
                    full_name=full_name, email=email, phone=phone,
                    course_interest=course_interest, message=message
                )

                subject = f"New Enquiry: {course_interest} - {full_name}"
                body = (f"Name: {full_name}\nEmail: {email}\nPhone: {phone}\n"
                        f"Course: {course_interest}\n\nMessage:\n{message}")

                try:
                    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_EMAIL], fail_silently=False)
                except Exception as email_err:
                    logger.error(f"Enquiry email failed: {email_err}")
                    raise Exception("Failed to send enquiry email. Please check your connection or try again later.")

            return JsonResponse({'status': 'success', 'message': 'Enquiry submitted successfully!'})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid data format received.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


def image_gallery(request):
    categories = ImageCategory.objects.prefetch_related('images').all()
    grouped_env_images = {}
    
    for category in categories:
        images = category.images.all()
        if images.exists():
            grouped_env_images[category.name] = images
    
    context = {
        'grouped_env_images': grouped_env_images,
    }
    return render(request, 'image.html', context)


from django.views.decorators.http import require_POST

@require_POST
def save_brochure_lead(request):
    try:
        data = json.loads(request.body)
        BrochureLead.objects.create(
            name=data.get('name'),
            email=data.get('email'),
            phone=data.get('phone'),
            course_name=data.get('course_name')
        )
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
def student_projects(request):
    return render(request, 'studentsproject.html', {'projects': StudentProject.objects.all()})