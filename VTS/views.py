from django.shortcuts import render, get_object_or_404
import json
import razorpay
from django.conf import settings
from django.http import JsonResponse
from django.core.mail import send_mail
from .models import (Course, Enrollment, Enquiry, Branch,
                    EnvironmentImage, FAQ, StudentProject,
                    StudentStory,StudentProject,)
from django.http import HttpResponse
from django.utils import timezone
import logging
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.views.decorators.csrf import csrf_exempt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from io import BytesIO
from django.db.models import Q
import re
from reportlab.platypus import Image
from django.contrib.staticfiles import finders
import os


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
    courses = Course.objects.all()
    search_query = request.GET.get('q', '').strip()
    category = request.GET.get('category', 'All')
    
    if category != "All":
        courses = courses.filter(category=category)
        
    if search_query:
        courses = courses.filter(
            Q(coursename__icontains=search_query) | 
            Q(category__icontains=search_query) |
            Q(short_description__icontains=search_query)
        ).distinct()

    context = {
        'courses': courses,
        'active_category': category,
        'search_query': search_query,
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
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()
        
        normal_style = styles['Normal']
        normal_style.fontSize = 10
        normal_style.leading = 14 
        
        bold_style = ParagraphStyle('BoldText', parent=normal_style, fontName='Helvetica-Bold')
        
        elements = []
        
        # ==========================================
        # 1. HEADER SECTION (Logo & Company Info)
        # ==========================================
        logo_path = finders.find('images/VTSlogo.jpg')
        
        if logo_path and os.path.exists(logo_path):
            logo = Image(logo_path, width=120, height=50, kind='proportional')
        else:
            logo = Paragraph("<b><font size=32 color='#6C2CB1'>VTS</font></b>", styles['Normal'])
        
        company_info = Paragraph(
            "<b>Vetri Technology Solutions</b><br/>"
            "April's Completx, Bus Stand backside,<br/>"
            "Surandai-600001", 
            normal_style
        )
        
        header_table = Table([[logo, company_info]], colWidths=[150, 380])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, 0), 'LEFT'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10))
        
        line = Table([['']], colWidths=[530])
        line.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, -1), 1, colors.black)]))
        elements.append(line)
        elements.append(Spacer(1, 20))
        
        # ==========================================
        # 2. BILL TO & INVOICE DETAILS SECTION
        # ==========================================
        customer_details = Paragraph(
            f"{enrollment.first_name} {enrollment.last_name}<br/>"
            f"+91-{enrollment.phone}<br/>"
            f"{enrollment.address}<br/>"
            f"{enrollment.city}, {enrollment.state} - {enrollment.pincode}",
            normal_style
        )
        
        invoice_date = timezone.now().strftime('%d/%m/%Y')
        
        info_data = [
            [
                Paragraph("<b>Bill To</b>", normal_style), 
                customer_details, 
                '', 
                Paragraph("<b>Invoice no.</b>", normal_style), 
                Paragraph(order_id, normal_style)
            ],
            [
                '', '', '', 
                Paragraph("<b>Date</b>", normal_style), 
                Paragraph(invoice_date, normal_style)
            ]
        ]
        
        # Widths total 530
        info_table = Table(info_data, colWidths=[60, 200, 50, 70, 150])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'), 
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 25))
        
        # ==========================================
        # 3. MAIN ITEM GRID SECTION
        # ==========================================
        clean_fee = str(enrollment.course.course_fee).replace('₹', '').replace('Rs.', '').strip()
        formatted_fee = f"Rs. {clean_fee}"
        
        item_data = [
            [
                Paragraph('<b>Description</b>', normal_style), 
                Paragraph('<b>Quantity</b>', normal_style), 
                Paragraph('<b>Unit price</b>', normal_style), 
                Paragraph('<b>Amount</b>', normal_style)
            ],
            [
                Paragraph(enrollment.course.coursename, normal_style), 
                '1', 
                formatted_fee, 
                formatted_fee
            ]
        ]
        
        item_table = Table(item_data, colWidths=[280, 70, 90, 90])
        item_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),         
            ('INNERGRID', (0, 0), (-1, -1), 1, colors.black),     
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),     
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 40),      
        ]))
        elements.append(item_table)
        elements.append(Spacer(1, 10))
        
        # ==========================================
        # 4. SUMMARY SECTION (Right Aligned)
        # ==========================================
        summary_data = [
            [Paragraph('<b>Total</b>', normal_style), Paragraph(formatted_fee, normal_style)],
            [Paragraph('<b>Paid Amount</b>', normal_style), Paragraph(formatted_fee, normal_style)],
            [Paragraph('<b>Balance Due</b>', normal_style), Paragraph('Rs. 0', normal_style)],
        ]
        
        summary_table = Table(summary_data, colWidths=[90, 90])
        summary_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBELOW', (0, 0), (-1, -1), 1, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        layout_table = Table([['', summary_table]], colWidths=[350, 180])
        elements.append(layout_table)
        
  
        doc.build(elements)
        buffer.seek(0)
        
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Invoice_{order_id}.pdf"'
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


def submit_enquiry(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # 1. Clean the data
            full_name = data.get('full_name', '').strip()
            email = data.get('email', '').strip()
            phone = data.get('phone', '').strip()
            course_interest = data.get('course_interest', '').strip()
            message = data.get('message', '').strip()

            # 2. BACKEND VALIDATION
            if not all([full_name, email, phone, course_interest, message]):
                return JsonResponse({'status': 'error', 'message': 'All fields are required.'}, status=400)
            
            # ---> NEW: Validate Name (Allows only letters, spaces, hyphens, and dots. NO numbers)
            if not re.match(r"^[A-Za-z\s\.\-']+$", full_name):
                return JsonResponse({'status': 'error', 'message': 'Please enter a valid name (numbers are not allowed).'}, status=400)
                
            # Validate Email format
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                return JsonResponse({'status': 'error', 'message': 'Please enter a valid email address.'}, status=400)
                
            # Validate Phone (must be digits and exactly 10 numbers)
            if not phone.isdigit() or len(phone) < 10:
                return JsonResponse({'status': 'error', 'message': 'Please enter a valid 10-digit phone number.'}, status=400)

            # 3. Save to Database
            enquiry = Enquiry.objects.create(
                full_name=full_name,
                email=email,
                phone=phone,
                course_interest=course_interest,
                message=message
            )

            # 4. SEND EMAIL TO ADMIN
            subject = f"New Enquiry: {course_interest} - {full_name}"
            email_body = f"""
            Hello Admin,

            You have received a new course enquiry from the website.

            Details:
            ---------------------
            Name: {full_name}
            Email: {email}
            Phone: {phone}
            Interested Course: {course_interest}
            
            Message:
            {message}
            ---------------------
            """
            
            try:
                send_mail(
                    subject,
                    email_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.ADMIN_EMAIL], 
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Enquiry saved, but email failed to send: {e}")

            return JsonResponse({'status': 'success', 'message': 'Enquiry submitted successfully!'})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid data format received.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


def image_gallery(request):
    images = EnvironmentImage.objects.all()
    return render(request, 'image.html', {'images': images})


def student_projects(request):
    projects = StudentProject.objects.all()
    return render(request, 'studentsproject.html', {'projects': projects})