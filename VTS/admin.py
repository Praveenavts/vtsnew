from django.contrib import admin
from .models import *


@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'order')
    ordering      = ('order', 'name')
    search_fields = ('name',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display   = ('coursename', 'category', 'course_fee', 'duration',
                      'mode', 'is_featured', 'is_enrollable_online', 'job_offer')
    list_filter    = ('category', 'is_featured', 'is_enrollable_online', 'job_offer', 'mode')
    search_fields  = ('coursename', 'short_description', 'course_overview')
    ordering       = ('coursename',)
    list_editable  = ('is_featured', 'is_enrollable_online')
    fieldsets = (
        ('Basic Info', {
            'fields': ('category', 'coursename', 'level', 'short_description',
                       'detailtitle', 'subtitle_1', 'subtitle_2', 'subtitle_3')
        }),
        ('Pricing & Details', {
            'fields': ('course_fee', 'duration', 'certification', 'mode', 'job_offer')
        }),
        ('Content', {
            'fields': ('course_overview', 'tools_covered', 'learn', 'benefits')
        }),
        ('Media', {
            'fields': ('thumbnail', 'short_video', 'brochure')
        }),
        ('Settings', {
            'fields': ('is_featured', 'is_enrollable_online')
        }),
    )


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display  = ('id', 'first_name', 'last_name', 'phone', 'email',
                     'course', 'payment_status', 'payment_method', 'payment_date')
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


@admin.register(EnvironmentImage)
class EnvironmentImageAdmin(admin.ModelAdmin):
    list_display = ('alt_text', 'order', 'image')
    ordering     = ('order',)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display  = ('question', 'order')
    ordering      = ('order',)
    search_fields = ('question', 'answer')


@admin.register(StudentProject)
class StudentProjectAdmin(admin.ModelAdmin):
    list_display  = ('title', 'student_name', 'category', 'created_at')
    list_filter   = ('category',)
    search_fields = ('title', 'student_name', 'category')
    ordering      = ('-created_at',)


@admin.register(StudentStory)
class StudentStoryAdmin(admin.ModelAdmin):
    list_display  = ('student_name', 'course_or_role', 'order')
    ordering      = ('order', '-id')
    search_fields = ('student_name', 'course_or_role')