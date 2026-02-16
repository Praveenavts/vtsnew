from django.db import models
from django.urls import reverse

# Create your models here.

class Course(models.Model):
    CATEGORY_CHOICES = [
        ('Development', 'Development'),
        ('Design', 'Design'),
        ('Data', 'Data'),
        ('Emerging Tech', 'Emerging Tech'),
    ]

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Development')
    thumbnail = models.ImageField(upload_to='course_thumbnails/', help_text="Image for the listing card")
    coursename = models.CharField(max_length=200, help_text="Short course name for listing card")
    level = models.CharField(max_length=100, help_text="e.g., Beginner to Advanced")
    detailtitle = models.CharField(max_length=255, help_text="Main title on the detail page")
    subtitle_1 = models.CharField(max_length=255, blank=True)
    subtitle_2 = models.CharField(max_length=255, blank=True)
    subtitle_3 = models.CharField(max_length=255, blank=True)
    course_fee = models.CharField(max_length=50, help_text="e.g., ₹ 30,000")
    duration = models.CharField(max_length=50, help_text="e.g., 6 Months")
    certification = models.CharField(max_length=50, default="Yes")
    mode = models.CharField(max_length=100, help_text="e.g., Online & Offline")
    brochure = models.FileField(upload_to='brochures/', blank=True, null=True, help_text="Upload PDF brochure")
    short_video = models.FileField(upload_to='course_videos/', blank=True, null=True, help_text="Short overview video")
    course_overview = models.TextField()
    tools_covered = models.CharField(max_length=500, help_text="Comma-separated tools (e.g., Python, Django, React, MySQL, APIs)")
    learn = models.TextField(help_text="What you will learn. Enter each bullet point on a new line.")

    def __str__(self):
        return self.coursename

    def get_learn_points(self):
        return [point.strip() for point in self.learn.split('\n') if point.strip()]

    def get_tools_list(self):
        return [tool.strip() for tool in self.tools_covered.split(',') if tool.strip()]
    


class Enrollment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    gender = models.CharField(max_length=20)
    dob = models.DateField()
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    mode = models.CharField(max_length=50)
    message = models.TextField(blank=True, null=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    payment_status = models.CharField(max_length=20, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} - {self.course.coursename}"