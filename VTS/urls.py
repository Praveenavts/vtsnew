from django.urls import path
from .views import (home, courses, about, contact,
                    course_detail,create_enrollment,verify_payment,
                    download_invoice,submit_enquiry,image_gallery,
                    student_projects,)


urlpatterns = [
    path('', home, name='home'),

    path('courses', courses, name='courses'),
    path('courses/<int:pk>/', course_detail, name='course_detail'),
    path('api/create-enrollment/', create_enrollment, name='create_enrollment'),
    path('api/verify-payment/', verify_payment, name='verify_payment'),
    path('api/download-invoice/<str:order_id>/', download_invoice, name='download_invoice'),
    
    path('about', about, name='about'),

    path('contact', contact, name='contact'),
    path('api/submit-enquiry/', submit_enquiry, name='submit_enquiry'),
    path('learning-environment/', image_gallery, name='image_gallery'),
    path('student-projects/', student_projects, name='student_projects'),

]