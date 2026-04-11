from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Course  

# 🔹 Static pages
class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = 'weekly'

    def items(self):
        return ['home', 'about', 'contact', 'courses', 'student_projects']

    def location(self, item):
        return reverse(item)


# 🔹 Dynamic pages (DB)
class CourseSitemap(Sitemap):
    priority = 0.8
    changefreq = 'daily'

    def items(self):
        return Course.objects.all()

    def location(self, obj):
        return obj.get_absolute_url()