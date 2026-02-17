from django.contrib import admin
from .models import (Course, Enquiry, Branch, EnvironmentImage,
                    FAQ, Enrollment, StudentProject,StudentStory,)
from django.utils.html import format_html

# Register your models here.

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):

    list_display = (
        'coursename',
        'category',
        'level',
        'course_fee',
        'duration',
        'thumbnail_preview',
    )

    list_filter = ('category', 'level', 'mode')
    search_fields = ('coursename', 'category', 'level')
    readonly_fields = ('thumbnail_preview',)

    fieldsets = (
        ("Basic Information", {
            'fields': (
                'category',
                'thumbnail',
                'thumbnail_preview',
                'coursename',
                'level',
                'is_featured',
                'short_description',
                'detailtitle',
                'subtitle_1',
                'subtitle_2',
                'subtitle_3',
            )
        }),
        ("Course Details", {
            'fields': (
                'course_fee',
                'duration',
                'certification',
                'mode',
                'brochure',
                'short_video',
            )
        }),
        ("Content", {
            'fields': (
                'course_overview',
                'tools_covered',
                'learn',
            )
        }),
    )

    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" width="80" style="border-radius:5px;" />',
                obj.thumbnail.url
            )
        return "No Image"

    thumbnail_preview.short_description = "Thumbnail Preview"




admin.site.register(Enrollment)
admin.site.register(Enquiry)

class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'latitude', 'longitude', 'has_coordinates')
    def has_coordinates(self, obj):
        return bool(obj.latitude and obj.longitude)
    has_coordinates.boolean = True

admin.site.register(Branch,BranchAdmin)
admin.site.register(EnvironmentImage)
admin.site.register(FAQ)

admin.site.register(StudentProject)


class StudentStoryAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'course_or_role', 'order')
    list_editable = ('order',)

admin.site.register(StudentStory, StudentStoryAdmin)