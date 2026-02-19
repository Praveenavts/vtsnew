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
from requests.exceptions import ConnectionError
from requests.exceptions import RequestException
from django.db import transaction
from .models import Course


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

def course_autocomplete(request):
    if 'term' in request.GET:
        term = request.GET.get('term')
        # Filter courses containing the typed term (case-insensitive)
        courses = Course.objects.filter(coursename__icontains=term)[:10] # Limit to 10 suggestions
        
        # Create a list of course names
        course_names = list(courses.values_list('coursename', flat=True))
        
        return JsonResponse(course_names, safe=False)
    
    return JsonResponse([], safe=False)


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
        try:
            data = json.loads(request.body)
            course = Course.objects.get(id=data['course_id'])

            # Calculate amounts
            base_amount = int(float(course.course_fee.replace(',', '').replace('₹', '').strip()))
            gst = int(base_amount * 0.18) 
            total_amount = base_amount + gst
            order_amount = total_amount * 100  # Razorpay expects paise
            order_currency = 'INR'
            
            # Hit Razorpay API (NO DATABASE SAVING HERE YET)
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
            logger.info(f"Received payment success data: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'}, status=400)
        
        try:
            # 1. Verify the Razorpay Signature to ensure the payment is legitimate
            try:
                client.utility.verify_payment_signature({
                    'razorpay_order_id': data['razorpay_order_id'],
                    'razorpay_payment_id': data['razorpay_payment_id'],
                    'razorpay_signature': data['razorpay_signature']
                })
            except razorpay.errors.SignatureVerificationError:
                logger.error("Razorpay signature verification failed.")
                return JsonResponse({'status': 'error', 'message': 'Payment verification failed. Signature mismatch.'}, status=400)

            # 2. Extract User Details sent from the frontend
            user_data = data.get('user_details')
            if not user_data:
                return JsonResponse({'status': 'error', 'message': 'User details missing from request.'}, status=400)

            # 3. Create the Enrollment record NOW (since payment succeeded)
            try:
                course = Course.objects.get(id=user_data['course_id'])
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
                    message=user_data['message'],
                    razorpay_order_id=data['razorpay_order_id'],
                    payment_status='Paid'  # Mark as paid immediately
                )
                logger.info(f"New Enrollment created and set to Paid: {enrollment.id}")
            except Exception as e:
                logger.error(f"Database creation failed: {e}")
                return JsonResponse({'status': 'error', 'message': 'Failed to save enrollment to database.'}, status=500)

            # 4. Calculate Amounts for the Email and Response
            try:
                base_amount = int(float(course.course_fee.replace(',', '').replace('₹', '').strip()))
                gst = int(base_amount * 0.18)
                total_amount = base_amount + gst
            except Exception as e:
                logger.error(f"Amount calculation failed: {e}")
                total_amount = data.get('amount_paid', 0) # Fallback to frontend amount

            # 5. Send Confirmation Email
            try:
                subject = f"Enrollment Confirmation - {course.coursename}"
                message = f"""
                        Dear {enrollment.first_name} {enrollment.last_name},

                        Thank you for enrolling in "{course.coursename}" at Vetri Technology Solutions.

                        Your payment of ₹{total_amount} has been successfully received. 
                        Payment Reference ID: {data['razorpay_payment_id']}

                        Our team will contact you shortly with further instructions.

                        Best Regards,
                        Vetri Technology Solutions Team
                        """
                send_mail(subject, message, settings.EMAIL_HOST_USER, [enrollment.email], fail_silently=True)
                logger.info("Confirmation email sent.")
            except Exception as e:
                logger.error(f"Email sending failed: {e}")

            # 6. Return Data to Frontend for the Success Modal
            response_data = {
                'status': 'success',
                'transaction_id': data['razorpay_payment_id'],
                'date': timezone.now().strftime('%d/%m/%Y'),
                'amount': f"{total_amount:,.0f}",
                'email': enrollment.email,
                'method': 'Online Payment',
                'order_id': data['razorpay_order_id']
            }
            logger.info(f"Payment success, returning: {response_data}")
            return JsonResponse(response_data)

        except Exception as e:
            logger.error(f"Unexpected error in verify_payment: {e}")
            return JsonResponse({'status': 'error', 'message': f'Error saving enrollment: {str(e)}'}, status=500)
            
    return JsonResponse({'status': 'invalid method'}, status=405)

