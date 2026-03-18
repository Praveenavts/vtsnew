from django.db import models
from django.urls import reverse
import re
import requests


class CourseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Course Category"
        verbose_name_plural = "Course Categories"

    def __str__(self):
        return self.name


class Course(models.Model):
    category = models.ForeignKey(
        CourseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='courses',
    )
    thumbnail = models.ImageField(upload_to='course_thumbnails/')
    coursename = models.CharField(max_length=200)
    level = models.CharField(max_length=100)
    short_description = models.CharField(max_length=255, blank=True)
    detailtitle = models.CharField(max_length=255)
    subtitle_1 = models.CharField(max_length=255, blank=True)
    subtitle_2 = models.CharField(max_length=255, blank=True)
    subtitle_3 = models.CharField(max_length=255, blank=True)

    course_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Course fee in rupees (e.g. 10000.00) — do NOT include ₹ symbol"
    )

    duration = models.CharField(max_length=50)
    certification = models.CharField(max_length=50, default="Yes")
    mode = models.CharField(max_length=100)
    brochure = models.FileField(upload_to='brochures/', blank=True, null=True)
    short_video = models.FileField(upload_to='course_videos/', blank=True, null=True)
    course_overview = models.TextField()
    tools_covered = models.CharField(max_length=500)
    learn = models.TextField()
    is_featured = models.BooleanField(default=False)
    job_offer = models.CharField(
        max_length=3,
        choices=[('Yes', 'Yes'), ('No', 'No')],
        default='No',
    )
    benefits = models.TextField(blank=True)
    is_enrollable_online = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['is_featured'], name='course_featured_idx'),
            models.Index(fields=['category'], name='course_category_idx'),
            models.Index(fields=['is_enrollable_online'], name='course_enroll_idx'),
        ]

    def __str__(self):
        return self.coursename

    def get_benefits_list(self):
        return [b.strip() for b in self.benefits.split('\n') if b.strip()]

    def get_learn_points(self):
        return [p.strip() for p in self.learn.split('\n') if p.strip()]

    def get_tools_list(self):
        return [t.strip() for t in self.tools_covered.split(',') if t.strip()]


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

    razorpay_order_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True, 
    )
    payment_status = models.CharField(max_length=20, default='Pending')
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    bank_rrn = models.CharField(max_length=100, blank=True, null=True)
    payment_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_status'], name='enroll_status_idx'),
            models.Index(fields=['email'],          name='enroll_email_idx'),
            models.Index(fields=['created_at'],     name='enroll_date_idx'),
        ]

    def __str__(self):
        return f"{self.first_name} - {self.course.coursename}"


class Enquiry(models.Model):
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    course_interest = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at'], name='enquiry_date_idx'),
        ]

    def __str__(self):
        return f"{self.full_name} - {self.course_interest}"


class Branch(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    map_link = models.URLField(max_length=1000)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.map_link and not (self.latitude and self.longitude):
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
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
    alt_text = models.CharField(max_length=255, blank=True)
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
    title = models.CharField(max_length=255)
    student_name = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
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
    video_file = models.FileField(upload_to='student_videos/', blank=True, null=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', '-id']
        verbose_name_plural = "Student Stories"

    def __str__(self):
        return self.student_name
