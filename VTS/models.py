from django.db import models
from django.urls import reverse
import re
import requests
from django.utils.text import slugify
from django.core.exceptions import ValidationError



class HomeBanner(models.Model):
    headline = models.CharField(max_length=255, help_text="The main bold text")
    description = models.TextField(help_text="The smaller paragraph text")
    background_image = models.ImageField(upload_to='home_banners/')
    is_active = models.BooleanField(default=False, help_text="Check this to display THIS banner on the homepage. Only one should be active.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Home Banner"
        verbose_name_plural = "Home Banners"

    def __str__(self):
        return f"{self.headline} ({'Active' if self.is_active else 'Inactive'})"


class HomeAboutSection(models.Model):
    # Image
    image = models.ImageField(upload_to='home_about/')
    
    # Floating Badge (bottom right of image)
    badge_title = models.CharField(max_length=100, help_text="e.g., 'Established in 2021'")
    badge_description = models.TextField(help_text="e.g., 'Specializing in IT training...'")
    main_heading = models.CharField(max_length=200, help_text="e.g., 'Why Choose Our Training Programs'")
    main_description = models.TextField()
    is_active = models.BooleanField(default=False, help_text="Check this to display THIS section on the homepage.")

    class Meta:
        verbose_name = "Home About Section"
        verbose_name_plural = "Home About Sections"

    def __str__(self):
        return f"{self.main_heading} ({'Active' if self.is_active else 'Inactive'})"


class HomeBenefitSection(models.Model):
    badge_text = models.CharField(max_length=50, default="Key Benefits")
    image = models.ImageField(upload_to='home_benefits/', help_text="The illustration on the left")
    is_active = models.BooleanField(default=False, help_text="Check to display this section on the homepage")

    class Meta:
        verbose_name = "Home Benefit Section"
        verbose_name_plural = "Home Benefit Sections"

    def __str__(self):
        return f"{self.badge_text} ({'Active' if self.is_active else 'Inactive'})"


class BenefitCard(models.Model):
    ICON_CHOICES = (
        ('users', 'Users / Team'),
        ('video', 'Video / Live Class'),
        ('briefcase', 'Briefcase / Practical'),
        ('trending', 'Trending / Career'),
        ('heart', 'Heart / Mentorship'),
        ('badge', 'Badge / Certification'),
        ('check', 'Checkmark (Default)'),
    )

    section = models.ForeignKey(HomeBenefitSection, on_delete=models.CASCADE, related_name='cards')
    icon = models.CharField(max_length=20, choices=ICON_CHOICES, default='check')
    title = models.CharField(max_length=100, help_text="e.g., 'Industry-Experienced Trainers'")
    description = models.CharField(max_length=200, help_text="Keep it short and punchy.")
    order = models.IntegerField(default=0, help_text="Order in which it appears (1, 2, 3...)")

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


class HomeProcessSection(models.Model):
    title = models.CharField(max_length=200, default="How Our Training Works")
    subtitle = models.TextField(default="Follow our proven 4-step journey to transform from a beginner into an industry-ready tech professional.")
    is_active = models.BooleanField(default=False, help_text="Check to display this section on the homepage")

    class Meta:
        verbose_name = "Home Process Section"
        verbose_name_plural = "Home Process Sections"

    def __str__(self):
        return f"{self.title} ({'Active' if self.is_active else 'Inactive'})"


class ProcessStep(models.Model):
    section = models.ForeignKey(HomeProcessSection, on_delete=models.CASCADE, related_name='steps')
    step_number = models.PositiveIntegerField(help_text="1, 2, 3, or 4")
    title = models.CharField(max_length=100, help_text="e.g., 'Register'")
    description = models.CharField(max_length=200)
    icon_image = models.ImageField(upload_to='process_icons/', help_text="Upload a small PNG icon")

    class Meta:
        ordering = ['step_number']

    def __str__(self):
        return f"Step {self.step_number}: {self.title}"
    
class LearningJourneyCTA(models.Model):
    title = models.CharField(max_length=200, default="Start your Learning Journey today !")
    description = models.TextField(help_text="The subtitle text")
    button_text = models.CharField(max_length=50, default="Get Free Consultation")
    image = models.ImageField(upload_to='cta_images/', help_text="Upload the cutout person image (PNG with transparent background recommended)")
    is_active = models.BooleanField(default=False, help_text="Check to display this banner on the page")

    class Meta:
        verbose_name = "Home Learning Journey CTA"
        verbose_name_plural = "Home Learning Journey CTAs"

    def __str__(self):
        return f"{self.title} ({'Active' if self.is_active else 'Inactive'})"

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
    tools_covered = models.CharField(max_length=500, blank=True, null=True)
    learn_title = models.CharField(max_length=255, blank=True, null=True)
    learn = models.TextField()
    is_featured = models.BooleanField(default=False)
    job_offer = models.CharField(
        max_length=3,
        choices=[('Yes', 'Yes'), ('No', 'No')],
        default='No',
    )
    benefit_title = models.CharField(max_length=255, blank=True, null=True)
    benefits = models.TextField(blank=True)
    is_enrollable_online = models.BooleanField(default=True)
    emi_available = models.BooleanField(default=False, help_text="Check if EMI option is available for this course")
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['is_featured'], name='course_featured_idx'),
            models.Index(fields=['category'], name='course_category_idx'),
            models.Index(fields=['is_enrollable_online'], name='course_enroll_idx'),
            models.Index(fields=['emi_available'], name='course_emi_idx'),
        ]

    def __str__(self):
        return self.coursename

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.coursename)
        super().save(*args, **kwargs)

    def get_benefits_list(self):
        return [b.strip() for b in self.benefits.split('\n') if b.strip()]

    def get_learn_points(self):
        return [p.strip() for p in self.learn.split('\n') if p.strip()]

    def get_tools_list(self):
        if not self.tools_covered:
            return []
        return [t.strip() for t in self.tools_covered.split(',') if t.strip()]
    
    def get_absolute_url(self):
        return reverse('course_detail', kwargs={'slug': self.slug})


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