def download_invoice(request, order_id):
    try:
        enrollment = Enrollment.objects.get(razorpay_order_id=order_id)
        
        # Create PDF buffer
        buffer = BytesIO()
        
        # Setup Document (Letter size: 595 x 792 points)
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter, 
            rightMargin=40, 
            leftMargin=40, 
            topMargin=40, 
            bottomMargin=40
        )
        
        styles = getSampleStyleSheet()
        
        # Custom Styles
        normal_style = styles['Normal']
        normal_style.fontSize = 10
        normal_style.leading = 14
        
        bold_style = ParagraphStyle(
            'BoldStyle',
            parent=normal_style,
            fontName='Helvetica-Bold'
        )
        
        elements = []
        
        # ==========================================
        # 1. HEADER SECTION
        # ==========================================
        try:
            logo_path = finders.find('images/VTSlogo.jpg')
            if logo_path and os.path.exists(logo_path):
                logo = Image(logo_path, width=100, height=40, kind='proportional')
            else:
                logo = Paragraph("<b><font size=24 color='#6C2CB1'>VTS</font></b>", normal_style)
        except:
            logo = Paragraph("<b><font size=24 color='#6C2CB1'>VTS</font></b>", normal_style)
        
        company_info = Paragraph(
            "<b>Vetri Technology Solutions</b><br/>"
            "April's Complex, Bus Stand backside,<br/>"
            "Surandai - 627 859",
            normal_style
        )
        
        header_table = Table([[logo, company_info]], colWidths=[120, 310])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 15))
        
        # Divider line
        line = Table([['']], colWidths=[430])
        line.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 1, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(line)
        elements.append(Spacer(1, 20))
        
        # ==========================================
        # 2. BILL TO & INVOICE DETAILS
        # ==========================================
        customer_header = Paragraph("<b>BILL TO</b>", bold_style)
        customer_details = Paragraph(
            f"{enrollment.first_name} {enrollment.last_name}<br/>"
            f"+91 {enrollment.phone}<br/>"
            f"{enrollment.address}<br/>"
            f"{enrollment.city}, {enrollment.state} - {enrollment.pincode}",
            normal_style
        )
        
        invoice_header = Paragraph("<b>INVOICE</b>", bold_style)
        invoice_info = Paragraph(
            f"<b>Invoice No:</b> {order_id}<br/>"
            f"<b>Date:</b> {timezone.now().strftime('%d/%m/%Y')}<br/>"
            f"<b>Course:</b> {enrollment.course.coursename}",
            normal_style
        )
        
        info_table = Table([
            [customer_header, '', invoice_header],
            [customer_details, '', invoice_info]
        ], colWidths=[180, 20, 210])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 25))
        
        # ==========================================
        # 3. CALCULATIONS
        # ==========================================
        raw_fee_str = str(enrollment.course.course_fee).replace('₹', '').replace('Rs.', '').replace(',', '').strip()
        
        try:
            base_amount = float(raw_fee_str)
        except ValueError:
            base_amount = 0.0
            
        gst_amount = base_amount * 0.18
        total_amount = base_amount + gst_amount
        
        str_base = f"₹ {base_amount:,.2f}"
        str_gst = f"₹ {gst_amount:,.2f}"
        str_total = f"₹ {total_amount:,.2f}"
        
        # ==========================================
        # 4. ITEM TABLE
        # ==========================================
        item_data = [
            [
                Paragraph('<b>Description</b>', bold_style), 
                Paragraph('<b>Qty</b>', bold_style), 
                Paragraph('<b>Rate</b>', bold_style), 
                Paragraph('<b>Amount</b>', bold_style)
            ],
            [
                Paragraph(enrollment.course.coursename, normal_style), 
                '1', 
                str_base,
                str_base
            ]
        ]
        
        item_table = Table(item_data, colWidths=[220, 40, 85, 85])
        item_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ]))
        elements.append(item_table)
        elements.append(Spacer(1, 15))
        
        # ==========================================
        # 5. SUMMARY SECTION - FIXED
        # ==========================================
        # Create a simpler summary with proper alignment
        summary_data = [
            [Paragraph('<b>Subtotal</b>', normal_style), str_base],
            [Paragraph('<b>GST (18%)</b>', normal_style), str_gst],
            [Paragraph('<b>Total Amount</b>', bold_style), str_total],
            [Paragraph('<b>Paid Amount</b>', bold_style), str_total],
            [Paragraph('<b>Balance Due</b>', normal_style), '₹ 0.00'],
        ]
        
        # Use right-aligned style for amounts
        summary_table = Table(summary_data, colWidths=[200, 100])
        summary_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, 2), (0, 3), 'Helvetica-Bold'),
            ('FONTNAME', (1, 2), (1, 3), 'Helvetica-Bold'),
            ('LINEABOVE', (0, 2), (1, 2), 1, colors.black),
            ('LINEABOVE', (0, 3), (1, 3), 1, colors.green),
            ('LINEBELOW', (0, 4), (1, 4), 0.5, colors.grey),
        ]))
        
        # Place summary on the right side
        empty_col = Table([['']], colWidths=[130])
        layout_table = Table([[empty_col, summary_table]], colWidths=[130, 300])
        layout_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(layout_table)
        
        elements.append(Spacer(1, 30))
        
        # ==========================================
        # 6. FOOTER
        # ==========================================
        footer_text = Paragraph(
            "<b>Thank you for your business!</b><br/>"
            "For any queries, contact us at: vetritechnologysolutions@gmail.com",
            ParagraphStyle('Footer', parent=normal_style, alignment=1, fontSize=9, textColor=colors.grey)
        )
        elements.append(footer_text)
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Invoice_{order_id}.pdf"'
        return response
    
    except Enrollment.DoesNotExist:
        return HttpResponse("Invoice not found.", status=404)
    except Exception as e:
        logger.error(f"Error generating PDF invoice: {e}")
        import traceback
        traceback.print_exc()
        return HttpResponse(f"Error generating invoice: {str(e)}", status=500)
    

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