from django.shortcuts import render,get_object_or_404
import json
import razorpay
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from .models import Course,Enrollment

# Create your views here.
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def home(request):
    return render(request, 'home.html')

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
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'invalid method'}, status=405)


def verify_payment(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        
        try:
            params_dict = {
                'razorpay_order_id': data['razorpay_order_id'],
                'razorpay_payment_id': data['razorpay_payment_id'],
                'razorpay_signature': data['razorpay_signature']
            }
            client.utility.verify_payment_signature(params_dict)
            enrollment = Enrollment.objects.get(razorpay_order_id=data['razorpay_order_id'])
            enrollment.payment_status = 'Paid'
            enrollment.save()

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
            
            # Make sure EMAIL_HOST_USER is configured in your settings.py
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[enrollment.email],
                fail_silently=False,
            )

            return JsonResponse({'status': 'success'})

        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({'status': 'error', 'message': 'Payment signature verification failed.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'invalid method'}, status=405)


def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')