class AboutPageSection(models.Model):
    main_heading = models.CharField(max_length=200, default="About Vetri Training – Online IT Courses with Placement Support")
    sub_heading = models.TextField(default="Empowering the next generation of IT Professionals with foundational knowledge and industry - ready skills")
    story_heading = models.CharField(max_length=200, default="Our Story – Building Job-Oriented Training Programs")
    paragraph_1 = models.TextField()
    paragraph_2 = models.TextField(blank=True, null=True, help_text="Optional second paragraph")
    image = models.ImageField(upload_to='about_pages/', help_text="Upload the main collaboration image")
    is_active = models.BooleanField(default=False, help_text="Check to display this on the website")

    class Meta:
        verbose_name = "About Page Section"
        verbose_name_plural = "About Page Sections"

    def __str__(self):
        return f"{self.main_heading} ({'Active' if self.is_active else 'Inactive'})"


class AboutMissionVision(models.Model):
    mission_title = models.CharField(max_length=100, default="Mission")
    mission_text = models.TextField(help_text="Text for the Mission card")
    mission_icon = models.ImageField(upload_to='about_icons/', help_text="Upload the Mission target icon")
    vision_title = models.CharField(max_length=100, default="Vision")
    vision_text = models.TextField(help_text="Text for the Vision card")
    vision_icon = models.ImageField(upload_to='about_icons/', help_text="Upload the Vision bulb icon")
    is_active = models.BooleanField(default=False, help_text="Check to display this section on the About page")

    class Meta:
        verbose_name = "Mission & Vision Section"
        verbose_name_plural = "Mission & Vision Sections"

    def __str__(self):
        return f"Mission & Vision ({'Active' if self.is_active else 'Inactive'})"


class EcosystemSection(models.Model):
    center_badge_text = models.CharField(max_length=100, default="The Complete VETRI Ecosystem")
    main_image = models.ImageField(upload_to='ecosystem/', help_text="The large illustration on the left")
    is_active = models.BooleanField(default=False, help_text="Check to display this section")

    class Meta:
        verbose_name = "Ecosystem Section"
        verbose_name_plural = "Ecosystem Sections"

    def __str__(self):
        return f"Ecosystem Section ({'Active' if self.is_active else 'Inactive'})"

class EcosystemBranch(models.Model):
    section = models.ForeignKey(EcosystemSection, on_delete=models.CASCADE, related_name='branches')
    logo = models.ImageField(upload_to='ecosystem_logos/')
    title = models.CharField(max_length=100, help_text="e.g., 'Vetri Technology Solution (VTS)'")
    link_url = models.CharField(max_length=200, help_text="e.g., '/' or 'https://google.com'")
    link_text = models.CharField(max_length=20, default="Site")
    bullet_1 = models.CharField(max_length=100)
    bullet_2 = models.CharField(max_length=100)
    
    order = models.IntegerField(default=0, help_text="Order (1, 2, 3)")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class AboutApproachSection(models.Model):
    title = models.CharField(max_length=200, default="Our Job-Oriented Training Approach")
    is_active = models.BooleanField(default=False, help_text="Check to display this section on the page")

    class Meta:
        verbose_name = "About Approach Section"
        verbose_name_plural = "About Approach Sections"

    def __str__(self):
        return f"{self.title} ({'Active' if self.is_active else 'Inactive'})"

