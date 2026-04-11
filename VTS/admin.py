from django.contrib import admin
from .models import *
from django.core.cache import cache
from django.contrib import messages

COURSE_CACHE_KEYS = [
    'all_courses', 'featured_courses',
    'all_categories', 'home_projects', 'home_stories',
]


@admin.register(HomeBanner)
class HomeBannerAdmin(admin.ModelAdmin):
    list_display = ('headline', 'is_active', 'created_at')
    list_filter = ('is_active',)
    list_editable = ('is_active',)

@admin.register(HomeAboutSection)
class HomeAboutSectionAdmin(admin.ModelAdmin):
    list_display = ('main_heading', 'badge_title', 'is_active')
    list_editable = ('is_active',)

class BenefitCardInline(admin.TabularInline):
    model = BenefitCard
    extra = 1 

@admin.register(HomeBenefitSection)
class HomeBenefitSectionAdmin(admin.ModelAdmin):
    list_display = ('badge_text', 'is_active')
    list_editable = ('is_active',)
    inlines = [BenefitCardInline]

class ProcessStepInline(admin.TabularInline):
    model = ProcessStep
    extra = 4
    max_num = 4 

@admin.register(HomeProcessSection)
class HomeProcessSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active')
    list_editable = ('is_active',)
    inlines = [ProcessStepInline]

@admin.register(LearningJourneyCTA)
class LearningJourneyCTAAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active')
    list_editable = ('is_active',)

