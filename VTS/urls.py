from django.urls import path
from .views import *


urlpatterns = [
    path('', home, name='home'),
    path('course-autocomplete/',course_autocomplete, name='course_autocomplete'),
    path('courses/', courses, name='courses'),
    path('courses/<slug:slug>/', course_detail, name='course_detail'),
    path('api/save-brochure-lead/', save_brochure_lead, name='save_brochure_lead'),
    path('api/create-enrollment/', create_enrollment, name='create_enrollment'),
    path('about/', about, name='about'),

    path('contact/', contact, name='contact'),
    path('api/submit-enquiry/', submit_enquiry, name='submit_enquiry'),
    path('learning-environment/', image_gallery, name='image_gallery'),
    path('student-projects/', student_projects, name='student_projects'),


]