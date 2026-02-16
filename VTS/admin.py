from django.contrib import admin
from .models import Course
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