@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'order')
    ordering      = ('order', 'name')
    search_fields = ('name',)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display   = ('coursename', 'slug', 'category', 'course_fee', 'duration',
                      'mode', 'is_featured','emi_available', 'is_enrollable_online', 'job_offer')
    list_filter    = ('category', 'is_featured','emi_available', 'is_enrollable_online', 'job_offer', 'mode')
    search_fields  = ('coursename', 'slug', 'short_description', 'course_overview')
    ordering       = ('coursename',)
    list_editable  = ('is_featured','emi_available', 'is_enrollable_online')
    prepopulated_fields = {'slug': ('coursename',)}
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('category', 'coursename', 'slug', 'level', 'short_description',
                       'detailtitle', 'subtitle_1', 'subtitle_2', 'subtitle_3')
        }),
        ('Pricing & Details', {
            'fields': ('course_fee', 'duration', 'certification', 'mode', 'job_offer')
        }),
        ('Content', {
            'fields': ('course_overview', 'tools_covered','learn_title', 'learn','benefit_title', 'benefits')
        }),
        ('Media', {
            'fields': ('thumbnail', 'short_video', 'brochure')
        }),
        ('Settings', {
            'fields': ('is_featured','emi_available', 'is_enrollable_online')
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        cache.delete_many(COURSE_CACHE_KEYS)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        cache.delete_many(COURSE_CACHE_KEYS)

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        cache.delete_many(COURSE_CACHE_KEYS)

    def save_queryset(self, request, queryset):
        super().save_queryset(request, queryset)
        cache.delete_many(COURSE_CACHE_KEYS)

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display  = ('id', 'first_name', 'last_name', 'phone', 'email',
                     'course')
    list_filter   = ('payment_status', 'payment_method', 'mode', 'gender', 'course')
    search_fields = ('first_name', 'last_name', 'email', 'phone',
                     'razorpay_order_id', 'razorpay_payment_id', 'bank_rrn')
    ordering      = ('-created_at',)
    readonly_fields = ('razorpay_order_id', 'razorpay_payment_id',
                       'payment_method', 'bank_rrn', 'payment_date', 'created_at')
    fieldsets = (
        ('Student Info', {
            'fields': ('course', 'first_name', 'last_name', 'email', 'phone',
                       'gender', 'dob', 'address', 'city', 'state', 'pincode',
                       'mode', 'message')
        }),
        ('Payment Info', {
            'fields': ('payment_status', 'razorpay_order_id', 'razorpay_payment_id',
                       'payment_method', 'bank_rrn', 'payment_date', 'created_at')
        }),
    )

@admin.register(AboutPageSection)
class AboutPageSectionAdmin(admin.ModelAdmin):
    list_display = ('main_heading', 'is_active')
    list_editable = ('is_active',)

@admin.register(AboutMissionVision)
class AboutMissionVisionAdmin(admin.ModelAdmin):
    list_display = ('mission_title', 'vision_title', 'is_active')
    list_editable = ('is_active',)

class EcosystemBranchInline(admin.TabularInline):
    model = EcosystemBranch
    extra = 3
    max_num = 3 

@admin.register(EcosystemSection)
class EcosystemSectionAdmin(admin.ModelAdmin):
    list_display = ('center_badge_text', 'is_active')
    list_editable = ('is_active',)
    inlines = [EcosystemBranchInline]

class AboutApproachCardInline(admin.TabularInline):
    model = AboutApproachCard
    extra = 2 

@admin.register(AboutApproachSection)
class AboutApproachSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active')
    list_editable = ('is_active',)
    inlines = [AboutApproachCardInline]

class CareerSkillCardInline(admin.TabularInline):
    model = CareerSkillCard
    extra = 3 
    max_num = 3 

@admin.register(CareerSkillsSection)
class CareerSkillsSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active')
    list_editable = ('is_active',)
    inlines = [CareerSkillCardInline]

class JourneyStepInline(admin.TabularInline):
    model = JourneyStep
    extra = 6 
    max_num = 6 

@admin.register(JourneySection)
class JourneySectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active')
    list_editable = ('is_active',)
    inlines = [JourneyStepInline]

class TargetAudienceInline(admin.TabularInline):
    model = TargetAudience
    extra = 5

@admin.register(EnrollmentSection)
class EnrollmentSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active')
    list_editable = ('is_active',)
    inlines = [TargetAudienceInline]

@admin.register(CTABanner)
class CTABannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'button_text', 'is_active')
    list_editable = ('is_active',)


@admin.register(ContactInfoCard)
class ContactInfoCardAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon', 'order', 'is_active')
    list_editable = ('order', 'is_active')

@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display  = ('full_name', 'phone', 'email', 'course_interest', 'created_at')
    list_filter   = ('course_interest',)
    search_fields = ('full_name', 'email', 'phone', 'course_interest', 'message')
    ordering      = ('-created_at',)
    readonly_fields = ('created_at',)

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display  = ('name', 'address', 'latitude', 'longitude')
    search_fields = ('name', 'address')

@admin.register(ImageCategory)
class ImageCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    list_editable = ('order',)

@admin.register(EnvironmentImage)
class EnvironmentImageAdmin(admin.ModelAdmin):
    list_display = ('alt_text', 'category', 'order')
    list_filter = ('category',) # Adds a filter sidebar
    list_editable = ('order',)

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display  = ('question', 'order')
    ordering      = ('order',)
    search_fields = ('question', 'answer')

@admin.register(StudentProject)
class StudentProjectAdmin(admin.ModelAdmin):
    list_display  = ('title', 'student_name', 'category','project_link', 'created_at')
    list_filter   = ('category',)
    search_fields = ('title', 'student_name', 'category')
    ordering      = ('-created_at',)

admin.site.register(StorySection)

@admin.register(StudentStory)
class StudentStoryAdmin(admin.ModelAdmin):
    list_display  = ('student_name', 'course_or_role', 'order')
    ordering      = ('order', '-id')
    search_fields = ('student_name', 'course_or_role')

admin.site.register(CompanyLink)

    
@admin.register(Contactnumber)
class ContactnumberAdmin(admin.ModelAdmin):
    list_display = ('contact_numbers',)


@admin.register(CompanyStat)
class CompanyStatAdmin(admin.ModelAdmin):
    list_display = ('label', 'value', 'order')
    list_editable = ('value', 'order')

@admin.register(BrochureLead)
class BrochureLeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'course_name', 'downloaded_at')
    list_filter = ('course_name', 'downloaded_at')
    search_fields = ('name', 'email', 'phone', 'course_name')
    readonly_fields = ('downloaded_at',)
    def has_add_permission(self, request):
        return False

@admin.register(VisitorLog)
class VisitorLogAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'city', 'country', 'path', 'timestamp')
    list_filter = ('country', 'timestamp', 'city')
    search_fields = ('ip_address', 'city', 'path')
    readonly_fields = ('ip_address', 'city', 'country', 'path', 'timestamp')
    list_per_page = 50

    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        total_visits = VisitorLog.objects.count()
        unique_ips = VisitorLog.objects.values('ip_address').distinct().count()
        messages.info(request, f"📊 Total Visitors: {total_visits}")

        return super().changelist_view(request, extra_context=extra_context)