from django.shortcuts import render, get_object_or_404
import json
import razorpay
from django.conf import settings
from django.http import JsonResponse
from django.core.mail import send_mail
from .models import (Course, Enrollment, Enquiry, Branch,
                    EnvironmentImage, FAQ, StudentProject,
                    StudentStory,)
from django.http import HttpResponse
from django.utils import timezone
import logging
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.views.decorators.csrf import csrf_exempt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from io import BytesIO


logger = logging.getLogger(__name__)

# Create your views here.
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def home(request):
    featured_courses = Course.objects.filter(is_featured=True)[:3]
    projects = StudentProject.objects.all()[:3]
    stories = StudentStory.objects.all()
    return render(request, 'home.html',
                  {'featured_courses': featured_courses,
                   'projects': projects,
                   'stories': stories,
                   })

def courses(request):
    category = request.GET.get('category')

    if category and category != "All":
        courses = Course.objects.filter(category=category)
    else:
        courses = Course.objects.all()
        category = "All"

    context = {
        'courses': courses,
        'active_category': category
    }
    return render(request, 'courses/course_list.html', context)

def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    return render(request, 'courses/course_detail.html', {'course': course})

def create_enrollment(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        
        try:
            course = Course.objects.get(id=data['course_id'])
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
                message=data['message']
            )

            base_amount = int(float(course.course_fee.replace(',', '').replace('₹', '').strip()))
            gst = int(base_amount * 0.18) 
            total_amount = base_amount + gst
            order_amount = total_amount * 100
            order_currency = 'INR'
            order_receipt = f'order_rcptid_{enrollment.id}'
            
            razorpay_order = client.order.create(dict(amount=order_amount, currency=order_currency, receipt=order_receipt))
            enrollment.razorpay_order_id = razorpay_order['id']
            enrollment.save()

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
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'invalid method'}, status=405)

def verify_payment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.info(f"Received payment success data: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'}, status=400)
        
        try:
            try:
                enrollment = Enrollment.objects.get(razorpay_order_id=data['razorpay_order_id'])
                enrollment.payment_status = 'Paid'
                enrollment.save()
                logger.info(f"Enrollment {enrollment.id} updated to Paid.")
            except Enrollment.DoesNotExist:
                logger.error(f"Enrollment not found for order_id: {data['razorpay_order_id']}")
                return JsonResponse({'status': 'error', 'message': 'Enrollment not found.'}, status=404)
            except Exception as e:
                logger.error(f"Database update failed: {e}")
                return JsonResponse({'status': 'error', 'message': 'Failed to update payment status.'}, status=500)

            try:
                subject = f"Enrollment Confirmation - {enrollment.course.coursename}"
                message = f"""
                Dear {enrollment.first_name} {enrollment.last_name},

                Thank you for enrolling in "{enrollment.course.coursename}" at Vetri Technology Solutions.

                Your payment of ₹{enrollment.course.course_fee} has been successfully received. 
                Payment Reference ID: {data['razorpay_payment_id']}

                Our team will contact you shortly with further instructions.

                Best Regards,
                Vetri Technology Solutions Team
                """
                send_mail(subject, message, settings.EMAIL_HOST_USER, [enrollment.email], fail_silently=True)
                logger.info("Confirmation email sent.")
            except Exception as e:
                logger.error(f"Email sending failed: {e}")

            try:
                base_amount = int(float(enrollment.course.course_fee.replace(',', '').replace('₹', '').strip()))
                gst = int(base_amount * 0.18)
                total_amount = base_amount + gst
            except Exception as e:
                logger.error(f"Amount calculation failed: {e}")
                total_amount = 0

            response_data = {
                'status': 'success',
                'transaction_id': data['razorpay_payment_id'],
                'date': timezone.now().strftime('%d/%m/%Y'),
                'amount': f"{total_amount:,.0f}",
                'email': enrollment.email,
                'method': 'Online Payment',
                'order_id': enrollment.razorpay_order_id
            }
            logger.info(f"Payment success, returning: {response_data}")
            return JsonResponse(response_data)

        except Exception as e:
            logger.error(f"Unexpected error in verify_payment: {e}")
            return JsonResponse({'status': 'error', 'message': f'Error updating system: {str(e)}'}, status=500)
            
    return JsonResponse({'status': 'invalid method'}, status=405)


def download_invoice(request, order_id):
    try:
        enrollment = Enrollment.objects.get(razorpay_order_id=order_id)
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1, 
            textColor=colors.darkblue
        )
        normal_style = styles['Normal']
        normal_style.fontSize = 12
        
        elements = []
        
        elements.append(Paragraph("INVOICE", title_style))
        elements.append(Spacer(1, 12))
        
        data = [
            ['Field', 'Details'],
            ['Name', f"{enrollment.first_name} {enrollment.last_name}"],
            ['Course', enrollment.course.coursename],
            ['Amount', enrollment.course.course_fee],
            ['Status', 'PAID'],
            ['Order ID', order_id],
            ['Date', timezone.now().strftime('%d/%m/%Y')]
        ]
        
        table = Table(data, colWidths=[150, 300])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{order_id}.pdf"'
        return response
    
    except Enrollment.DoesNotExist:
        return HttpResponse("Invoice not found.", status=404)
    except Exception as e:
        logger.error(f"Error generating PDF invoice: {e}")
        return HttpResponse("Error generating invoice.", status=500)

def about(request):
    return render(request, 'about.html')

def contact(request):
    branches = Branch.objects.all()
    env_images = EnvironmentImage.objects.all()
    faqs = FAQ.objects.all()
    valid_map_branches = branches.filter(latitude__isnull=False, longitude__isnull=False)
    branches_data = list(valid_map_branches.values('name', 'address', 'latitude', 'longitude', 'map_link'))

    context = {
        'branches': branches,
        'branches_json': json.dumps(branches_data),
        'env_images': env_images,
        'faqs': faqs,
    }
    return render(request, 'contact.html', context)


@csrf_exempt
def submit_enquiry(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            Enquiry.objects.create(
                full_name=data.get('full_name'),
                email=data.get('email'),
                phone=data.get('phone'),
                course_interest=data.get('course_interest'),
                message=data.get('message')
            )
            return JsonResponse({'status': 'success', 'message': 'Enquiry submitted successfully!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)


def image_gallery(request):
    images = EnvironmentImage.objects.all()
    return render(request, 'image.html', {'images': images})