class AboutApproachCard(models.Model):
    section = models.ForeignKey(AboutApproachSection, on_delete=models.CASCADE, related_name='cards')
    text = models.TextField(help_text="The paragraph text inside the card")
    order = models.IntegerField(default=0, help_text="Order (1, 2, 3...)")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Card: {self.text[:30]}..."
    

class CareerSkillsSection(models.Model):
    title = models.CharField(max_length=200, default="How We Build Your Career Skills")
    is_active = models.BooleanField(default=False, help_text="Check to display this section")

    class Meta:
        verbose_name = "About Skills Section"
        verbose_name_plural = "About Skills Sections"

    def __str__(self):
        return f"{self.title} ({'Active' if self.is_active else 'Inactive'})"

class CareerSkillCard(models.Model):
    ICON_CHOICES = (
        ('platform', 'Monitor / Platform'),
        ('approach', 'Network / Steps'),
        ('connection', 'Clipboard / Industry'),
    )

    section = models.ForeignKey(CareerSkillsSection, on_delete=models.CASCADE, related_name='cards')
    icon = models.CharField(max_length=20, choices=ICON_CHOICES, default='platform')
    title = models.CharField(max_length=100, help_text="e.g., 'About the Training Platform'")
    
    bullet_1 = models.CharField(max_length=100)
    bullet_2 = models.CharField(max_length=100)
    bullet_3 = models.CharField(max_length=100)
    bullet_4 = models.CharField(max_length=100, blank=True, null=True, help_text="Optional 4th bullet")
    
    order = models.IntegerField(default=0, help_text="1, 2, or 3")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title

class JourneySection(models.Model):
    title = models.CharField(max_length=200, default='"Your Learning & Career Journey"')
    is_active = models.BooleanField(default=False, help_text="Check to display this section")

    class Meta:
        verbose_name = "About Journey Section"
        verbose_name_plural = "About Journey Sections"

    def __str__(self):
        return f"{self.title} ({'Active' if self.is_active else 'Inactive'})"

class JourneyStep(models.Model):
    section = models.ForeignKey(JourneySection, on_delete=models.CASCADE, related_name='steps')
    title = models.CharField(max_length=100, help_text="e.g., 'Entry & Counseling'")
    description = models.CharField(max_length=150)
    image = models.ImageField(upload_to='journey_steps/', help_text="Upload the step illustration")
    order = models.IntegerField(default=0, help_text="1, 2, 3, 4, 5, 6")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Step {self.order}: {self.title}"
    
class EnrollmentSection(models.Model):
    title = models.CharField(max_length=200, default="Who Can Enroll in Our Courses")
    is_active = models.BooleanField(default=False, help_text="Check to display this section")

    class Meta:
        verbose_name = "About Enrollment Section"
        verbose_name_plural = "About Enrollment Sections"

    def __str__(self):
        return f"{self.title} ({'Active' if self.is_active else 'Inactive'})"

class TargetAudience(models.Model):
    COLOR_CHOICES = (
        ('#FF9C00', 'Orange'),
        ('#6C2CB1', 'Purple'),
    )

    section = models.ForeignKey(EnrollmentSection, on_delete=models.CASCADE, related_name='audiences')
    title = models.CharField(max_length=100, help_text="e.g., 'Students', 'Career Switchers'")
    image = models.ImageField(upload_to='enrollment_images/', help_text="Upload the portrait image")
    
    theme_color = models.CharField(max_length=10, choices=COLOR_CHOICES, default='#FF9C00')
    
    order = models.IntegerField(default=0, help_text="1, 2, 3, 4, 5")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class CTABanner(models.Model):
    title = models.CharField(max_length=150, default="Ready to Start Your Career")
    description = models.TextField(help_text="The text below the title")
    image = models.ImageField(upload_to='cta_banners/', help_text="Upload the circular profile/avatar image")
    button_text = models.CharField(max_length=50, default="Get Free Consultation Now")
    
    is_active = models.BooleanField(default=False, help_text="Check to display this banner on the page")

    class Meta:
        verbose_name = "About CTA Banner"
        verbose_name_plural = "About CTA Banners"

    def __str__(self):
        return f"{self.title} ({'Active' if self.is_active else 'Inactive'})"


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

