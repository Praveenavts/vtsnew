from django.db import models
from django.urls import reverse
import re
import requests

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
    short_description = models.CharField(max_length=255, blank=True, help_text="Brief description for the card (e.g., 'Build complete web applications')")
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
    is_featured = models.BooleanField(default=False, help_text="Check this to show the course on the homepage")
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
    

class Enquiry(models.Model):
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    course_interest = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.course_interest}"


class Branch(models.Model):
    name = models.CharField(max_length=255, help_text="e.g., Surandai - April's Complex")
    address = models.TextField(help_text="Full address to display on the card")
    map_link = models.URLField(max_length=1000, help_text="Paste the Google Maps link here")
    latitude = models.FloatField(blank=True, null=True, help_text="Auto-fills from link. Or enter manually (e.g., 8.9743)")
    longitude = models.FloatField(blank=True, null=True, help_text="Auto-fills from link. Or enter manually (e.g., 77.3948)")
    
    def save(self, *args, **kwargs):
        if self.map_link and not (self.latitude and self.longitude):
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                
                response = requests.get(self.map_link, headers=headers, allow_redirects=True, timeout=10)
                final_url = response.url
                match_at = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', final_url)
                match_3d4d = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', final_url)
                
                if match_at:
                    self.latitude = float(match_at.group(1))
                    self.longitude = float(match_at.group(2))
                elif match_3d4d:
                    self.latitude = float(match_3d4d.group(1))
                    self.longitude = float(match_3d4d.group(2))
                    
            except Exception as e:
                print(f"Error parsing map link for {self.name}: {e}")
                
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class EnvironmentImage(models.Model):
    image = models.ImageField(upload_to='learning_environment/')
    alt_text = models.CharField(max_length=255, blank=True, help_text="Image description")
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

class FAQ(models.Model):
    question = models.CharField(max_length=500)
    answer = models.TextField()
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.question
    
class StudentProject(models.Model):
    title = models.CharField(max_length=255, help_text="e.g., Food App design")
    student_name = models.CharField(max_length=100, help_text="e.g., divya")
    category = models.CharField(max_length=100, help_text="e.g., UI/UX Designing")
    image = models.ImageField(upload_to='student_projects/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} by {self.student_name}"
    

class StudentStory(models.Model):
    student_name = models.CharField(max_length=100)
    course_or_role = models.CharField(max_length=100)
    image = models.ImageField(upload_to='student_stories/')
    video_file = models.FileField(upload_to='student_videos/', blank=True, null=True, help_text="Upload MP4 video file")
    
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', '-id']
        verbose_name_plural = "Student Stories"

    def __str__(self):
        return self.student_name