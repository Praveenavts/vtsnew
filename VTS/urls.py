from django.urls import path
from .views import (home, courses, about, contact,
                    course_detail,create_enrollment,verify_payment,)


urlpatterns = [
    path('', home, name='home'),

    path('courses', courses, name='courses'),
    path('courses/<int:pk>/', course_detail, name='course_detail'),
    path('api/create-enrollment/', create_enrollment, name='create_enrollment'),
    path('api/verify-payment/', verify_payment, name='verify_payment'),
    
    path('about', about, name='about'),
    path('contact', contact, name='contact'),

]