class ContactInfoCard(models.Model):
    ICON_CHOICES = (
        ('clock', 'Clock (Office Hours)'),
        ('phone', 'Phone (Call Us)'),
        ('mail', 'Envelope (Email)'),
        ('location', 'Map Pin (Address)'),
    )

    title = models.CharField(max_length=100, help_text="e.g., 'Office Hours', 'Phone Number'")
    icon = models.CharField(max_length=20, choices=ICON_CHOICES, default='clock')
    details = models.TextField(help_text="Press Enter to create a new line.")
    
    order = models.IntegerField(default=0, help_text="1, 2, 3...")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Contact Info Card"
        verbose_name_plural = "Contact Info Cards"

    def __str__(self):
        return self.title


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

class ImageCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="e.g., 'Classrooms', 'Labs', 'Campus'")
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Image Category"
        verbose_name_plural = "Image Categories"

    def __str__(self):
        return self.name
    
class EnvironmentImage(models.Model):
    MEDIA_CHOICES = (
        ('image', 'Image'),
        ('video', 'Video'),
    )

    category = models.ForeignKey('ImageCategory', on_delete=models.CASCADE, related_name='images', null=True, blank=True)
    media_type = models.CharField(max_length=10, choices=MEDIA_CHOICES, default='image')
    image = models.ImageField(upload_to='learning_environment/images/', blank=True, null=True)
    video = models.FileField(upload_to='learning_environment/videos/', blank=True, null=True, help_text="Upload .mp4 or .webm files here")
    
    alt_text = models.CharField(max_length=255, blank=True, help_text="Description for image, or title for video")
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Contact Environment Image & video"
        verbose_name_plural = "Contact Environment Image & video"

    def __str__(self):
        category_name = self.category.name if self.category else "Uncategorized"
        return f"[{category_name}] {self.get_media_type_display()} - {self.alt_text or 'Item'}"


    def clean(self):
        super().clean()
        if self.media_type == 'image' and not self.image:
            raise ValidationError({'image': 'You selected "Image" but did not upload an image file.'})
        if self.media_type == 'video' and not self.video:
            raise ValidationError({'video': 'You selected "Video" but did not upload a video file.'})


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
    project_link = models.URLField(max_length=500, blank=True, null=True, help_text="External link to the project (e.g., GitHub, live website)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} by {self.student_name}"


class StorySection(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="e.g., 'Feedback Videos', 'Success Stories'")
    order = models.IntegerField(default=0, help_text="Determines which section shows up first on the page")

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Story Section"
        verbose_name_plural = "Story Sections"

    def __str__(self):
        return self.name


class StudentStory(models.Model):
    section = models.ForeignKey(StorySection, on_delete=models.CASCADE, related_name='stories', null=True, blank=True)
    student_name = models.CharField(max_length=100, blank=True, null=True)
    course_or_role = models.CharField(max_length=100, blank=True, null=True)
    image = models.ImageField(upload_to='student_stories/')
    video_file = models.FileField(upload_to='student_videos/', blank=True, null=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', '-id']
        verbose_name_plural = "Student Stories"

    def __str__(self):
        return f"[{self.section.name}] {self.student_name}"


class CompanyLink(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField()

    def __str__(self):
        return self.name
    

class Contactnumber(models.Model):
    contact_numbers = models.CharField(
        max_length=100,
        help_text="Enter phone numbers separated by commas (e.g. 8438164827, 8438524427)"
    )

    class Meta:
        verbose_name = "Contact Number"
        verbose_name_plural = "Contact Numbers"

    def __str__(self):
        return self.contact_numbers
    

class CompanyStat(models.Model):
    value = models.CharField(max_length=20, help_text="e.g., '8+', '5000+', '85%'")
    label = models.CharField(max_length=100, help_text="e.g., 'Years of Excellence', 'Students Trained'")
    order = models.PositiveIntegerField(default=0, help_text="Determines the display order")

    class Meta:
        ordering = ['order'] # Automatically sorts by the order field
        verbose_name = "Company Stat"
        verbose_name_plural = "Company Stats"

    def __str__(self):
        return f"{self.value} - {self.label}"
    

class BrochureLead(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    course_name = models.CharField(max_length=200)
    downloaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-downloaded_at']
        verbose_name = "Brochure Lead"
        verbose_name_plural = "Brochure Leads"

    def __str__(self):
        return f"{self.name} - {self.course_name}"
    
class VisitorLog(models.Model):
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    path = models.CharField(max_length=255, help_text="The page they visited")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Visitor Log"
        verbose_name_plural = "Visitor Logs"

    def __str__(self):
        return f"{self.ip_address} visited {self.path} at {self.timestamp}"